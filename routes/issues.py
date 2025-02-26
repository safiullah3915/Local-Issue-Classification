from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.issue import Issue
from models import db

issues_blueprint = Blueprint("issues", __name__)

@issues_blueprint.route("/report", methods=["POST"])
@jwt_required()
def report_issue():
    """Allows users to submit a new issue report."""
    data = request.get_json()
    if not data or "description" not in data:
        return jsonify({"error": "Issue description is required"}), 400

    user_id = get_jwt_identity()

    new_issue = Issue(
        description=data["description"],
        user_id=user_id,
        status="Pending",  
        department=None,  
        sent_to_department=False  
    )

    db.session.add(new_issue)
    db.session.commit()

    return jsonify({"message": "Issue reported successfully", "issue_id": new_issue.id}), 201


@issues_blueprint.route("/status", methods=["GET"])
@jwt_required()
def get_issue_status():
    issue_id = request.args.get("id")
    if not issue_id:
        return jsonify({"error": "Issue ID is required"}), 400

    issue = Issue.query.get(issue_id)
    if not issue:
        return jsonify({"error": "Issue not found"}), 404

    return jsonify({
        "issue_id": issue.id,
        "description": issue.description,
        "status": issue.status,
        "department": issue.department if issue.department else "Not Assigned",
        "sent_to_department": bool(issue.sent_to_department)  # ✅ Explicit conversion
    }), 200



@issues_blueprint.route("/user-reports", methods=["GET"])
@jwt_required()
def get_user_issues():
    """ Fetch all reports submitted by the logged-in user """
    user_id = get_jwt_identity()

    issues = Issue.query.filter_by(user_id=user_id).all()
    
    issues_list = [{
        "id": issue.id,
        "description": issue.description,
        "status": issue.status,
        "department": issue.department if issue.department else "Pending"
    } for issue in issues]

    return jsonify({"issues": issues_list}), 200
