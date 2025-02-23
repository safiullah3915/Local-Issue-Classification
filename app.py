import threading
import time
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from models import db
from models.issue import Issue
from model import process_unsent_issues  # Import function to categorize and send reports

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS
CORS(app)

# Initialize database
db.init_app(app)

# Initialize JWT
jwt = JWTManager(app)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/model-selection")
def model_selection():
    return render_template("model_selection.html")

@app.route("/report-issue")
def report_issue():
    return render_template("report_issue.html")

@app.route("/track-status")
def track_status():
    return render_template("trackstatus.html")

@app.route("/train-test-model")
def train_test_model():
    return render_template("traintestmodel.html")

# Import and register blueprints
from routes.auth import auth_blueprint
from routes.issues import issues_blueprint
from routes.models import models_blueprint

app.register_blueprint(auth_blueprint, url_prefix="/api/auth")
app.register_blueprint(issues_blueprint, url_prefix="/api/issues")
app.register_blueprint(models_blueprint, url_prefix="/api/models")

# Background Task for Processing Unsent Reports
def run_background_task():
    """ Periodically checks for new reports and categorizes them """
    while True:
        with app.app_context():
            process_unsent_issues()
        time.sleep(50)  # Run every 5 minutes (300 seconds)

# Start background task in a separate thread
threading.Thread(target=run_background_task, daemon=True).start()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Ensure database tables are created
    app.run(debug=True)
