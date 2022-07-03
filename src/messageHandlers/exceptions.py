class InvalidCmd(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class NoSuchHandler(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
