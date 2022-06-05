import sys
import logging
import inspect


def log(func):
    def wrapper(*args, **kwargs):
        logger_name = 'server' if 'server.py' in sys.argv[0] else 'client'
        LOGGER = logging.getLogger(logger_name)

        result = func(*args, **kwargs)

        LOGGER.debug(f'Вызвана функция "{func.__name__}" с параметрами args = {args}, kwargs = {kwargs}, ' + 
                    f'из модуля "{func.__module__}", из функции "{inspect.stack()[1][3]}"')

        return result
    return wrapper
