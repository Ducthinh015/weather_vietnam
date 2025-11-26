from backend.db import get_db

print("=== RAW CHECK WEATHER COLLECTION ===")

db = get_db()

print("Total weather docs:", db.weather.count_documents({}))

# Thử lấy 5 docs đầu tiên
for doc in db.weather.find({}, {"province": 1, "timestamp": 1}).limit(5):
    print(doc)
