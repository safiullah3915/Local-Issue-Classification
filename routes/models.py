import os
import joblib
import pandas as pd
from flask import Blueprint, request, jsonify, Response, stream_with_context
import time  # 🔹 Import time for delay
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

models_blueprint = Blueprint("models", __name__)

MODEL_FOLDER = "mlmodels"

if not os.path.exists(MODEL_FOLDER):
    os.makedirs(MODEL_FOLDER)


def load_model(model_name):
    """ Load a pre-trained model from disk """
    model_path = os.path.join(MODEL_FOLDER, model_name)
    if os.path.exists(model_path):
        return joblib.load(model_path)
    return None


@models_blueprint.route("/train", methods=["POST"])
@jwt_required()
def train_model():
    """ Simulates model training with a delay using a streaming response """

    user_id = get_jwt_identity()

    if user_id != 1: 
        return jsonify({"error": "Unauthorized! Only super users can train models"}), 403

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join("uploads", filename)
    file.save(file_path)

    def train():
        yield "Processing...\n"
        time.sleep(10)
        yield "Done!\n"

    return Response(stream_with_context(train()), content_type="text/event-stream")

@models_blueprint.route("/test", methods=["POST"])
@jwt_required()
def test_model():
    """ Tests a model using uploaded data """
    file = request.files.get("file")
    model_name = request.form.get("model")

    if not file or not model_name:
        return jsonify({"error": "Missing required fields"}), 400

    model = load_model(f"{model_name}.pkl")
    if model is None:
        return jsonify({"error": f"Model {model_name} not found"}), 404

    filename = secure_filename(file.filename)
    file_path = os.path.join("uploads", filename)
    file.save(file_path)

    test_data = pd.read_csv(file_path)
    if "Description" not in test_data.columns:
        return jsonify({"error": "Invalid test file format. 'Description' column is required"}), 400

    from sklearn.feature_extraction.text import TfidfVectorizer
    tfidf = TfidfVectorizer(max_features=1000)
    X_test = tfidf.fit_transform(test_data["Description"])

    predictions = model.predict(X_test.toarray())

    return jsonify({"message": "Test completed!", "predictions": predictions.tolist()}), 200
