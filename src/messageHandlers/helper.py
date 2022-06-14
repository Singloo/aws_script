import aioboto3
from botocore.exceptions import ClientError
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from mypy_boto3_ec2.client import EC2Client
    from mypy_boto3_ec2.service_resource import EC2ServiceResource, Instance
else:
    EC2Client = object
    EC2ServiceResource = object
    Instance = object


async def test_aws_resource(region_name: str, aws_access_key_id: str, aws_secret_access_key: str, instance_id: str | None = None):
    try:
        session = aioboto3.Session()
        async with session.resource('ec2',
                                    region_name=region_name,
                                    aws_access_key_id=aws_access_key_id,
                                    aws_secret_access_key=aws_secret_access_key) as ec2:
            ec2: EC2ServiceResource
            if instance_id is None:
                all_instance = ec2.instances.all()
                async for item in all_instance.limit(1):
                    pass
                return True
            else:
                instances = ec2.instances.filter(
                    InstanceIds=[instance_id]
                )
                found: EC2Client | None = None
                async for item in instances.limit(1):
                    found = item
                return found is not None
    except ClientError as e:
        return e.response['Error']['Message']
