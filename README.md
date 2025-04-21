# Creative Automation Tool

A web-based tool for automating creative workflows, allowing users to upload, edit, and export PSD and InDesign files.

## Features

- User authentication and project management
- Upload and process PSD and InDesign files
- Layer management with text and image editing
- Real-time preview of changes
- Export to multiple formats and sizes
- Responsive web interface

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)
- Heroku CLI (for deployment)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/creative-automation-tool.git
cd creative-automation-tool
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory with the following content:
```
SECRET_KEY=your-secret-key-here
```

5. Initialize the database:
```bash
flask db upgrade
```

## Running the Application

1. Start the development server:
```bash
python app.py
```

2. Access the application at `http://localhost:5000`

## Deployment

### Heroku Deployment

1. Install the Heroku CLI:
```bash
# macOS
brew tap heroku/brew && brew install heroku

# Windows
choco install heroku-cli

# Ubuntu
sudo snap install heroku --classic
```

2. Login to Heroku:
```bash
heroku login
```

3. Create a new Heroku app:
```bash
heroku create your-app-name
```

4. Set up environment variables:
```bash
heroku config:set SECRET_KEY=your-secret-key-here
```

5. Add the Heroku PostgreSQL addon:
```bash
heroku addons:create heroku-postgresql:hobby-dev
```

6. Deploy to Heroku:
```bash
git add .
git commit -m "Initial deployment"
git push heroku main
```

7. Initialize the database:
```bash
heroku run flask db upgrade
```

8. Open the application:
```bash
heroku open
```

### Alternative Deployment Options

#### 1. DigitalOcean App Platform

1. Install the DigitalOcean CLI:
```bash
# macOS
brew install doctl

# Windows
choco install doctl

# Ubuntu
snap install doctl
```

2. Login to DigitalOcean:
```bash
doctl auth init
```

3. Create a new app:
```bash
doctl apps create --spec app.yaml
```

4. Set up environment variables:
```bash
doctl apps update <app-id> --spec app.yaml
```

#### 2. AWS Elastic Beanstalk

1. Install the AWS CLI:
```bash
# macOS
brew install awscli

# Windows
choco install awscli

# Ubuntu
sudo apt install awscli
```

2. Configure AWS credentials:
```bash
aws configure
```

3. Create an Elastic Beanstalk environment:
```bash
eb init -p python-3.9 creative-automation-tool
eb create production
```

4. Deploy your application:
```bash
eb deploy
```

#### 3. Google Cloud Run

1. Install the Google Cloud SDK:
```bash
# macOS
brew install google-cloud-sdk

# Windows
choco install google-cloud-sdk

# Ubuntu
sudo apt-get install google-cloud-sdk
```

2. Initialize and login:
```bash
gcloud init
```

3. Build and deploy:
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/creative-automation-tool
gcloud run deploy --image gcr.io/PROJECT_ID/creative-automation-tool
```

#### 4. PythonAnywhere (Free Tier)
- Free tier includes:
  - 1 web app
  - 512MB disk space
  - 100 seconds CPU time per day
  - Custom domain support
  - SSL support
- Steps:
  1. Create a free account at [PythonAnywhere](https://www.pythonanywhere.com)
  2. Upload your code using Git or the web interface
  3. Set up a web app in the Web tab
  4. Configure your WSGI file
  5. Set up environment variables in the Web tab
  6. Reload your web app

#### 5. Render (Free Tier)
- Free tier includes:
  - 750 hours/month of runtime
  - Automatic HTTPS
  - Custom domains
  - Continuous deployment from Git
- Steps:
  1. Create a free account at [Render](https://render.com)
  2. Connect your GitHub repository
  3. Create a new Web Service
  4. Configure:
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `gunicorn app:app`
  5. Add environment variables
  6. Deploy

#### 6. Railway (Free Tier)
- Free tier includes:
  - 500 hours/month of runtime
  - 1GB disk space
  - Automatic HTTPS
  - Custom domains
- Steps:
  1. Create a free account at [Railway](https://railway.app)
  2. Connect your GitHub repository
  3. Create a new project
  4. Add environment variables
  5. Deploy

#### 7. Fly.io (Free Tier)
- Free tier includes:
  - 3 shared-cpu-1x 256MB VMs
  - 3GB persistent volume storage
  - 160GB outbound data transfer
- Steps:
  1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
  2. Login: `fly auth login`
  3. Launch app: `fly launch`
  4. Deploy: `fly deploy`

### Important Notes for Free Tiers

1. **Resource Limitations**:
   - Free tiers have limited CPU, memory, and storage
   - Some services may sleep after inactivity
   - Check the specific limits for each platform

2. **Database Options**:
   - For free database hosting, consider:
     - ElephantSQL (free tier)
     - Supabase (free tier)
     - Railway's free PostgreSQL
     - Neon (free tier)

3. **File Storage**:
   - For file uploads, consider:
     - AWS S3 (free tier)
     - Google Cloud Storage (free tier)
     - Cloudinary (free tier)

4. **Best Practices**:
   - Monitor your resource usage
   - Implement proper error handling
   - Use environment variables for sensitive data
   - Set up proper logging
   - Consider implementing a backup strategy

### Environment Variables

The following environment variables are required for production:

- `SECRET_KEY`: A secret key for Flask session management
- `DATABASE_URL`: The database URL (automatically set by Heroku)
- `PORT`: The port to run the application on (automatically set by Heroku)

## Project Structure

```
creative-automation-tool/
├── app.py              # Main application file
├── requirements.txt    # Python dependencies
├── Procfile           # Heroku process file
├── runtime.txt        # Python runtime version
├── static/            # Static files (CSS, JS, images)
│   ├── css/
│   └── js/
├── templates/         # HTML templates
├── uploads/          # Uploaded files
└── utils/            # Utility modules
```

## Usage

1. Register a new account or log in
2. Upload a PSD or InDesign file
3. Edit layers (text, images)
4. Preview changes in real-time
5. Export the final design

## API Endpoints

- `POST /upload` - Upload a new project file
- `POST /update-layer` - Update layer content
- `POST /export` - Export project to different formats
- `GET /project/<id>` - View project details
- `PUT /project/<id>` - Update project
- `DELETE /project/<id>` - Delete project

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the GitHub repository or contact the maintainers.

## Acknowledgments

- Flask framework
- PSD Tools library
- Tailwind CSS 