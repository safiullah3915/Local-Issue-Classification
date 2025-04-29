import difflib
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta
from groq import Groq
from models.issue import Issue
from models import db
from routes.cache.config import Config

groq_api_key = Config.GROQ_API_KEY

SMTP_SERVER = Config.MAIL_SERVER
SMTP_PORT = Config.MAIL_PORT
EMAIL_USERNAME = Config.MAIL_USERNAME
EMAIL_PASSWORD = Config.MAIL_PASSWORD
EMAIL_SENDER = Config.EMAIL_SENDER

SUPER_FOCAL_EMAIL = "trendbussiness.3915@gmail.com"

client = None
if groq_api_key:
    try:
        client = Groq(api_key=groq_api_key)
    except Exception:
        print("")

department_mapping = {
    "police department": "Police Department",
    "health department": "Health Department",
    "education department": "Education Department",
    "public works department": "Public Works Department",
    "traffic police department": "Traffic Police Department",
}

SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are an AI assistant specialized in analyzing detailed user queries regarding municipal issues. "
        "Your task is to deeply analyze each query and map it to the most appropriate department from the list: "
        "Police Department, Health Department, Education Department, Public Works Department, Traffic Police Department. "
        "Return only the department name—no extra text."
    ),
}


def closest_match(department):
    matches = difflib.get_close_matches(
        department.lower(), department_mapping.keys(), n=1, cutoff=0.6
    )
    return (
        department_mapping.get(matches[0], "Unrecognized department") if matches else "Unrecognized department"
    )


def verify_groq_api():
    return bool(client)


def get_department_routing(user_query):
    if not verify_groq_api():
        return "API key is missing or invalid."

    try:
        messages = [SYSTEM_PROMPT, {"role": "user", "content": user_query}]

        chat_completion = client.chat.completions.create(
            messages=messages, model="mistral-saba-24b"
        )

        department = chat_completion.choices[0].message.content.strip()
        return closest_match(department)

    except Exception:
        return ""


def send_email(issue):
    """Send the main department email."""
    try:
        subject = f"New Issue Report - {issue.department}"
        body = f"""
        🚨 New Issue Report 🚨
        ---------------------------------
        📌 Report ID: {issue.id}
        📝 Description: {issue.description}
        🏢 Assigned Department: {issue.department}
        📅 Reported On: {issue.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        ---------------------------------
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

        print(f"📧 Email sent successfully for Report ID {issue.id}")
        return True

    except Exception as e:
        print(f"❌ Failed to send email for Report ID {issue.id}: {e}")
        return False

def notify_super_focal(issue):
    try:
        subject = f"⚠️ Overdue Issue (14 days)  Report ID {issue.id}"
        body = f"""
        ⚠️ Pending Issue Exceeded 14 Days ⚠️
        ---------------------------------
        📌 Report ID: {issue.id}
        📝 Description: {issue.description}
        🏢 Assigned Department: {issue.department or 'Not Assigned'}
        ⏳ Status: {issue.status}
        📅 Reported On: {issue.created_at.strftime('%Y-%m-%d %H:%M:%S')}
        ---------------------------------
        Immediate attention required.
        """

        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = SUPER_FOCAL_EMAIL

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"📧 Super Focal Person notified for Report ID {issue.id}")
        return True

    except Exception as e:
        print(f"❌ Failed to notify Super Focal Person for Report ID {issue.id}: {e}")
        return False


def process_overdue_issues():
    fourteen_days_ago = datetime.utcnow() - timedelta(days=14)

    overdue_issues = (
        Issue.query.filter(Issue.status == "Pending")
        .filter(Issue.created_at <= fourteen_days_ago)
        .all()
    )

    if not overdue_issues:
        print("✅ No overdue issues detected.")
        return "No overdue issues."

    for issue in overdue_issues:
        notify_super_focal(issue)

    return f"📢 {len(overdue_issues)} overdue issues forwarded to Super Focal Person."


def process_unsent_issues():
    if not verify_groq_api():
        return "Groq API not initialized. Cannot process issues."

    unsent_issues = Issue.query.filter_by(sent_to_department=False).all()
    if not unsent_issues:
        print("✅ No new reports to process.")
        return "No new reports to process."

    for issue in unsent_issues:
        issue.department = get_department_routing(issue.description)
        issue.sent_to_department = send_email(issue)
        db.session.commit()

    return f"{len(unsent_issues)} reports processed."
