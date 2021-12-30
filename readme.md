this is a simple server linked with wechat official account to control aws ec2 instance.  
just for personal use

### requirements
1. wechat official account
2. aws ec2 instance
3. with outline service running on your instance

accept 3 cammands  
`ec2 <ec2-instance-id> [start|stop|state]`  
after pass instance id, server will cache it for 10 minutes, you can use cammand in short to control it.  
like `start` `stop` `status`

also you need to provide env variables.

<img
src=./docs/1.png
width=200
/>