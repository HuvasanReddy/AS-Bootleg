from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import uuid
from utils.document_processor import DocumentProcessor, process_document
from utils.layer_manager import LayerManager
import json
from dotenv import load_dotenv
import base64

# Load environment variables
load_dotenv()

# Check for required environment variables
secret_key = os.getenv('SECRET_KEY')
if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable is required")

app = Flask(__name__)
app.config['SECRET_KEY'] = secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMPLATE_UPLOAD_FOLDER'] = os.path.join('uploads', 'user_templates')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'psd', 'ai', 'indd', 'jpg', 'jpeg', 'png', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ensure upload directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TEMPLATE_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'exports'), exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User model
class User(UserMixin, db.Model):
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
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    files = db.relationship('ProjectFile', backref='project', lazy=True)

# ProjectFile model
class ProjectFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    filepath = db.Column(db.String(200))  # Add filepath column
    layers = db.Column(db.Text)  # JSON string of layer data

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', projects=projects)

@app.route('/project/new', methods=['POST'])
@login_required
def create_project():
    name = request.form.get('name')
    description = request.form.get('description')
    
    project = Project(name=name, description=description, user_id=current_user.id)
    db.session.add(project)
    db.session.commit()
    
    return redirect(url_for('project', project_id=project.id))

@app.route('/project/<int:project_id>')
@login_required
def project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        flash('You do not have permission to view this project')
        return redirect(url_for('dashboard'))
    
    return render_template('project.html', project=project)

@app.route('/project/<int:project_id>/upload', methods=['POST'])
@login_required
def upload_file(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Process the file and extract layers
        layers = process_document(file_path)
        
        if isinstance(layers, dict) and 'error' in layers:
            os.remove(file_path)  # Clean up the file if processing failed
            return jsonify({'error': layers['error']}), 400
        
        # Save file information to database
        project_file = ProjectFile(
            filename=unique_filename,
            original_filename=filename,
            file_type=file.content_type,
            project_id=project_id,
            filepath=file_path,  # Store the filepath
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
    
    return jsonify({'error': 'File upload failed'}), 500

@app.route('/project/<int:project_id>/file/<int:file_id>/layers', methods=['GET'])
@login_required
def get_file_layers(project_id, file_id):
    project_file = ProjectFile.query.get_or_404(file_id)
    if project_file.project_id != project_id or project_file.project.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify(json.loads(project_file.layers))

@app.route('/project/<int:project_id>/file/<int:file_id>/export', methods=['POST'])
@login_required
def export_file(project_id, file_id):
    project_file = ProjectFile.query.get_or_404(file_id)
    if project_file.project_id != project_id or project_file.project.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    layer_data = request.json.get('layers', [])
    if not layer_data:
        return jsonify({'error': 'No layer data provided'}), 400
    
    # Process the file with the new layer data
    processor = DocumentProcessor()
    original_file = os.path.join(app.config['UPLOAD_FOLDER'], project_file.filename)
    export_filename = f"export_{project_file.filename}"
    export_path = os.path.join(app.config['UPLOAD_FOLDER'], 'exports', export_filename)
    
    try:
        processor.export_file(original_file, export_path, layer_data)
        return send_file(
            export_path,
            as_attachment=True,
            download_name=project_file.original_filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/batch-process', methods=['POST'])
@login_required
def batch_process():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files part'}), 400
    
    files = request.files.getlist('files[]')
    results = []
    
    for file in files:
        if file.filename == '':
            continue
        
        if file:
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Process the file and extract layers
            processor = DocumentProcessor()
            layers = processor.process_file(file_path)
            
            # Convert image data to base64 if present
            for layer in layers:
                if 'image_data' in layer:
                    layer['image_data'] = base64.b64encode(layer['image_data']).decode('utf-8')
                if 'locked' not in layer:
                    layer['locked'] = False
            
            # Create project with description
            project = Project(
                name=filename,
                description=f"Batch processed file: {filename}",
                user_id=current_user.id
            )
            db.session.add(project)
            
            # Save file information
            project_file = ProjectFile(
                filename=unique_filename,
                original_filename=filename,
                file_type=file.content_type,
                project_id=project.id,
                layers=json.dumps(layers)
            )
            db.session.add(project_file)
            
            results.append({
                'filename': filename,
                'success': True,
                'project_id': project.id,
                'file_id': project_file.id
            })
        else:
            results.append({
                'filename': file.filename,
                'success': False,
                'error': 'Invalid file type'
            })
    
    db.session.commit()
    return jsonify({'results': results})

@app.route('/api/update-layer', methods=['POST'])
@login_required
def update_layer():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        project_id = data.get('project_id')
        file_id = data.get('file_id')
        layer_id = data.get('layer_id')
        content = data.get('content')
        layer_type = data.get('layer_type')
        
        if not all([project_id, file_id, layer_id, content, layer_type]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Verify permissions
        project_file = ProjectFile.query.get_or_404(file_id)
        if project_file.project.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Load document and update layer
        lm = LayerManager()
        lm.load_document(project_file.filepath)
        result = lm.update_layer(layer_id, content, layer_type)
        
        if 'error' in result:
            return jsonify({'error': result['error']}), 400
        
        # Update layers in database
        layers = json.loads(project_file.layers)
        for i, layer in enumerate(layers):
            if layer['id'] == layer_id:
                layers[i] = result['layer']
                break
        
        project_file.layers = json.dumps(layers)
        db.session.commit()
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port) 