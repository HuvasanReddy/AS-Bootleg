from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
from utils.document_processor import process_document
from utils.layer_manager import LayerManager
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'psd', 'indd'}

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'exports'), exist_ok=True)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    projects = db.relationship('Project', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    file_path = db.Column(db.String(200))
    layers = db.Column(db.JSON)

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

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{current_user.id}_{filename}")
        file.save(filepath)
        
        # Create project
        project = Project(
            name=filename,
            user_id=current_user.id,
            file_path=filepath
        )
        db.session.add(project)
        
        # Process the document
        layers = process_document(filepath)
        project.layers = layers
        db.session.commit()
        
        return jsonify({
            'message': 'File uploaded successfully',
            'layers': layers,
            'project_id': project.id
        })
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/update-layer', methods=['POST'])
@login_required
def update_layer():
    data = request.json
    layer_id = data.get('layer_id')
    content = data.get('content')
    layer_type = data.get('type')
    project_id = data.get('project_id')
    
    if not all([layer_id, content, layer_type, project_id]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    # Update the layer
    result = LayerManager.update_layer(layer_id, content, layer_type)
    return jsonify(result)

@app.route('/export', methods=['POST'])
@login_required
def export_document():
    data = request.json
    size = data.get('size')
    format = data.get('format', 'png')
    project_id = data.get('project_id')
    
    if not all([size, project_id]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first()
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    
    # Export the document
    result = LayerManager.export_document(size, format)
    return jsonify(result)

@app.route('/project/<int:project_id>')
@login_required
def view_project(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    return render_template('project.html', project=project)

@app.route('/project/<int:project_id>', methods=['PUT'])
@login_required
def update_project(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    
    # Update project data
    data = request.json
    if 'name' in data:
        project.name = data['name']
    if 'layers' in data:
        project.layers = data['layers']
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/project/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    
    # Delete associated files
    if project.file_path and os.path.exists(project.file_path):
        os.remove(project.file_path)
    
    db.session.delete(project)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/project/<int:project_id>/export', methods=['POST'])
@login_required
def export_project(project_id):
    project = Project.query.filter_by(id=project_id, user_id=current_user.id).first_or_404()
    
    data = request.json
    size = data.get('size', 'square')
    format = data.get('format', 'png')
    
    # Export the document
    result = LayerManager.export_document(size, format)
    
    # Create a unique filename for the export
    export_filename = f"{project.name}_{size}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
    export_path = os.path.join(app.config['UPLOAD_FOLDER'], 'exports', export_filename)
    
    # Ensure exports directory exists
    os.makedirs(os.path.dirname(export_path), exist_ok=True)
    
    # Save the exported file
    result['image'].save(export_path)
    
    return jsonify({
        'success': True,
        'path': f"/static/exports/{export_filename}",
        'format': format
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 