from pymongo import MongoClient
from constants import MONGO_DBNAME, MONGO_HOST, MONGO_PASSWORD, MONGO_PORT, MONGO_USERNAME
mongoClient = MongoClient(
    host=MONGO_HOST,
    port=int(MONGO_PORT),
)
