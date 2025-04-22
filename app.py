from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_sqlalchemy import SQLAlchemy
# Temporarily comment out login imports
# from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid
import tempfile
import shutil
import logging
from utils.document_processor import DocumentProcessor, process_document
from utils.layer_manager import LayerManager
import json
from dotenv import load_dotenv
import base64
from schemas import UpdateLayerSchema, BatchProcessSchema, UploadFileSchema
from extensions import init_extensions

# Configure logging with more details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_db_connection(app):
    """Verify database connection and log detailed information"""
    from sqlalchemy import text
    with app.app_context():
        try:
            # Get database URL (mask password for logging)
            db_url = app.config['SQLALCHEMY_DATABASE_URI']
            masked_url = db_url.replace(db_url.split(':')[2].split('@')[0], '****')
            logger.info(f"Attempting to connect to database: {masked_url}")

            # Test connection
            db.session.execute(text('SELECT 1'))
            db.session.commit()
            logger.info("Database connection successful!")

            # Get database info
            result = db.session.execute(text('SELECT version();')).scalar()
            logger.info(f"Database version: {result}")

            return True
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            return False

def create_app():
    # Load environment variables
    load_dotenv()

    # Initialize Flask app
    app = Flask(__name__)
    
    # Configure the app
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Use DATABASE_URL from environment, or construct it from individual components
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Construct URL from individual components
        db_user = os.getenv('POSTGRES_USER', 'postgres')
        db_password = os.getenv('POSTGRES_PASSWORD')
        db_host = os.getenv('RAILWAY_TCP_PROXY_DOMAIN', 'containers-us-west-34.railway.app')
        db_port = os.getenv('RAILWAY_TCP_PROXY_PORT', '7386')
        db_name = os.getenv('POSTGRES_DB', 'railway')
        
        if not all([db_user, db_password, db_host, db_port, db_name]):
            logger.warning("Some database configuration values are missing, using default SQLite database")
            database_url = 'sqlite:///app.db'
        else:
            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            logger.info(f"Constructed database URL from Railway components (user: {db_user}, host: {db_host}, port: {db_port}, db: {db_name})")

    # Convert postgres:// to postgresql:// if necessary
    if database_url and database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
        logger.info("Converted postgres:// to postgresql:// in database URL")
        
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['TEMPLATE_UPLOAD_FOLDER'] = os.path.join('uploads', 'user_templates')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

    # Initialize extensions in the correct order
    try:
        logger.info("Initializing CORS...")
        CORS(app)
        
        logger.info("Initializing extensions...")
        init_extensions(app)
        logger.info("Extensions initialized successfully")

        # Verify database connection
        if not verify_db_connection(app):
            logger.error("Failed to verify database connection")
            raise Exception("Database connection verification failed")
        
    except Exception as e:
        logger.error(f"Error during initialization: {str(e)}")
        # Don't raise the error, let the app continue with reduced functionality
        pass

    # Create upload directories
    try:
        logger.info("Creating upload directories...")
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['TEMPLATE_UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'exports'), exist_ok=True)
        logger.info("Upload directories created successfully")
    except Exception as e:
        logger.error(f"Error creating directories: {str(e)}")
        # Don't raise the error, let the app continue with reduced functionality
        pass

    with app.app_context():
        # Import routes and models here to avoid circular imports
        from routes import register_routes
        register_routes(app)
        
        # Initialize database
        try:
            logger.info("Initializing database tables...")
            db.create_all()
            logger.info("Database tables initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            # Don't raise the error, let the app continue with reduced functionality
            pass

    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask application on port {port}")
    app.run(host='0.0.0.0', port=port) 