from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
ma = Marshmallow()

def init_extensions(app):
    """Initialize Flask extensions in the correct order"""
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialize Marshmallow after SQLAlchemy
    with app.app_context():
        ma.init_app(app) 