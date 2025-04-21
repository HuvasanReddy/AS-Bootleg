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

def create_app():
    # Load environment variables
    load_dotenv()

    # Initialize Flask app
    app = Flask(__name__)
    
    # Configure the app
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
    database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:DuiDSlJeUZaMptWBSALYMzDlSHembYvi@postgres-6sob.railway.internal:5432/railway')
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
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
    except Exception as e:
        logger.error(f"Error initializing extensions: {str(e)}")
        raise

    # Create upload directories
    try:
        logger.info("Creating upload directories...")
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['TEMPLATE_UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'exports'), exist_ok=True)
        logger.info("Upload directories created successfully")
    except Exception as e:
        logger.error(f"Error creating directories: {str(e)}")
        raise

    with app.app_context():
        # Import routes and models here to avoid circular imports
        from routes import register_routes
        register_routes(app)
        
        # Initialize database
        try:
            logger.info("Initializing database...")
            db.create_all()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise

    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask application on port {port}")
    app.run(host='0.0.0.0', port=port) 