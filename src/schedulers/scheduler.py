from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
from pytz import utc
from src.messageHandlers.ec2Handler import stop_ec2
from src.logger import logger
jobstores = {
    'redis': RedisJobStore(
        host='redis',
        port=6379,
        db=0
    )
}
sched = BackgroundScheduler(jobstores=jobstores, timezone=utc)


def schedule_to_shut_down_ec2(instance_id):
    success, resp = stop_ec2(instance_id)
    logger.info(f'[SCHEDULE] [Stop ec2] {success},{resp}')
