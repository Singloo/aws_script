this is a simple server linked with wechat official account to control aws ec2 instance.  
provide some simple commands

### requirements
1. wechat official account
2. MongoDb
3. aws credientials

### Env variables
```
MONGO_USERNAME=
MONGO_PASSWORD=
MONGO_HOST=
MONGO_PORT=27017
MONGO_DBNAME=
CRYPTO_KEY=for encryption
SENTRY_DSN=
```

### Available commands

> aws bind

Bind Aws crediential, you will be asked to input these fields:
aws access key id: e.g. AKIAUY54QBW6WAPIOGBE
aws secret access key: e.g. 8Qu6yPw52QsVjDeIvxYvnFeiYwBBK7yqpYeHuPU2
aws region: e.g.: us-east-1
after binding, you will get an ID and alias to identify your crediential.

> aws list

List all your bound aws crediential.

> aws rm

Remove a bound aws crediential.
*All ec2 instances related with this crediential and all cron jobs related to those ec2 instances will also be removed.

use it like:
aws rm <id | alias>

> aws default

Set a default aws crediential.
use it like:
aws default <id | alias>

> ec2 list

List all your bound ec2 instances.

> ec2 rm

Remove a bound ec2 instance.
*All cron jobs related to this instance will be removed also.

use it like:
ec2 rm <id | alias>

> ec2 start | start

Start an ec2 instance. Expect instance status to be stopped.

use it like:
ec2 start [id | alias]
if id|alias is not provided, the default instance will be started.

> ec2 status | status

Get the status and ip of an ec2 instance.

use it like:
ec2 status [id | alias]
if id|alias is not provided, the default instance will be used.

> ec2 stop | stop

Stop an ec2 instance. Expect instance status to be running.

use it like:
ec2 stop [id | alias]
if id|alias is not provided, the default instance will be stopped.

> ec2 alias

Set a new alias for an ec2 instance.

use it like:
ec2 alias <id | old_alias> <new_alias>

> ec2 default 

Set an ec2 instance to be the default instance.
use it like:
ec2 default <id | alias>

> ec2 cron 

Add a cron job, start or stop ec2 instance at a certain time.
use it like:
ec2 cron <ec2 id | alias> <time> <start|stop>
ec2 cron <time> <start|stop>
if id|alias is not provided, the default instance will be used.

time should be in the format of:  
hour:minute
hour = [0-23]
minute = [0-59]

e.g.:
ec2 cron 12:00 start
ec2 cron 22:22 stop
ec2 cron u1 12:00 start
ec2 cron 62c1298e9b234e046a08503b 11:11 stop

> ec2 cron list

List all cron jobs

> ec2 cron run 

Run a cron job
use it like:
ec2 cron run <id | alias>

> ec2 cron stop 

Stop a cron job
use it like:
ec2 cron stop <id | alias>
