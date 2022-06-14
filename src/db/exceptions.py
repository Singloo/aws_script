class ExceedMaximumNumber(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__('Exceed maximum number', *args)


class NoSuchDocument(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)
