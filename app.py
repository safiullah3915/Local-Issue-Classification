import threading
import time
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from routes.cache.config import Config
from models import db
from models.issue import Issue
from routes.cache.email import process_unsent_issues  , process_overdue_issues

app = Flask(__name__)
app.config.from_object(Config)

CORS(app, supports_credentials=True) 


db.init_app(app)

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

from routes.auth import auth_blueprint
from routes.issues import issues_blueprint
from routes.models import models_blueprint

app.register_blueprint(auth_blueprint, url_prefix="/api/auth")
app.register_blueprint(issues_blueprint, url_prefix="/api/issues")
app.register_blueprint(models_blueprint, url_prefix="/api/models")

def run_background_task():
    """ Periodically checks for new reports and categorizes them """
    while True:
        with app.app_context():
            process_unsent_issues()
            process_overdue_issues()
        time.sleep(50)  

threading.Thread(target=run_background_task, daemon=True).start()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  
    app.run(debug=True)
