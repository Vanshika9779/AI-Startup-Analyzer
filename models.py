from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json


db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    sender = db.Column(db.String(10))
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class AnalysisReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    idea = db.Column(db.Text, nullable=False)
    title = db.Column(db.String(180), default="Startup Analysis")
    reply = db.Column(db.Text, nullable=False)
    metrics_json = db.Column(db.Text, nullable=False)
    structured_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def metrics(self):
        try:
            return json.loads(self.metrics_json or '{}')
        except Exception:
            return {}

    @property
    def structured(self):
        try:
            return json.loads(self.structured_json or '{}')
        except Exception:
            return {}

    def to_dict(self):
        return {
            "id": self.id,
            "idea": self.idea,
            "title": self.title,
            "reply": self.reply,
            "metrics": self.metrics,
            "structured": self.structured,
            "created_at": self.created_at.strftime("%d %b %Y, %I:%M %p")
        }
