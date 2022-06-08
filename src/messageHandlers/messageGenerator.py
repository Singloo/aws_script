from datetime import datetime
from src.types.type import Ec2Status
import re


class MessageGenerator():
    messages: list[str]

    def __init__(self, msg: str | list[str]) -> None:
        self.messages = []
        if isinstance(msg, str):
            self.messages.append(msg)
        if isinstance(msg, list):
            self.messages.extend(msg)

    def _append_new_msg(self, msg: str):
        self.messages.append(msg)
        return self

    @property
    def separator(self):
        self.messages.append('--------------------')
        return self

    def add_ip(self, ip: str):
        return self._append_new_msg(ip)

    def add_outline_token(self, token: str, ip: str):
        new_token = re.sub(r'(\d{1,3}\.){3}\d{1,3}', ip, token)
        return self._append_new_msg(new_token)

    def last_cmd_still_running(self, last_cmd: str, started_at: datetime, last_status: str):
        msg = f'Command [{last_cmd}] started at [{started_at}] and still running. Last status {last_status}'
        return self._append_new_msg(msg)

    def generate(self):
        return '\n'.join(self.messages)

    def invalid_cmd(self, cmd: str, expected_input: str):
        msg = f'{cmd}: invalid input, expect {expected_input}'
        return self._append_new_msg(msg)
