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

    def same_cmd_is_running(self, cmd: str, started_at: datetime):
        return self._append_new_msg(f'A same command: {cmd} has started at: {started_at}, please check it out later')

    def invalid_status_for_cmd(self, cmd: str, expected_status: str, current_status: str):
        return self._append_new_msg(f'Command: {cmd} expect instance status: {expected_status} but got: {current_status}')

    def cmd_error(self, cmd: str, error):
        return self._append_new_msg(f'Sorry, an error encountered when executing command: {cmd}, error: {error}')

    def cmd_success(self, cmd: str, current_status: str):
        return self._append_new_msg(f'Command: {cmd} executed successfully, current instance state: {current_status}')

    def no_such_document(self, collection_name: str, *conditions: list[str]):
        return self._append_new_msg(f'No such document in: {collection_name}, queryed with: {conditions}')
