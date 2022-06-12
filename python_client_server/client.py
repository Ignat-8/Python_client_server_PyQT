""" Программа клиента для отправки приветствия сервера 
и получения ответа """
print("загружаем модули...")

import sys
import json
import time
# from socket import socket, AF_INET, SOCK_STREAM
import socket
import logging
from threading import Thread
from unittest import expectedFailure
import logs.conf_client_log
import common.settings as cmnset
from common.utils import get_message, send_message
from common.decors import log
import common.errors as my_err
from metaclasses import ClientMaker


# Инициализация клиентского логера
CLIENT_LOGGER = logging.getLogger('client')


# Класс формирования и отправки сообщений на сервер 
# и взаимодействия с пользователем.
class ClientSender(Thread, metaclass=ClientMaker):
    def __init__(self, CLIENT_SOCK, user_name='Guest'):
        self.user_name = user_name
        self.CLIENT_SOCK = CLIENT_SOCK
        super().__init__()

    @staticmethod
    def create_message(user_name, action='presence', text='', destination=''):
        """Функция создаёт словарь с сообщением.
        По умолчанию это регистрационное сообщение presence"""
        message = {
            'action': action,
            'time': time.time(),
            'user': {
                'account_name': user_name,
                },
        }
        if text and destination:
            message['text'] = text
            message['destination'] = destination

        CLIENT_LOGGER.debug('Сформировано сообщение %s', message)
        return message

    @staticmethod
    def print_help():
        """Функция выводящяя справку по использованию"""
        print('Поддерживаемые команды:')
        print('message - отправить сообщение. Кому и текст будет запрошены отдельно.')
        print('help - вывести подсказки по командам')
        print('exit - выход из программы')
    
    # user_interactive
    def run(self):
        """Функция взаимодействия с пользователем, запрашивает команды, отправляет сообщения"""
        self.print_help
        while True:
            command = input('Введите команду: ')
            if command == 'message':
                to_user = input('Введите получателя сообщения: ')
                if to_user == self.user_name:
                    print('Нельзя отправить сообщение самому себе')
                    continue
                message_text = input('Введите сообщение для отправки: ')

                message_send = self.create_message(self.user_name,
                                                    action='message', 
                                                    text=message_text, 
                                                    destination=to_user)
                CLIENT_LOGGER.debug(f'Сформирован словарь сообщения: {message_send}')
                try:
                    send_message(self.CLIENT_SOCK, message_send)
                    CLIENT_LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
                    print(f'Отправлено сообщение для пользователя {to_user}')
                    # ждем ответ от сервера
                    time.sleep(1)
                except Exception as e:
                    print('Потеряно соединение с сервером:\n', e)
                    CLIENT_LOGGER.critical('Потеряно соединение с сервером.')
                    sys.exit(1)
            elif command == 'help':
                self.print_help()
            elif command == 'exit':
                message_exit = self.create_message(self.user_name, action='exit')
                send_message(self.CLIENT_SOCK, message_exit)
                print('Завершение соединения.')
                CLIENT_LOGGER.info('Завершение работы по команде пользователя.')
                # Задержка неоходима, чтобы успело уйти сообщение о выходе
                time.sleep(0.5)
                break
            else:
                print('Команда не распознана, попробойте снова. \
                    help - вывести поддерживаемые команды.')


# Класс-приёмник сообщений с сервера. 
# Принимает сообщения, выводит в консоль.
class ClientReader(Thread, metaclass=ClientMaker):
    def __init__(self, CLIENT_SOCK, user_name='Guest'):
        self.user_name = user_name
        self.CLIENT_SOCK = CLIENT_SOCK
        super().__init__()

    @staticmethod
    def process_ans(message):
        CLIENT_LOGGER.debug(f'Разбор сообщения от сервера: {message}')
        if 'response' in message:
            if message['response'] == 200:
                CLIENT_LOGGER.debug(f"'200': 'ok'")
                if 'text' in message and message['text']:
                    return {'200': 'ok', 'message': message['text']}
                else:
                    return {'200': 'ok'}

            if message['response'] == 300:
                CLIENT_LOGGER.debug(f"300: {message['error']}")
                raise my_err.AccountNameNotUniq

            if message['response'] == 400:
                CLIENT_LOGGER.debug(f"400: {message['error']}")
                raise my_err.ServerError(f"400: {message['error']}")
        raise my_err.ReqFieldMissingError('response')

    # message_from_server
    def run(self):
        """Функция - обработчик сообщений других пользователей, 
        поступающих с сервера"""
        while True:
            try:
                message = get_message(self.CLIENT_SOCK)
                if 'action' in message and message['action'] == 'message' \
                        and 'destination' in message and 'text' in message \
                        and message['destination'] == self.user_name:
                    
                    print(f"\nПолучено сообщение от пользователя {message['user']['account_name']}:"
                        f"\n{message['text']}")
                    CLIENT_LOGGER.info(f"Получено сообщение от пользователя {message['user']['account_name']}:"
                                        f"\n{message['text']}")

                # 'Получатель с таким имененм не активен'
                if 'response' in message and message['response'] == 301:
                    print(message['error'])

            except (my_err.NonDictError, my_err.NonStrError, my_err.NonBytesError):
                CLIENT_LOGGER.error(f'Не удалось декодировать полученное сообщение.')
            except (OSError, ConnectionError, ConnectionAbortedError,
                    ConnectionResetError, json.JSONDecodeError):
                CLIENT_LOGGER.critical(f'Потеряно соединение с сервером.')
                break


@log
def register_on_server(user_name, CLIENT_SOCK, server_address, server_port):
    # Запрашиваем имя пользователя
    while True:
        if not user_name:
            user_name = input('Введите имя пользователя: ')
        else:
            break

    try:  # пытаемся зарегистрироваться на сервере
        message_to_server = ClientSender.create_message(
                                        user_name=user_name, 
                                        action='presence', 
                                        text='', 
                                        destination='')
        send_message(CLIENT_SOCK, message_to_server)
        server_answer = ClientReader.process_ans(get_message(CLIENT_SOCK))

    except json.JSONDecodeError:
        CLIENT_LOGGER.error('Не удалось декодировать полученную Json строку.')
        print('Не удалось декодировать полученную Json строку.')
        sys.exit(1)
    except my_err.ServerError as error:
        CLIENT_LOGGER.error(f'При установки соединения сервер вернул ошибку: {error.text}')
        print(f'При установки соединения сервер вернул ошибку: {error.text}')
        sys.exit(1)
    except my_err.ReqFieldMissingError as missing_error:
        CLIENT_LOGGER.error(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
        print(f'В ответе сервера отсутствует необходимое поле {missing_error.missing_field}')
        sys.exit(1)
    except (ConnectionRefusedError, ConnectionError):
        CLIENT_LOGGER.critical(
            f'Не удалось подключиться к серверу {server_address}:{server_port}, '
            f'конечный компьютер отверг запрос на подключение.')
        print(f'Не удалось подключиться к серверу {server_address}:{server_port}, '
                f'конечный компьютер отверг запрос на подключение.')
        sys.exit(1)
    except my_err.AccountNameNotUniq:
        print('Данное имя уже используется')
        user_name = '' 
        user_name, server_answer = register_on_server(user_name, CLIENT_SOCK)

    return user_name, server_answer


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
