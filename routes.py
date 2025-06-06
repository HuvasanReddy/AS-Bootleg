from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, session
from models import User, Project, ProjectFile
from extensions import db, ma
import os
import uuid
import json
import tempfile
import shutil
from werkzeug.utils import secure_filename
from utils.document_processor import DocumentProcessor, process_document
from utils.layer_manager import LayerManager
from schemas import UpdateLayerSchema, BatchProcessSchema, UploadFileSchema
import logging
import base64

logger = logging.getLogger(__name__)

def register_routes(app):
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal Server Error: {error}")
        return render_template('error.html', error="An internal error occurred. Please try again later."), 500

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', error="Page not found"), 404

    @app.route('/debug')
    def debug_info():
        """Endpoint to check application configuration and status"""
        try:
            db_status = "Connected" if db.session.execute('SELECT 1').scalar() else "Disconnected"
        except Exception as e:
            db_status = f"Error: {str(e)}"

        info = {
            "database_url": app.config['SQLALCHEMY_DATABASE_URI'],
            "database_status": db_status,
            "upload_folder": app.config['UPLOAD_FOLDER'],
            "template_folder": app.config['TEMPLATE_UPLOAD_FOLDER'],
            "static_folder": app.static_folder,
            "debug_mode": app.debug,
            "env": app.env
        }
        return jsonify(info)

    @app.route('/')
    def index():
        logger.debug("Accessing index route")
        try:
            logger.debug("Rendering index template")
            return render_template('index.html')
        except Exception as e:
            logger.error(f"Error in index route: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/test')
    def test():
        """Simple test endpoint to verify the application is running"""
        return jsonify({
            "status": "ok",
            "message": "Application is running"
        })

    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            # Test file system
            os.access(app.config['UPLOAD_FOLDER'], os.W_OK)
            return jsonify({
                "status": "healthy",
                "database": "connected",
                "upload_folder": "accessible",
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }), 500

    @app.route('/env-check')
    def env_check():
        """Diagnostic endpoint to check environment variables"""
        try:
            # List of environment variables to check
            env_vars = {
                'DATABASE_URL': os.getenv('DATABASE_URL'),
                'POSTGRES_USER': os.getenv('POSTGRES_USER'),
                'POSTGRES_DB': os.getenv('POSTGRES_DB'),
                'RAILWAY_TCP_PROXY_DOMAIN': os.getenv('RAILWAY_TCP_PROXY_DOMAIN'),
                'RAILWAY_TCP_PROXY_PORT': os.getenv('RAILWAY_TCP_PROXY_PORT'),
                'PORT': os.getenv('PORT'),
                'RAILWAY_ENVIRONMENT_NAME': os.getenv('RAILWAY_ENVIRONMENT_NAME'),
                'RAILWAY_SERVICE_NAME': os.getenv('RAILWAY_SERVICE_NAME')
            }

            # Mask sensitive information
            masked_vars = env_vars.copy()
            if masked_vars.get('DATABASE_URL'):
                parts = masked_vars['DATABASE_URL'].split('@')
                if len(parts) > 1:
                    masked_vars['DATABASE_URL'] = f"...@{parts[1]}"

            # Check which variables are set
            status = {
                'missing_vars': [k for k, v in env_vars.items() if v is None],
                'set_vars': [k for k, v in env_vars.items() if v is not None],
                'values': masked_vars
            }

            return jsonify({
                'status': 'ok' if not status['missing_vars'] else 'warning',
                'environment': os.getenv('RAILWAY_ENVIRONMENT_NAME', 'unknown'),
                'service': os.getenv('RAILWAY_SERVICE_NAME', 'unknown'),
                'database_configured': bool(env_vars.get('DATABASE_URL')),
                'environment_check': status
            })
        except Exception as e:
            logger.error(f"Error checking environment variables: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    # Add all your other routes here...
    # Copy the remaining routes from app.py 