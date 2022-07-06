"""Декораторы."""
import sys
import socket
import logging
import inspect
sys.path.append('../')


def log(func):
    """Декоратор логирования."""
    def wrapper(*args, **kwargs):
        logger_name = 'server' if 'server.py' in sys.argv[0] \
                      else 'client'
        LOGGER = logging.getLogger(logger_name)

        result = func(*args, **kwargs)

        LOGGER.debug(
            f'Вызвана функция "{func.__name__}" с параметрами \
            args = {args}, kwargs = {kwargs}, ' +
            f'из модуля "{func.__module__}", \
            из функции "{inspect.stack()[1][3]}"')

        return result
    return wrapper


def login_required(func):
    """
    Декоратор, проверяющий, что клиент авторизован на сервере.
    Проверяет, что передаваемый объект сокета находится в
    списке авторизованных клиентов.
    За исключением передачи словаря-запроса
    на авторизацию. Если клиент не авторизован,
    генерирует исключение TypeError
    """

    def checker(*args, **kwargs):
        # проверяем, что первый аргумент - экземпляр MessageProcessor
        # Импортить необходимо тут, иначе ошибка рекурсивного импорта.
        # ------------------------------------------------------------

        from server.core import MyServer

        # if isinstance(args[0], MyServer):
        if True:
            found = False
            print('!!!!!!!!!!! decors login_required')
            for arg in args:
                print('arg =', arg)
                if isinstance(arg, socket.socket):
                    # Проверяем, что данный сокет есть в
                    # списке names класса MyServer
                    for client in args[0].messages:
                        if args[0].messages[client]['socket'] == arg:
                            found = True
                            print('!!!!!!!!!!!!!!! true socket')

            # Теперь надо проверить, что передаваемые аргументы
            # не presence сообщение. Если presence, то разрешаем
            for arg in args:
                if isinstance(arg, dict):
                    if 'action' in arg and arg['action'] == 'presence':
                        found = True
                        print('!!!!!!!!!!!!!!! true presence')
            # Если не не авторизован и не сообщение начала
            # авторизации, то вызываем исключение.
            if not found:
                raise TypeError
        return func(*args, **kwargs)

    return checker
