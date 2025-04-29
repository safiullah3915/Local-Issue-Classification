from datetime import datetime
from models import db


class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="Pending")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    department = db.Column(db.String(100))
    sent_to_department = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
