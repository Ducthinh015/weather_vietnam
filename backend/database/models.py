from datetime import datetime
from zoneinfo import ZoneInfo
from ..db import db

class ForecastHistory(db.Model):
    __tablename__ = 'forecast_history'

    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")), nullable=False)
    temperature = db.Column(db.Float, nullable=True)
    prediction = db.Column(db.Float, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'city': self.city,
            'timestamp': self.timestamp.isoformat(),
            'temperature': self.temperature,
            'prediction': self.prediction,
        }

