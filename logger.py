import logging





def get_logger():
    logger = logging.getLogger()
    handler1 = logging.StreamHandler()

    logger.setLevel(logging.INFO)
    handler1.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[%(process)s] [%(filename)s %(lineno)s] %(asctime)s %(levelname)s: %(message)s")
    handler1.setFormatter(formatter)

    logger.addHandler(handler1)
    return logger


logger = get_logger()
