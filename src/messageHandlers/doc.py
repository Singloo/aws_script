from . import AsyncBaseMessageHandler


class AwsBindHelper(AsyncBaseMessageHandler):
    async def __call__(self, inputs: list[str]):
        return '''Bind Aws crediential, you will be asked to input these fields:
aws access key id: e.g. AKIAUY54QBW6WAPIOGBE
aws secret access key: e.g. 8Qu6yPw52QsVjDeIvxYvnFeiYwBBK7yqpYeHuPU2
aws region: e.g.: us-east-1
after binding, you will get an ID and alias to identify your crediential.
        '''


class AwsListHelper(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return '''List all your bound aws crediential.
        '''


class AwsRmHelper(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return '''
Remove a bound aws crediential.
*All ec2 instances related with this crediential and all cron jobs related to those ec2 instances will also be removed.

use it like:
aws rm <id | alias>
        '''


class AwsDefaultHelper(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return '''
Set a default aws crediential.
use it like:
aws default <id | alias>
        '''


class AwsHelper(AsyncBaseMessageHandler):
    async def _fallback(self, cmds: list[str]):
        return '''
available commands:

aws bind
aws list
aws rm <id | alias>
aws default <alias>

check out the help for more information.
        '''
    @property
    def bind(self):
        return AwsBindHelper(self.params)

    @property
    def list(self):
        return AwsListHelper(self.params)

    @property
    def rm(self):
        return AwsRmHelper(self.params)

    @property
    def default(self):
        return AwsDefaultHelper(self.params)


class Ec2BindHelper(AsyncBaseMessageHandler):
    async def __call__(self, inputs: list[str]):
        return '''Bind Ec2 instance, require aws crediential id|alias provided, you will be asked to input these fields:
instacne id: e.g. i-01258a15b15fec037
outline token(optional): e.g. ss://Y2hhY2hhMjWV0Zi1wb2x5MTMwNTpvdk9VVlZXbXdLQzI=@8.8.8.8:12345
after binding, you will get an ID and alias to identify your crediential.

use it like:
ec2 bind <aws crediential id | alias>
        '''


class Ec2ListHelper(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return '''List all your bound ec2 instances.
        '''


class Ec2RmHelper(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return '''
Remove a bound ec2 instance.
*All cron jobs related to this instance will be removed also.

use it like:
ec2 rm <id | alias>
        '''


class Ec2StartHelper(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return '''
Start an ec2 instance. Expect instance status to be stopped.

use it like:
ec2 start [id | alias]
if id|alias is not provided, the default instance will be started.
        '''


class Ec2StatusHelper(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return '''
Get the status and ip of an ec2 instance.

use it like:
ec2 status [id | alias]
if id|alias is not provided, the default instance will be used.
        '''


class Ec2StopHelper(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return '''
Stop an ec2 instance. Expect instance status to be running.

use it like:
ec2 stop [id | alias]
if id|alias is not provided, the default instance will be stopped.
        '''


class Ec2AliasHelper(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return '''
Set a new alias for an ec2 instance.

use it like:
ec2 alias <id | old_alias> <new_alias>
        '''


class Ec2DefaultHelper(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return '''
Set an ec2 instance to be the default instance.
use it like:
ec2 default <id | alias>
        '''


class Ec2CronListHelper(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return '''
List all cron jobs
        '''


class Ec2CronRunHelper(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return '''
Run a cron job
use it like:
ec2 cron run <id | alias>
        '''


class Ec2CronStopHelper(AsyncBaseMessageHandler):
    async def __call__(self, cmds: list[str]):
        return '''
Stop a cron job
use it like:
ec2 cron stop <id | alias>
        '''


class Ec2CronHelper(AsyncBaseMessageHandler):
    async def _fallback(self, cmds: list[str]):
        return '''
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

Other commands:
ec2 cron list
ec2 cron run
ec2 cron stop
        '''
    @property
    def list(self):
        return Ec2CronListHelper(self.params)

    @property
    def run(self):
        return Ec2CronRunHelper(self.params)

    @property
    def stop(self):
        return Ec2CronStopHelper(self.params)


class Ec2Helper(AsyncBaseMessageHandler):
    async def _fallback(self, cmds: list[str]):
        return '''
available commands:

ec2 bind
ec2 list
ec2 rm <id | alias>
ec2 default <alias>
ec2 start [id | alias]
ec2 status [id | alias]
ec2 stop [id | alias]
ec2 alias <id | old_alias> <new_alias>
ec2 cron [ec2 id | alias] <time> <start|stop>
ec2 cron list
ec2 cron run <id | alias>
ec2 cron stop <id | alias>

start equals to ec2 start
stop equals to ec2 stop
status equals to ec2 status

check out the help for more information.
        '''
    @property
    def bind(self):
        return Ec2BindHelper(self.params)

    @property
    def list(self):
        return Ec2ListHelper(self.params)

    @property
    def rm(self):
        return Ec2RmHelper(self.params)

    @property
    def start(self):
        return Ec2StartHelper(self.params)

    @property
    def status(self):
        return Ec2StatusHelper(self.params)

    @property
    def state(self):
        return Ec2StatusHelper(self.params)

    @property
    def stop(self):
        return Ec2StopHelper(self.params)

    @property
    def alias(self):
        return Ec2AliasHelper(self.params)

    @property
    def cron(self):
        return Ec2CronHelper(self.params)

    @property
    def default(self):
        return Ec2DefaultHelper(self.params)


class Help(AsyncBaseMessageHandler):
    @property
    def aws(self):
        return AwsHelper(self.params)

    @property
    def ec2(self):
        return Ec2Helper(self.params)

    async def _fallback(self, cmds: list[str]):
        return '''
What can I do for you?
try to input

help aws
help ec2

to get more detail
        '''
