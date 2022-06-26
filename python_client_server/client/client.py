""" Программа клиента для получения и отправки сообщений """
print("загружаем модули...")
import sys, logging
from PyQt5.QtWidgets import QApplication
from client_db import ClientDB
from client_socket import ClientSocket
from win_main import ClientMainWindow

sys.path.append('../')
import common.settings as cmnset
import common.errors as my_err


# Инициализация клиентского логера
logger = logging.getLogger('client')


def main():
    # парсим аргументы командной строки
    try:
        key_names = ('-m', '--mode', '-n', '--name')
        server_address = sys.argv[1]
        if server_address in key_names:
            raise IndexError

        server_port = int(sys.argv[2])
        if server_port in key_names:
            raise IndexError
        if server_port < 1024 or server_port > 65535:
            raise ValueError
    except IndexError:
        server_address = cmnset.DEFAULT_ADDRESS
        server_port = cmnset.DEFAULT_PORT
        logger.info('Использование параметров по умолчанию - DEFAULT_ADDRESS и DEFAULT_PORT')
    except ValueError:
        logger.error('Номер порта должен быть в диапазоне от 1024 до 65535')
        sys.exit(1)

    try:
        user_name = ''
        if '-n' in sys.argv:
            user_name = sys.argv[sys.argv.index('-n') + 1]
        
        if '--name' in sys.argv:
            user_name = sys.argv[sys.argv.index('--name') + 1]
    except ValueError:
        logger.error('Указано не верное значение аргумента')
        print("Указано не верное значение аргумента")
        sys.exit(1)
    
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
