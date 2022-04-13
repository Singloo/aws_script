import os


RESERVED_INSTANCE_ID = os.getenv('RESERVED_INSTANCE_ID')

REGION_NAME = os.getenv('REGION_NAME')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

SS_STR = os.getenv('SS_STR')
SS_PORT = os.getenv('SS_PORT')

MONGO_USERNAME = os.getenv('MONGO_USERNAME')
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD')
MONGO_HOST = os.getenv('MONGO_HOST')
MONGO_PORT = os.getenv('MONGO_PORT')
MONGO_DBNAME = os.getenv('MONGO_DBNAME')