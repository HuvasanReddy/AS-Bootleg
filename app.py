from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, send_file
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
from utils.document_processor import process_document
from utils.layer_manager import LayerManager
from utils.ai_service import AIService
from datetime import datetime
import json
from dotenv import load_dotenv
import uuid
from utils.document_processor import DocumentProcessor

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'psd', 'indd', 'png', 'jpg', 'jpeg'}

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
ai_service = AIService()

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'exports'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'templates'), exist_ok=True)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    projects = db.relationship('Project', backref='user', lazy=True)
    templates = db.relationship('Template', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    files = db.relationship('ProjectFile', backref='project', lazy=True)

class Template(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    file_path = db.Column(db.String(200))
    layers = db.Column(db.JSON)
    is_public = db.Column(db.Boolean, default=False)

class ProjectFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    layers = db.Column(db.Text)  # JSON string of layer data

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

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
            flash('Email already exists')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        return redirect(url_for('dashboard'))
    return render_template('register.html')

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
    
    if file:
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Process the file and extract layers
        processor = DocumentProcessor()
        layers = processor.process_file(file_path)
        
        # Save file information to database
        project_file = ProjectFile(
            filename=unique_filename,
            original_filename=filename,
            file_type=file.content_type,
            project_id=project_id,
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

# Template management endpoints
@app.route('/api/templates', methods=['GET'])
@login_required
def get_templates():
    templates = Template.query.filter(
        (Template.user_id == current_user.id) | (Template.is_public == True)
    ).all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'is_public': t.is_public,
        'created_at': t.created_at.isoformat()
    } for t in templates])

@app.route('/api/templates', methods=['POST'])
@login_required
def create_template():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'templates', f"{current_user.id}_{filename}")
        file.save(filepath)
        
        # Process the document
        layers = process_document(filepath)
        
        # Create template
        template = Template(
            name=filename,
            user_id=current_user.id,
            file_path=filepath,
            layers=layers,
            is_public=request.form.get('is_public', 'false').lower() == 'true'
        )
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'message': 'Template created successfully',
            'template_id': template.id
        })
    
    return jsonify({'error': 'Invalid file type'}), 400

# Batch processing endpoints
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
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{current_user.id}_{filename}")
            file.save(filepath)
            
            # Process the document
            layers = process_document(filepath)
            
            # Create project
            project = Project(
                name=filename,
                user_id=current_user.id,
                file_path=filepath
            )
            db.session.add(project)
            results.append({
                'filename': filename,
                'success': True,
                'project_id': project.id
            })
        else:
            results.append({
                'filename': file.filename,
                'success': False,
                'error': 'Invalid file type'
            })
    
    db.session.commit()
    return jsonify({'results': results})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port) 