from pymongo import MongoClient
import os

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://2331540234_db_user:0905175313@cluster0.qyfcbff.mongodb.net/agricast?retryWrites=true&w=majority"
)

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=10000, appname="AgriCastAI")

db = client["agricast"]
