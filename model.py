import os
import difflib
import smtplib
from email.message import EmailMessage
from groq import Groq
from models.issue import Issue
from models import db
from config import Config  

groq_api_key = Config.GROQ_API_KEY  

SMTP_SERVER = Config.MAIL_SERVER  
SMTP_PORT = Config.MAIL_PORT  
EMAIL_USERNAME = Config.MAIL_USERNAME  
EMAIL_PASSWORD = Config.MAIL_PASSWORD  
EMAIL_SENDER = Config.EMAIL_SENDER  

client = None
if groq_api_key:
    try:
        client = Groq(api_key=groq_api_key)
        print("✅ Groq API initialized successfully.")
    except Exception as e:
        print(f"❌ Error initializing Groq API: {e}")

department_mapping = {
    "police department": "Police Department",
    "health department": "Health Department",
    "education department": "Education Department",
    "public works department": "Public Works Department",
    "municipal committee": "Municipal Committee"
}

SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are an AI assistant that classifies user queries into the following departments: "
               "Police Department, Health Department, Education Department, Public Works Department, Municipal Committee. "
               "Only return one of these department names exactly as listed, without additional text."
}

def closest_match(department):
    """Finds the closest matching department from the predefined mapping."""
    matches = difflib.get_close_matches(department.lower(), department_mapping.keys(), n=1, cutoff=0.6)
    return department_mapping.get(matches[0], "Unrecognized department") if matches else "Unrecognized department"

def verify_groq_api():
    """Checks if the Groq API key is valid."""
    if not client:
        print("❌ Invalid Groq API Key. Ensure it is correctly set in `config.py`.")
        return False
    return True

def get_department_routing(user_query):
    """Classifies the user query and determines the relevant department."""
    if not verify_groq_api():
        return "API key is missing or invalid."

    try:
        messages = [
            SYSTEM_PROMPT,
            {"role": "user", "content": user_query}
        ]

        chat_completion = client.chat.completions.create(
            messages=messages,
            model="mixtral-8x7b-32768"
        )

        department = chat_completion.choices[0].message.content.strip()
        return closest_match(department)

    except Exception as e:
        return f"❌ Error calling LLM: {str(e)}"

def send_email(issue):
    """Sends an email with issue details to the assigned department using Mailtrap SMTP."""
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
    """Fetch and categorize unsent reports, then send email notifications."""
    if not verify_groq_api():
        return "Groq API not initialized. Cannot process issues."

    unsent_issues = Issue.query.filter_by(sent_to_department=False).all()

    if not unsent_issues:
        print("✅ No new reports to process.")
        return "No new reports to process."

    for issue in unsent_issues:
        assigned_department = get_department_routing(issue.description)

        issue.department = assigned_department
        issue.sent_to_department = send_email(issue)  
        db.session.commit()

        if issue.sent_to_department:
            print(f"🚀 Report ID {issue.id} sent to {assigned_department} department via email.")
        else:
            print(f"❌ Email failed for Report ID {issue.id}, but department is assigned.")

    return f"✅ {len(unsent_issues)} reports processed."
