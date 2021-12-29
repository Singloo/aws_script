import json
import boto3
import os
from botocore.exceptions import ClientError

region_name = os.getenv('region_name')
aws_access_key_id = os.getenv('aws_access_key_id')
aws_secret_access_key = os.getenv('aws_secret_access_key')

ec2 = boto3.resource('ec2',
    region_name=region_name,
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)

def lambda_handler(event, context):
    try:
        print('event',event)
        instance_id = json.loads(event['body']).get('instance_id',None)
        if instance_id is None:
            raise Exception('Invalid Input')
        
        filtered = ec2.instances.filter(
                InstanceIds=[instance_id]
            )
        ins = list(filtered.all())[0]
        print(ins.state['Name'])
        if ins.state['Name'] != 'running':
            return {
                'statusCode': 200,
                'body': json.dumps(
                {
                    'message': f"Instance current state is {ins.state['Name']}"
                }
                )
            }
        response = ins.stop()
        print(response)
        return {
            'statusCode': 200,
            'body': json.dumps(
                {
                    'message':response['StoppingInstances'][0]['CurrentState']['Name']
                }
                )
        }
    except ClientError as e:
        print(e)
        return {
            'statusCode': 500,
            'body': json.dumps(
                    {'message':str(e)}
                )
        }

