class InvalidCmd(Exception):
    message: str

    def __init__(self, message: str) -> None:
        self.message = message
