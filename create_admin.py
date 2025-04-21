from app import db, User
from werkzeug.security import generate_password_hash

def create_admin_account():
    # Create database tables
    db.create_all()
    
    # Check if admin already exists
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        # Create admin user
        admin = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin account created successfully!")
    else:
        print("Admin account already exists!")

if __name__ == '__main__':
    create_admin_account() 