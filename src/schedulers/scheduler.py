from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from pytz import utc, timezone
from src.logger import logger
from src.utils.constants import MONGO_DBNAME
from src.db.mongo import Mongo

CHINA_TIME = timezone('China/Shanghai')

jobstores = {
    'mongo':  MongoDBJobStore(
        client=Mongo()._mongoClient, database=MONGO_DBNAME, collection='schedules')
}
sched = BackgroundScheduler(jobstores=jobstores, timezone=CHINA_TIME)

