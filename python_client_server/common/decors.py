import sys, socket
import logging
import inspect
sys.path.append('../')


def log(func):
    def wrapper(*args, **kwargs):
        logger_name = 'server' if 'server.py' in sys.argv[0] else 'client'
        LOGGER = logging.getLogger(logger_name)

        result = func(*args, **kwargs)

        LOGGER.debug(f'Вызвана функция "{func.__name__}" с параметрами args = {args}, kwargs = {kwargs}, ' + 
                    f'из модуля "{func.__module__}", из функции "{inspect.stack()[1][3]}"')

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
        # ----------------------------------------------------------------
        # args = (
        #         <MessageProcessor(Thread-5, started daemon 140650633856768)>,
        #         {'action': 'presence',
        #          'time': 1654900198.8001323,
        #           'user': {
        #                    'account_name': 'test1',
        #                    'pubkey': '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAmKN/CFSxgU8eu0oO0oKw\n29WTZQSfqw/mJgEtr8nLUAOHGcg3kT7epUgPfwbo/V67sJlGhb/UD7dPK81utWRn\nFKhhUGuo+ad/4HnvbSQjIHy2Wbr85T4gJCL1IqTkodAgSOo4Nuv/Qq9r5po0dNIC\nF4YTZrzfCy6V0v349iXM2CXf+/14fHCxsm3OkNCUwHsOW6nzh5fIyAs1UhssJm/Z\nbCNzX5PkRjI7bwBJhoXHNgS1fDyII6vGrQAyAwxU0hKrBAtAzYIon5ZlIYxyF2/5\nKb8IVmLmnrvCpmtjTQ4u80Dp6YuErMCD82GzgUi50UdQoW617AmFxaKpvO7Lu+aA\nfwIDAQAB\n-----END PUBLIC KEY-----'
        #                    'password': 'scscddvdvdfvdsvsvd' 
        #                   }
        #          },
        #          <socket.socket fd=25, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 7777), raddr=('127.0.0.1', 52416)>
        # )
        from server.core import MyServer

        # if isinstance(args[0], MyServer):
        if True:
            found = False
            print('!!!!!!!!!!! decors login_required')
            for arg in args:
                print('arg =', arg)
                if isinstance(arg, socket.socket):
                    # Проверяем, что данный сокет есть в списке names класса
                    # MessageProcessor
                    for client in args[0].messages:
                        # args[0].names = {'test1': <socket.socket fd=25, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 7777), raddr=('127.0.0.1', 52420)>}
                        if args[0].messages[client]['socket'] == arg:
                            found = True
                            print('!!!!!!!!!!!!!!! true socket')

            # Теперь надо проверить, что передаваемые аргументы не presence
            # сообщение. Если presence, то разрешаем
            for arg in args:
                if isinstance(arg, dict):
                    if 'action' in arg and arg['action'] == 'presence':
                        found = True
                        print('!!!!!!!!!!!!!!! true presence')
            # Если не не авторизован и не сообщение начала авторизации, 
            # то вызываем исключение.
            if not found:
                raise TypeError
        return func(*args, **kwargs)

    return checker
    