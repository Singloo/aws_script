from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from pytz import utc, timezone
from src.messageHandlers.ec2Handler import stop_ec2
from src.logger import logger
import asyncio
from src.utils.constants import MONGO_DBNAME
from src.db.mongo import Mongo

CHINA_TIME = timezone('China/Shanghai')

jobstores = {
    'redis':  MongoDBJobStore(
        client=Mongo()._mongoClient, database=MONGO_DBNAME, collection='schedules')
}
sched = BackgroundScheduler(jobstores=jobstores, timezone=CHINA_TIME)


def schedule_to_shut_down_ec2(instance_id):
    # loop = asyncio.new_event_loop()
    # task = loop.create_task(stop_ec2(instance_id))
    success, resp = asyncio.run(stop_ec2(instance_id))
    logger.info(f'[SCHEDULE] [Stop ec2] {success},{resp}')
    # loop.close()
