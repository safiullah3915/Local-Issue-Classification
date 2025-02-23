import pandas as pd
import joblib
import os
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import TfidfVectorizer

MODEL_FOLDER = "mlmodels"

def train_new_models(file_path):

    if not os.path.exists(MODEL_FOLDER):
        os.makedirs(MODEL_FOLDER)

    df = pd.read_excel(file_path)

    tfidf = TfidfVectorizer(max_features=1000)
    X = tfidf.fit_transform(df["Description"])

    scaler = StandardScaler(with_mean=False)
    X_scaled = scaler.fit_transform(X)

    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_scaled.toarray())

    df["PCA1"] = X_pca[:, 0]
    df["PCA2"] = X_pca[:, 1]

    kmeans = KMeans(n_clusters=5, random_state=42).fit(X_scaled)
    dbscan = DBSCAN(eps=0.5, min_samples=5).fit(X_scaled)
    hierarchical = AgglomerativeClustering(n_clusters=5).fit(X_scaled.toarray())

    joblib.dump(kmeans, os.path.join(MODEL_FOLDER, "kmeans_model.pkl"))
    joblib.dump(dbscan, os.path.join(MODEL_FOLDER, "dbscan_model.pkl"))
    joblib.dump(hierarchical, os.path.join(MODEL_FOLDER, "hierarchical_model.pkl"))

    return "Models trained successfully!"

if __name__ == "__main__":
    print("This script is for training models. Run it explicitly to train models.")
