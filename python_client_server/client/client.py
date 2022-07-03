""" Программа клиента для получения и отправки сообщений """
print("загружаем модули...")
import sys, logging, argparse
from PyQt5.QtWidgets import QApplication
from client_db import ClientDB
from client_socket import ClientSocket
from win_main import ClientMainWindow

sys.path.append('../')
import common.settings as cmnset
import common.errors as my_err


# Инициализация клиентского логера
logger = logging.getLogger('client')


# Парсер аргументов коммандной строки
def arg_parser():
    """
    Парсер аргументов командной строки, возвращает кортеж из 4 элементов
    адрес сервера, порт, имя пользователя, пароль.
    Выполняет проверку на корректность номера порта.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=cmnset.DEFAULT_ADDRESS, nargs='?')
    parser.add_argument('port', default=cmnset.DEFAULT_PORT, type=int, nargs='?')
    parser.add_argument('-n', '--name', default=None, nargs='?')
    parser.add_argument('-p', '--password', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_name = namespace.name
    client_passwd = namespace.password

    # проверим подходящий номер порта
    if not 1023 < server_port < 65536:
        logger.critical(
            f'Попытка запуска клиента с неподходящим номером порта: {server_port}. '
            f'Допустимы адреса с 1024 до 65535. Клиент завершается.')
        exit(1)

    if not client_passwd or not client_name:
        logger.error(f'Попытка запуска клиента без пароля.')
        print("Имя пользователя и пароль обязательны при запуске клиента")
        exit(1)

    return server_address, server_port, client_name, client_passwd


def main():
    # Загружаем параметы коммандной строки
    server_address, server_port, user_name, client_passwd = arg_parser()
    logger.debug('Загружены параметры командной строки')
    
    # Приветственное сообщение
    print(f'Консольный месседжер. Клиентский модуль. Имя пользователя: {user_name}')

    # Создаём клиентокое приложение
    client_app = QApplication(sys.argv)

    # Записываем логи
    logger.info(
        f'Запущен клиент с парамертами: адрес сервера: {server_address} , '
        f'порт: {server_port}, имя пользователя: {user_name}')

    # Создаём объект базы данных
    database = ClientDB(user_name)

    # Создаём объект - транспорт и запускаем транспортный поток
    try:
        transport = ClientSocket(server_port, server_address, database, user_name)
    except my_err.ServerError as error:
        print(error.text)
        exit(1)
    transport.setDaemon(True)
    transport.start()

    # Создаём GUI
    main_window = ClientMainWindow(database, transport)
    main_window.make_connection(transport)
    main_window.setWindowTitle(f'Чат Программа alpha release - {user_name}')
    client_app.exec_()

    # Раз графическая оболочка закрылась, закрываем транспорт
    transport.socket_shutdown()
    transport.join()


if __name__ == '__main__':
    main()
