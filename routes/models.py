import os
import json
import joblib
import pandas as pd
from flask import Blueprint, request, jsonify, Response, stream_with_context
import time
from flask_jwt_extended import get_jwt, jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

models_blueprint = Blueprint("models", __name__)

MODEL_FOLDER = "mlmodels"
TEMP_PARAM_FILE = "train_params.json"

if not os.path.exists(MODEL_FOLDER):
    os.makedirs(MODEL_FOLDER)


def load_model(model_name):
    """ Load a pre-trained model from disk with compatibility handling """
    model_path = os.path.join(MODEL_FOLDER, f"{model_name.lower()}_model.pkl")

    if not os.path.exists(model_path):
        print(f"❌ Error: Model file '{model_path}' not found.")
        return None  # Prevents Flask from crashing

    try:
        return joblib.load(model_path)  # No fix_imports=True (caused issues in testing)
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        return None  # Prevents errors from stopping execution


from flask_jwt_extended import get_jwt, verify_jwt_in_request  
import subprocess

@models_blueprint.route("/train", methods=["POST"])
@jwt_required()
def train_model():
    """ Trains the selected model with user-specified hyperparameters """

    verify_jwt_in_request()
    claims = get_jwt()
    user_type = claims.get("user_type")

    if not user_type or user_type != "super":
        return jsonify({"error": "Unauthorized! Only super users can train models"}), 403

    file = request.files.get("file")
    model_name = request.form.get("model")

    if not file or not model_name:
        return jsonify({"error": "Missing required fields"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join("uploads", filename)
    file.save(file_path)

    # ✅ Get hyperparameters
    hyperparameters = {key: request.form[key] for key in request.form if key not in ["file", "model"]}

    # ✅ Save parameters to JSON
    PARAMS_FILE = "train_params.json"
    params = {
        "dataset_path": file_path,
        "model": model_name,
        "hyperparameters": hyperparameters
    }
    with open(PARAMS_FILE, "w") as f:
        json.dump(params, f)

    # ✅ Correctly run Jupyter Notebook (NO ARGUMENTS, just executes normally)
    try:
        subprocess.run(["jupyter", "nbconvert", "--execute", "train.ipynb", "--to", "notebook", "--output", "train_output.ipynb", "--ExecutePreprocessor.timeout=600"], check=True)
        return jsonify({"message": f"{model_name} trained successfully!"}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Training failed: {str(e)}"}), 500


@models_blueprint.route("/test", methods=["POST"])
@jwt_required()
def test_model():
    """ Tests a model using uploaded data and returns evaluation metrics """
    file = request.files.get("file")
    model_name = request.form.get("model")

    if not file or not model_name:
        return jsonify({"error": "Missing required fields"}), 400

    model = load_model(model_name)
    if model is None:
        return jsonify({"error": f"Model '{model_name}' not found or incompatible. Please retrain it."}), 404

    filename = secure_filename(file.filename)
    file_path = os.path.join("uploads", filename)
    file.save(file_path)

    # ✅ Load TF-IDF Vectorizer (Ensure test features match training)
    tfidf_path = "mlmodels/tfidf_vectorizer.pkl"
    if not os.path.exists(tfidf_path):
        return jsonify({"error": "TF-IDF vectorizer not found. Please retrain the model."}), 500

    tfidf = joblib.load(tfidf_path)  # Load trained TF-IDF

    # ✅ Load test dataset
    try:
        test_data = pd.read_excel(file_path, engine="openpyxl")
    except Exception:
        return jsonify({"error": "Invalid test file format. Please upload a valid .xlsx file"}), 400

    if "Description" not in test_data.columns:
        return jsonify({"error": "Invalid test file format. 'Description' column is required"}), 400

    # ✅ Transform test data using trained TF-IDF
    X_test = tfidf.transform(test_data["Description"])

    # ✅ Predict clusters (Handle errors gracefully)
    try:
        predictions = model.predict(X_test.toarray())
    except Exception as e:
        return jsonify({"error": f"Model prediction failed: {str(e)}"}), 500

    test_data['Predicted_Cluster'] = predictions

    # ✅ Compute Evaluation Metrics
    from sklearn.metrics import silhouette_score, davies_bouldin_score, adjusted_rand_score
    from scipy.spatial.distance import cdist
    import numpy as np

    metrics = {}

    if hasattr(model, "inertia_"):  # For K-Means
        metrics["inertia"] = model.inertia_

    if len(set(predictions)) > 1:  # Ensure at least 2 clusters exist
        metrics["silhouette_score"] = silhouette_score(X_test, predictions)
        metrics["davies_bouldin"] = davies_bouldin_score(X_test.toarray(), predictions)

        # Compute Dunn Index
        cluster_distances = cdist(X_test.toarray(), X_test.toarray(), metric="euclidean")
        min_intercluster_dist = np.min(cluster_distances[np.triu_indices_from(cluster_distances, 1)])
        max_intracluster_dist = max(
            [np.max(cluster_distances[predictions == i][:, predictions == i]) for i in set(predictions)]
        )
        metrics["dunn_index"] = min_intercluster_dist / max_intracluster_dist if max_intracluster_dist > 0 else 0

    if "Cluster" in test_data.columns:
        metrics["ari"] = adjusted_rand_score(test_data["Cluster"], predictions)

    return jsonify({
        "message": "Test completed!",
        "predictions": predictions.tolist(),
        "metrics": metrics
    }), 200


from models.ml_model import MLModel
from models import db

@models_blueprint.route("/available", methods=["GET"])
@jwt_required()
def get_available_models():
    """Fetches available models from the mlmodels folder."""
    try:
        models = [f.split('_model.pkl')[0] for f in os.listdir(MODEL_FOLDER) if f.endswith("_model.pkl")]
        return jsonify({"models": models}), 200
    except Exception as e:
        return jsonify({"error": f"Error fetching models: {str(e)}"}), 500

from sqlalchemy.exc import SQLAlchemyError  # Import for handling DB errors

@models_blueprint.route("/save-selection", methods=["POST"])
@jwt_required()
def save_model_selection():
    """Saves the selected model in the database (only one entry)."""
    claims = get_jwt()
    user_type = claims.get("user_type")


    data = request.get_json()
    selected_model = data.get("model_name")

    if not selected_model:
        return jsonify({"error": "Model name is required."}), 400

    try:
        # ✅ Start a new transaction
        with db.session.begin_nested():
            db.session.query(MLModel).delete()
            db.session.add(MLModel(model_name=selected_model))
        
        db.session.commit()  # ✅ Commit after inserting new model

        return jsonify({"message": f"Model '{selected_model}' is now selected."}), 200

    except SQLAlchemyError as e:
        db.session.rollback()  # ✅ Rollback in case of failure
        return jsonify({"error": f"Failed to save model selection: {str(e)}"}), 500

@models_blueprint.route("/selected", methods=["GET"])
@jwt_required()
def get_selected_model():
    """Fetches the currently selected ML model."""
    selected_model = MLModel.query.first()
    
    if selected_model:
        return jsonify({"model_name": selected_model.model_name}), 200
    else:
        return jsonify({"message": "No model selected"}), 200