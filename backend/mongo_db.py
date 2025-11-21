from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=10000, appname="AgriCastAI")
db = client["agricast_ai"]
