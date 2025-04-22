ALLOWED_EXTENSIONS = {'psd', 'ai', 'indd', 'jpg', 'jpeg', 'png', 'gif'}

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS 