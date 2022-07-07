from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from pytz import utc, timezone
from src.utils.constants import MONGO_DBNAME
from pymongo import MongoClient
from src.utils.constants import MONGO_DBNAME, MONGO_HOST, MONGO_PASSWORD, MONGO_PORT, MONGO_USERNAME

CHINA_TIME = timezone('Asia/Shanghai')

mongoClient = MongoClient(
    host=MONGO_HOST,
    port=int(MONGO_PORT),
    username=MONGO_USERNAME, password=MONGO_PASSWORD,
    connect=True,
)
jobstores = {
    'mongo':  MongoDBJobStore(
        client=mongoClient, database=MONGO_DBNAME, collection='schedules')
}
sched = BackgroundScheduler(
    jobstores=jobstores, timezone=CHINA_TIME)
