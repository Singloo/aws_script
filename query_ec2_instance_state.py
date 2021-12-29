import json
import boto3
import os
from botocore.exceptions import ClientError
import time

region_name = os.getenv('region_name')
aws_access_key_id = os.getenv('aws_access_key_id')
aws_secret_access_key = os.getenv('aws_secret_access_key')

ss_str = os.getenv('ss_str')
ss_port = os.getenv('ss_port')

ec2 = boto3.resource('ec2',
    region_name=region_name,
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)

def compose_ss_token(ip):
    return {
        'new_ss_token': f"{ss_str}{ip}:{ss_port}",
        'ip':ip
    }

def wait_for_ip(ins):
    ins.load()
    ip = ins.public_ip_address
    state = ins.state['Name']
    while ip is None:
        time.sleep(0.2)
        ins.load()
        ip = ins.public_ip_address
        state = ins.state['Name']
    return compose_ss_token(ip)
    
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
        addon =  wait_for_ip(ins) if ins.state['Name'] != 'stopped' else {}
        return {
            'statusCode': 200,
            'body': json.dumps(
            {
                'message': f"{ins.state['Name']}",
                **addon
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
