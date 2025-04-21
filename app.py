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

# Configure logging with more details
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check for required environment variables
secret_key = os.getenv('SECRET_KEY', 'dev-secret-key')  # Provide default for development
database_url = os.getenv('DATABASE_URL', 'sqlite:///app.db')
port = int(os.environ.get('PORT', 5000))  # Updated port configuration

logger.info(f"Starting application with database: {database_url}")
logger.info(f"Port configured as: {port}")

# Initialize Flask app with static folder configuration
app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMPLATE_UPLOAD_FOLDER'] = os.path.join('uploads', 'user_templates')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize CORS with more permissive settings for testing
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize database and migrations
db = SQLAlchemy(app)
migrate = Migrate(app, db)
ma = Marshmallow(app)

# Create upload directories if they don't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMPLATE_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'exports'), exist_ok=True)

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'psd', 'ai', 'indd', 'jpg', 'jpeg', 'png', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Error handlers
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}")
    return render_template('error.html', error="An internal error occurred. Please try again later."), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error="Page not found"), 404

# Comment out login manager initialization
# login_manager = LoginManager()
# login_manager.init_app(app)
# login_manager.login_view = 'login'
# login_manager.login_message = 'Please log in to access this page.'

# User model (keep for database structure)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    projects = db.relationship('Project', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Project model
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Make nullable
    files = db.relationship('ProjectFile', backref='project', lazy=True)

# ProjectFile model
class ProjectFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    filepath = db.Column(db.String(200))
    layers = db.Column(db.Text)  # JSON string of layer data

@app.route('/')
def index():
    logger.debug("Accessing index route")
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        return str(e), 500

@app.route('/test')
def test():
    """Simple test endpoint to verify the application is running"""
    return jsonify({
        "status": "ok",
        "message": "Application is running"
    })

@app.route('/health')
def health_check():
    logger.debug("Health check requested")
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        # Test file system
        os.access(app.config['UPLOAD_FOLDER'], os.W_OK)
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "upload_folder": "accessible"
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route('/dashboard')
def dashboard():
    # Get all projects instead of user-specific ones
    projects = Project.query.all()
    return render_template('dashboard.html', projects=projects)

@app.route('/project/new', methods=['POST'])
def create_project():
    name = request.form.get('name')
    description = request.form.get('description')
    
    # Create project without user_id
    project = Project(name=name, description=description)
    db.session.add(project)
    db.session.commit()
    
    return redirect(url_for('project', project_id=project.id))

@app.route('/project/<int:project_id>')
def project(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project.html', project=project)

@app.route('/project/<int:project_id>/upload', methods=['POST'])
def upload_file(project_id):
    try:
        # Validate request data
        data = UploadFileSchema().load({
            'file': request.files.get('file'),
            'project_id': project_id
        })
    except ValidationError as err:
        return jsonify(err.messages), 400

    project = Project.query.get_or_404(project_id)
    
    file = data['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file.save(tmp.name)
            # Process the file and extract layers
            layers = process_document(tmp.name)
            
            if isinstance(layers, dict) and 'error' in layers:
                os.unlink(tmp.name)
                return jsonify({'error': layers['error']}), 400
            
            # Generate unique filename
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Move the temporary file
            shutil.move(tmp.name, file_path)
            
            # Save file information
            project_file = ProjectFile(
                filename=unique_filename,
                original_filename=filename,
                file_type=file.content_type,
                project_id=project_id,
                filepath=file_path,
                layers=json.dumps(layers)
            )
            db.session.add(project_file)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'file_id': project_file.id,
                'filename': filename,
                'layers': layers
            })
    except Exception as e:
        if 'tmp' in locals() and os.path.exists(tmp.name):
            os.unlink(tmp.name)
        return jsonify({'error': str(e)}), 500

@app.route('/project/<int:project_id>/file/<int:file_id>/layers', methods=['GET'])
def get_file_layers(project_id, file_id):
    project_file = ProjectFile.query.get_or_404(file_id)
    return jsonify(json.loads(project_file.layers))

@app.route('/project/<int:project_id>/file/<int:file_id>/export', methods=['POST'])
def export_file(project_id, file_id):
    project_file = ProjectFile.query.get_or_404(file_id)
    
    layer_data = request.json.get('layers', [])
    if not layer_data:
        return jsonify({'error': 'No layer data provided'}), 400
    
    try:
        # Initialize LayerManager and load the document
        lm = LayerManager()
        lm.load_document(project_file.filepath)
        
        # Update layers
        for layer in layer_data:
            if layer['id'] in lm._layers:
                lm._layers[layer['id']].update(layer)
        
        # Export the document
        result = lm.export_document(size='square', format='png')
        
        if result['success']:
            return send_file(
                result['path'],
                as_attachment=True,
                download_name=f"{project_file.original_filename.rsplit('.', 1)[0]}_export.png"
            )
        else:
            return jsonify({'error': result.get('message', 'Export failed')}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/batch-process', methods=['POST'])
def batch_process():
    try:
        # Validate request data
        data = BatchProcessSchema().load({
            'files': request.files.getlist('files[]')
        })
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    files = data['files']
    results = []
    
    for file in files:
        if file.filename == '':
            continue
        
        if file:
            try:
                # Create a temporary file
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    file.save(tmp.name)
                    
                    # Process the file and extract layers
                    processor = DocumentProcessor()
                    layers = processor.process_file(tmp.name)
                    
                    # Convert image content to base64
                    for layer in layers:
                        if 'content' in layer and isinstance(layer['content'], (bytes, bytearray)):
                            layer['content'] = base64.b64encode(layer['content']).decode('utf-8')
                        if 'locked' not in layer:
                            layer['locked'] = False
                    
                    # Generate unique filename
                    filename = secure_filename(file.filename)
                    unique_filename = f"{uuid.uuid4()}_{filename}"
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    
                    # Move the temporary file
                    shutil.move(tmp.name, file_path)
                    
                    # Create project
                    project = Project(
                        name=filename,
                        description=f"Batch processed file: {filename}"
                    )
                    db.session.add(project)
                    db.session.flush()
                    
                    # Save file information
                    project_file = ProjectFile(
                        filename=unique_filename,
                        original_filename=filename,
                        file_type=file.content_type,
                        project_id=project.id,
                        filepath=file_path,
                        layers=json.dumps(layers)
                    )
                    db.session.add(project_file)
                    
                    results.append({
                        'filename': filename,
                        'success': True,
                        'project_id': project.id,
                        'file_id': project_file.id
                    })
            except Exception as e:
                if 'tmp' in locals() and os.path.exists(tmp.name):
                    os.unlink(tmp.name)
                results.append({
                    'filename': file.filename,
                    'success': False,
                    'error': str(e)
                })
    
    db.session.commit()
    return jsonify({'results': results})

@app.route('/api/update-layer', methods=['POST'])
def update_layer():
    try:
        # Validate request data
        data = UpdateLayerSchema().load(request.json)
    except ValidationError as err:
        return jsonify(err.messages), 400
    
    try:
        project_file = ProjectFile.query.get_or_404(data['file_id'])
        
        # Verify project_id matches
        if data['project_id'] != project_file.project_id:
            return jsonify({'error': 'Bad project_id'}), 400
        
        # Load document and update layer
        lm = LayerManager()
        lm.load_document(project_file.filepath)
        result = lm.update_layer(data['layer_id'], data['content'], data['layer_type'])
        
        if 'error' in result:
            return jsonify({'error': result['error']}), 400
        
        # Update layers in database
        layers = json.loads(project_file.layers)
        for i, layer in enumerate(layers):
            if layer['id'] == data['layer_id']:
                layers[i] = result['layer']
                break
        
        project_file.layers = json.dumps(layers)
        db.session.commit()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.before_first_request
def initialize_database():
    try:
        logger.info("Initializing database...")
        db.create_all()
        # Check if admin user exists, if not create one
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            logger.info("Admin user created successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        db.session.rollback()

if __name__ == '__main__':
    with app.app_context():
        try:
            logger.info("Initializing database...")
            db.create_all()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
    
    logger.info(f"Starting Flask application on port {port}")
    app.run(host='0.0.0.0', port=port) 