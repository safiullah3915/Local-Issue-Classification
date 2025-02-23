from flask import Blueprint, request, jsonify, session
from flask_jwt_extended import create_access_token
from models.user import User
from models import db
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

auth_blueprint = Blueprint("auth", __name__)

@auth_blueprint.route("/register", methods=["POST"])
def register_user():
    data = request.get_json()

    if not data.get("email") or not data.get("password") or not data.get("user_type"):
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "User already exists"}), 400

    new_user = User(email=data["email"], user_type=data["user_type"])
    new_user.set_password(data["password"])
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"}), 201

@auth_blueprint.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    user = User.query.filter_by(email=data["email"]).first()
    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"email": user.email, "user_type": user.user_type}
    )

    return jsonify({
        "message": "Login successful",
        "token": access_token,
        "user_email": user.email,
        "user_type": user.user_type
    }), 200


@auth_blueprint.route("/get_user", methods=["GET"])
def get_user():
    user_email = session.get("user_email")

    if not user_email:
        return jsonify({"error": "User session not found"}), 401

    return jsonify({"user_email": user_email}), 200

