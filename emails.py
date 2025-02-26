import os
import joblib
import smtplib
import pandas as pd
from email.message import EmailMessage
from models.issue import Issue
from models.ml_model import MLModel  
from models import db

MODEL_FOLDER = "mlmodels"

SMTP_SERVER = "sandbox.smtp.mailtrap.io"
SMTP_PORT = "2525"
EMAIL_USERNAME = "ed2401c6fea2db"
EMAIL_PASSWORD = "e85f9de532580a"
EMAIL_SENDER = "noreply@yourapp.com"

def load_model(model_name):
    """Loads a trained ML model from the mlmodels folder."""
    model_path = os.path.join(MODEL_FOLDER, f"{model_name.lower()}_model.pkl")
    if os.path.exists(model_path):
        return joblib.load(model_path)
    return None

def get_selected_model():
    """Fetches the currently selected ML model from the database."""
    model_entry = MLModel.query.first()
    return model_entry.model_name if model_entry else "kmeans" 

def classify_issue_with_ml(issue_description):
    """Classifies the issue description using the currently selected ML model."""
    model_name = get_selected_model()
    model = load_model(model_name)
    
    if model is None:
        return "Unrecognized department" 
    
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        tfidf = TfidfVectorizer(max_features=1000)
        X_test = tfidf.fit_transform([issue_description])

        prediction = model.predict(X_test.toarray())[0]

        department_mapping = {
            0: "Police Department",
            1: "Health Department",
            2: "Education Department",
            3: "Public Works Department",
            4: "Municipal Committee"
        }

        return department_mapping.get(prediction, "Unrecognized department")

    except Exception as e:
        print(f"❌ Error classifying issue: {e}")
        return "Unrecognized department"

def send_email(issue):
    """Sends an email with issue details to the assigned department."""
    try:
        subject = f"New Issue Report - {issue.department}"
        body = f"""
        🚨 New Issue Report 🚨
        ---------------------------------
        📌 Report ID: {issue.id}
        📝 Description: {issue.description}
        🏢 Assigned Department: {issue.department}
        📧 Sent to: trendbussiness.3915@gmail.com
        ---------------------------------
        Please take action accordingly.
        """

        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = "trendbussiness.3915@gmail.com"  

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)  
        server.send_message(msg)
        server.quit()

        print(f"📧 Email sent successfully for Report ID {issue.id} to {issue.department}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email for Report ID {issue.id}: {e}")
        return False

def process_unsent_issues():
    """Fetch and categorize unsent reports using the selected ML model, then send email notifications."""
    unsent_issues = Issue.query.filter_by(sent_to_department=False).all()

    if not unsent_issues:
        print("✅ No new reports to process.")
        return "No new reports to process."

    for issue in unsent_issues:

        assigned_department = classify_issue_with_ml(issue.description)

        issue.department = assigned_department
        issue.sent_to_department = send_email(issue)
        db.session.commit()

        if issue.sent_to_department:
            print(f"🚀 Report ID {issue.id} sent to {assigned_department} department via email.")
        else:
            print(f"❌ Email failed for Report ID {issue.id}, but department is assigned.")

    return f"✅ {len(unsent_issues)} reports processed."
