from logging import config, getLogger
from config import settings

config.dictConfig(settings.LOGGING_DIC)


def get_log(name):
    return getLogger(name)
