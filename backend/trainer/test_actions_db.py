from backend.db import get_db

db = get_db()

print("📌 GH ACTIONS – CHECK DB CONTENT")

print("Database name:", db.name)
print("Weather count:", db.weather.count_documents({}))
print("Models count:", db.models.count_documents({}))
print("Provinces:", len(db.weather.distinct("province")))
