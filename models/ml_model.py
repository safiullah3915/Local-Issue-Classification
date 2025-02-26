from models import db

class MLModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(50), nullable=False, unique=True) 

    def __init__(self, model_name):
        self.model_name = model_name
