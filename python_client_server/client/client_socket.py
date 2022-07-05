import sys
import time
import logging
import json
import threading
import hashlib
import binascii
import hmac
from socket import socket, AF_INET, SOCK_STREAM
from PyQt5.QtCore import pyqtSignal, QObject

sys.path.append('../')
from common.utils import get_message, send_message
# from common.settings import DEFAULT_ADDRESS, DEFAULT_PORT
from common.errors import ServerError, AccountNameNotUniq


# Логер и объект блокировки для работы с сокетом.
logger = logging.getLogger('client')
socket_lock = threading.Lock()


# Класс - Транспорт, отвечает за взаимодействие с сервером
class ClientSocket(threading.Thread, QObject):
    # Сигналы:
    new_message = pyqtSignal(str)  # новое сообщение
    connection_lost = pyqtSignal()  # потеря соединения

    def __init__(self, port, ip_address, database, username, passwd, keys):
        # Вызываем конструктор предка
        threading.Thread.__init__(self)
        QObject.__init__(self)

        self.database = database  # Класс База данных - работа с базой
        self.username = username  # Имя пользователя
        self.socket = None  # Сокет для работы с сервером
        self.password = passwd  # пароль
        self.passwd_hash_string = ''  # хэш пароля
        self.keys = keys  # набор ключей для шифрования
        # Устанавливаем соединение:
        self.connection_init(port, ip_address)
        # Обновляем таблицы известных пользователей и контактов
        try:
            self.user_list_update()
            self.contacts_list_update()
        except OSError as err:
            if err.errno:
                logger.critical('Потеряно соединение с сервером.')
                raise ServerError('Потеряно соединение с сервером!')
            logger.error('Timeout соединения при обновлении списка \
                          пользователей.')
        except json.JSONDecodeError:
            logger.critical('Потеряно соединение с сервером.')
            raise ServerError('Потеряно соединение с сервером!')

        self.running = True  # Флаг продолжения работы транспорта.

    def connection_init(self, port, ip):
        """Инициализирует сокет и регистрирует на сервере."""

        print(50*'=' + ' client_socket.connection_init')
        print('Инициализируем сокет')
        self.socket = socket(AF_INET, SOCK_STREAM)
        # Таймаут необходим для освобождения сокета.
        self.socket.settimeout(5)
        # Соединяемся, 5 попыток соединения,
        # флаг успеха ставим в True если удалось
        connected = False
        for i in range(5):
            logger.info(f'Попытка подключения №{i + 1}')
            print(f'Попытка подключения №{i + 1}')
            try:
                self.socket.connect((ip, port))
            except (OSError, ConnectionRefusedError):
                pass
            else:
                connected = True
                break
            time.sleep(1)

        # Если соединится не удалось - исключение
        if not connected:
            logger.critical('Не удалось установить соединение с сервером')
            print('Не удалось установить соединение с сервером')
            raise ServerError('Не удалось установить соединение с сервером')

        logger.debug('Установлено соединение с сервером')
        print('Установлено соединение с сервером')

        # вычисляем хэш пароля
        passwd_bytes = self.password.encode('utf-8')
        salt = self.username.lower().encode('utf-8')
        passwd_hash = hashlib.pbkdf2_hmac('sha256',
                                          passwd_bytes,
                                          salt,
                                          100000)
        self.passwd_hash_string = binascii.hexlify(passwd_hash)
        # Вычисленное значение можно хранить в БД
        # print(passwd_hash_string)

        # Получаем публичный ключ и декодируем его из байтов
        pubkey = self.keys.publickey().export_key().decode('ascii')

        # регистрируемся на сервере
        with socket_lock:
            print("сокет освободился регистрируемся на сервере")
            req = self.create_message()
            req['user']['public_key'] = pubkey
            req['user']['password'] = self.passwd_hash_string.decode('ascii')
            try:
                send_message(self.socket, req)
                server_ans = get_message(self.socket)
                self.process_server_ans(server_ans)
            except (OSError, json.JSONDecodeError):
                logger.critical('Потеряно соединение с сервером!')
                raise ServerError('Потеряно соединение с сервером!')

        logger.info('Регистрация на сервере успешна')
        print('Регистрация на сервере успешна')

    # @staticmethod
    def create_message(self, action='presence', text='', destination=''):
        """Функция создаёт словарь с сообщением.
        По умолчанию это регистрационное сообщение presence"""
        message = {
            'action': action,
            'time': time.time(),
            'user': {
                'account_name': self.username,
                },
        }
        if text or destination:
            message['text'] = text
            message['destination'] = destination

        logger.debug('Сформировано сообщение %s', message)
        return message

    def process_server_ans(self, message):
        """ Обрабатывает сообщения от сервера. Ничего не возвращает.
            Генерирует исключение при ошибке.
            """
        logger.debug(f'Разбор сообщения от сервера: {message}')
        print(50*'=' + ' client_socket.process_server_ans')
        print(f'Разбор сообщения от сервера: {message}')

        # Если это подтверждение чего-либо
        if 'response' in message:
            if message['response'] == 200:
                return
            elif message['response'] == 300:
                logger.debug(f"300: {message['text']}")
                raise AccountNameNotUniq
            elif message['response'] == 400:
                raise ServerError(f"{message['text']}")
            elif message['response'] == 511:
                # формируем секретный ключ для авторизации на сервере
                line_bytes = open('../common/utils.py', 'rb').readlines()
                secret_key = b""
                for el in line_bytes:
                    secret_key += el
                # вычисляем хэш ключа
                hash = hmac.new(secret_key,
                                message['data'].encode('utf-8'),
                                'MD5')
                digest = hash.digest()
                my_ans = {'response': 511}
                my_ans['data'] = binascii.b2a_base64(digest).decode('ascii')

                send_message(self.socket, my_ans)
                self.process_server_ans(get_message(self.socket))
            else:
                logger.debug(f"Принят неизвестный код \
                    подтверждения {message['response']}")

        # Если это сообщение от пользователя добавляем в базу,
        # даём сигнал о новом сообщении
        if 'action' in message \
                and message['action'] == 'message' \
                and 'destination' in message \
                and message['destination'] == self.username \
                and 'text' in message:

            sender = message['user']['account_name']
            logger.debug(f"Получено сообщение от пользователя {sender}:"
                         f"{message['text']}")
            self.database.save_message(sender, message['text'], 'in')
            self.new_message.emit(sender)

    # Функция, обновляющая контакт - лист с сервера
    def contacts_list_update(self):
        """ Скачивает с сервера контакт лист пользователя """
        logger.debug(f'Запрос контакт листа для \
            пользователя {self.username}')
        req = self.create_message(action='get_contacts')
        with socket_lock:
            send_message(self.socket, req)
            time.sleep(0.5)
            ans = get_message(self.socket)
            logger.debug(f'Получен ответ {ans}')

        if 'response' in ans and ans['response'] == 200:
            for contact in ans['text']:
                self.database.add_contact(contact)
        else:
            logger.error('Не удалось обновить список контактов.')

    def user_list_update(self):
        """Обновляет таблицу известных пользователей."""

        logger.debug(f'Запрос списка известных \
            пользователей {self.username}')
        req = self.create_message(action='get_userlist')
        with socket_lock:
            send_message(self.socket, req)
            time.sleep(0.5)
            ans = get_message(self.socket)
        if 'response' in ans and ans['response'] == 200:
            self.database.add_users(ans['text'])
        else:
            logger.error('Не удалось обновить список \
                известных пользователей.')

    # Функция обновления переписки cо всеми пользователями
    # список берем с сервера
    def update_messages(self):
        logger.debug(f'Обновление переписки для \
            пользователя {self.username}')
        print(50*'=' + ' client_socket.update_message')
        print(f'Обновление переписки для пользователя {self.username}')
        req = self.create_message(action='get_messages')
        print('message to server:', req)
        with socket_lock:
            print('сокет освободился, отправляем запрос на сервер')
            send_message(self.socket, req)
            time.sleep(0.5)
            ans = get_message(self.socket)
            print('unswer from server:', ans)

        if 'response' in ans and ans['response'] == 200:
            if ans['text']:  # если список не пустой
                self.database.update_messages(ans['text'])
        else:
            logger.error('Не удалось обновить переписку пользователей.')
            print('Не удалось обновить переписку пользователей.')

    def add_contact(self, contact):
        """ Добавляет новый контакт """
        logger.debug(f'Добавление контакта {contact}')
        print(50*'=' + ' client_socket.add_contact')
        print(f'Добавление контакта {contact}')
        with socket_lock:
            print('сокет освободился, отправляем запрос на сервер')
            req = self.create_message(action='add_contact',
                                      destination=contact)
            print('request =', req)
            send_message(self.socket, req)
            time.sleep(0.5)
            self.process_server_ans(get_message(self.socket))
            self.database.add_contact(contact)

    def remove_contact(self, contact):
        """ Удаляет клиента из списка контактов """
        logger.debug(f'Удаление контакта {contact}')

        with socket_lock:
            req = self.create_message(action='del_contact',
                                      destination=contact)
            send_message(self.socket, req)
            time.sleep(0.5)
            self.process_server_ans(get_message(self.socket))
            self.database.del_contact(contact)

    # Функция закрытия соединения, отправляет сообщение о выходе.
    def socket_shutdown(self):
        self.running = False
        req = self.create_message(action='exit')
        with socket_lock:
            try:
                send_message(self.socket, req)
            except OSError:
                pass
        logger.debug('Сокет завершает работу.')
        time.sleep(0.5)

    # Функция отправки сообщения на сервер
    def send_message(self, destination, text):
        message = self.create_message(action='message',
                                      text=text,
                                      destination=destination)
        logger.debug(f'Сформирован словарь сообщения: {message}')
        print(50*'=' + ' client_socket.send_message')
        print(f'Сформирован словарь сообщения: {message}')
        # Необходимо дождаться освобождения сокета для отправки сообщения
        with socket_lock:
            print('сокет освободился, отправляем сообщение')
            send_message(self.socket, message)
            time.sleep(0.5)
            print('обрабатываем сообщение от сервера')
            ans = get_message(self.socket)
            print('получен ответ ', ans)
            self.process_server_ans(ans)
            logger.info(f'Отправлено сообщение для пользователя {destination}')
            print(f'Отправлено сообщение для пользователя {destination}')

    def run(self):
        logger.debug('Запущен процесс - приёмник сообщений с сервера.')
        print('Запущен процесс - приёмник сообщений с сервера.')

        while self.running:
            # Отдыхаем секунду и снова пробуем захватить сокет.
            # Если не сделать тут задержку, то отправка может
            # достаточно долго ждать освобождения сокета.
            time.sleep(1)
            with socket_lock:
                try:
                    self.socket.settimeout(0.5)
                    message = get_message(self.socket)
                except OSError as err:
                    if err.errno:
                        # выход по таймауту вернёт номер ошибки err.errno
                        # равный None поэтому, при выходе по таймауту мы
                        # сюда попросту не попадём
                        logger.critical('Потеряно соединение с сервером.')
                        self.running = False
                        self.connection_lost.emit()
                # Проблемы с соединением
                except (ConnectionError, ConnectionAbortedError,
                        ConnectionResetError, json.JSONDecodeError,
                        TypeError):
                    logger.debug('Потеряно соединение с сервером.')
                    self.running = False
                    self.connection_lost.emit()
                # Если сообщение получено, то вызываем функцию обработчик:
                else:
                    logger.debug(f'Принято сообщение с сервера: {message}')
                    self.process_server_ans(message)
                finally:
                    self.socket.settimeout(5)


if __name__ == '__main__':
    username = 'test_1'
    ip_address = '127.0.0.1'
    port = 7777

    from client_db import ClientDB
    database = ClientDB(username)
    ClientSocket(port, ip_address, database, username)
