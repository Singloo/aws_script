from typing import TYPE_CHECKING
import aioboto3
from bson.objectid import ObjectId
from src.db.ec2Instance import Ec2InstanceRepo
from src.utils.constants import REGION_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, SS_PORT, SS_STR
from src.db.exceptions import ExceedMaximumNumber, NoSuchDocument
from src.db.awsCrediential import AwsCredientialRepo
from .messageGenerator import MessageGenerator

if TYPE_CHECKING:
    from mypy_boto3_ec2.client import EC2Client
    from mypy_boto3_ec2.service_resource import EC2ServiceResource, Instance
    from mypy_boto3_ec2.type_defs import StartInstancesResultTypeDef
else:
    EC2Client = object
    EC2ServiceResource = object
    Instance = object
    StartInstancesResultTypeDef = object


class Ec2InstanceManager():
    ec2: EC2ServiceResource

    def __init__(self, instance_id: str, region_name: str, aws_access_key_id: str, aws_secret_access_key: str) -> None:
        self.instance_id = instance_id
        self.region_name = region_name
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key

    async def __aenter__(self, ):
        session = aioboto3.Session()
        self.ec2 = await session.resource('ec2',
                                          region_name=self.region_name,
                                          aws_access_key_id=self.aws_access_key_id,
                                          aws_secret_access_key=self.aws_secret_access_key).__aenter__()
        filtered = self.ec2.instances.filter(
            InstanceIds=[self.instance_id]
        )
        ins: Instance
        async for item in filtered.limit(1):
            ins = item
        return ins

    async def __aexit__(self, type, value, trace):
        await self.ec2.__aexit__(type, value, trace)


def getEc2Instance(instance_id: str):
    return Ec2InstanceManager(
        instance_id,
        REGION_NAME,
        AWS_ACCESS_KEY_ID,
        AWS_SECRET_ACCESS_KEY
    )


def getEc2InstanceWithCredentialId(ec2_id: ObjectId, aws_crediential_id: ObjectId):
    crediential = AwsCredientialRepo().find_by_id(aws_crediential_id)
    ec2_instance = Ec2InstanceRepo().find_by_id(ec2_id)
    if crediential is None:
        raise NoSuchDocument(
            MessageGenerator().no_such_document('AwsCrediential', aws_crediential_id)
        )
    return Ec2InstanceManager(
        ec2_instance['instance_id'],
        crediential['region_name'],
        crediential['aws_access_key_id'],
        crediential['aws_secret_access_key']
    )
