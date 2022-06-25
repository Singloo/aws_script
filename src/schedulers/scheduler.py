from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from pytz import utc, timezone
from src.messageHandlers.ec2Handler import stop_ec2
from src.logger import logger
import asyncio
from src.utils.constants import MONGO_DBNAME
from src.db.mongo import Mongo
from src.db.ec2OperationLog import Ec2OperationLogRepo
from src.db.ec2Status import Ec2StatusRepo

CHINA_TIME = timezone('China/Shanghai')

jobstores = {
    'mongo':  MongoDBJobStore(
        client=Mongo()._mongoClient, database=MONGO_DBNAME, collection='schedules')
}
sched = BackgroundScheduler(jobstores=jobstores, timezone=CHINA_TIME)

