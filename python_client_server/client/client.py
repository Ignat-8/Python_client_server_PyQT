""" Программа клиента для получения и отправки сообщений """
print("загружаем модули...")
import sys
import json
import time
import logging
from threading import Thread
from unittest import expectedFailure
import logs.conf_client_log
import common.settings as cmnset
from common.utils import get_message, send_message
from common.decors import log
import common.errors as my_err
from metaclasses import ClientMaker
from client_db import ClientDB


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
        CLIENT_LOGGER.info('Использование параметров по умолчанию - DEFAULT_ADDRESS и DEFAULT_PORT')
    except ValueError:
        CLIENT_LOGGER.error('Номер порта должен быть в диапазоне от 1024 до 65535')
        sys.exit(1)

    try:
        user_name = ''
        if '-n' in sys.argv:
            user_name = sys.argv[sys.argv.index('-n') + 1]
        
        if '--name' in sys.argv:
            user_name = sys.argv[sys.argv.index('--name') + 1]
    except ValueError:
        CLIENT_LOGGER.error('Указано не верное значение аргумента')
        print("Указано не верное значение аргумента")
        sys.exit(1)
    
    # Приветственное сообщение
    print(f'Консольный месседжер. Клиентский модуль. Имя пользователя: {user_name}')

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as CLIENT_SOCK:
        CLIENT_SOCK.connect((server_address, server_port))
        # регистрируемся на сервере
        user_name, server_answer = register_on_server(user_name, CLIENT_SOCK, server_address, server_port)

        CLIENT_LOGGER.info(f'Установлено соединение с сервером для пользователя {user_name}.\n \
                                Ответ сервера: {server_answer}')
        print(f'Установлено соединение с сервером для пользователя {user_name}.\n \
                                Ответ сервера: {server_answer}')

        # Создаём объект базы данных
        database = ClientDB(user_name)

        # запускаем клиентский процесс приёма сообщений
        receiver = ClientReader(CLIENT_SOCK, user_name)
        receiver.daemon = True
        receiver.start()

        # затем запускаем отправку сообщений и взаимодействие с пользователем.
        user_interface = ClientSender(CLIENT_SOCK, user_name)
        user_interface.daemon = True
        user_interface.start()
        CLIENT_LOGGER.debug('Запущены процессы')

        # Watchdog основной цикл, если один из потоков завершён,
        # то значит или потеряно соединение или пользователь
        # ввёл exit. Поскольку все события обработываются в потоках,
        # достаточно просто завершить цикл.
        while True:
            time.sleep(1)
            if receiver.is_alive() and user_interface.is_alive():
                continue
            break


if __name__ == '__main__':
    main()
