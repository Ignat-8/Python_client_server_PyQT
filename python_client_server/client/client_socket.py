from socket import socket, AF_INET, SOCK_STREAM
import sys
import time
import logging
import json
import threading
from PyQt5.QtCore import pyqtSignal, QObject

sys.path.append('../')
from common.utils import *
from common.settings import *
from common.errors import *


# Логер и объект блокировки для работы с сокетом.
logger = logging.getLogger('client')
socket_lock = threading.Lock()


# Класс - Транспорт, отвечает за взаимодействие с сервером
class ClientSocket(threading.Thread, QObject):
    # Сигналы новое сообщение и потеря соединения
    new_message = pyqtSignal(str)
    connection_lost = pyqtSignal()

    def __init__(self, port, ip_address, database, username):
        # Вызываем конструктор предка
        threading.Thread.__init__(self)
        QObject.__init__(self)

        self.database = database  # Класс База данных - работа с базой
        self.username = username  # Имя пользователя
        self.socket = None  # Сокет для работы с сервером
        
        # Устанавливаем соединение:
        self.connection_init(port, ip_address)

        # Обновляем таблицы известных пользователей и контактов
        try:
            self.user_list_update()
            self.contacts_list_update()
        except OSError as err:
            if err.errno:
                logger.critical(f'Потеряно соединение с сервером.')
                raise ServerError('Потеряно соединение с сервером!')
            logger.error('Timeout соединения при обновлении списка пользователей.')
        except json.JSONDecodeError:
            logger.critical(f'Потеряно соединение с сервером.')
            raise ServerError('Потеряно соединение с сервером!')
        
        self.running = True  # Флаг продолжения работы транспорта.

    def connection_init(self, port, ip):
        """ Инициализирует сокет и регистрирует на сервере """

        self.socket = socket(AF_INET, SOCK_STREAM)
        # Таймаут необходим для освобождения сокета.
        self.socket.settimeout(5)

        # Соединяемся, 5 попыток соединения, флаг успеха ставим в True если удалось
        connected = False
        for i in range(5):
            logger.info(f'Попытка подключения №{i + 1}')
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
            raise ServerError('Не удалось установить соединение с сервером')

        logger.debug('Установлено соединение с сервером')
        print('Установлено соединение с сервером')

        # Посылаем серверу приветственное сообщение и получаем ответ,
        # что всё нормально или ловим исключение.
        try:
            with socket_lock:
                req = self.create_message()
                send_message(self.socket, req)
                self.process_server_ans(get_message(self.socket))
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
        print(f'Разбор сообщения от сервера: {message}')

        # Если это подтверждение чего-либо
        if 'response' in message:
            if message['response'] == 200:
                return
            elif message['response'] == 300:
                logger.debug(f"300: {message['error']}")
                raise AccountNameNotUniq
            elif message['response'] == 400:
                raise ServerError(f"{message['error']}")
            else:
                logger.debug(f"Принят неизвестный код подтверждения {message['response']}")
        else:
            raise ReqFieldMissingError('response')

        # Если это сообщение от пользователя добавляем в базу, даём сигнал о новом сообщении
        if 'action' in message \
                and message['action'] == 'message' \
                and 'destination' in message \
                and message['destination'] == self.username \
                and 'text' in message:
            
            sender = message['user']['account_name']
            logger.debug(f"Получено сообщение от пользователя {sender}:"
                         f"{message['text']}")
            self.database.save_message(sender, 'in', message['text'])
            self.new_message.emit(message['text'])
        
    # Функция, обновляющая контакт - лист с сервера
    def contacts_list_update(self):
        """ Скачивает с сервера контакт лист пользователя """
        logger.debug(f'Запрос контакт листа для пользователя {self.username}')
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
        """ Обновляет таблицу известных пользователей."""
        logger.debug(f'Запрос списка известных пользователей {self.username}')
        req = self.create_message(action='get_userlist')
        with socket_lock:
            send_message(self.socket, req)
            time.sleep(0.5)
            ans = get_message(self.socket)
        if 'response' in ans and ans['response'] == 200:
            self.database.add_users(ans['text'])
        else:
            logger.error('Не удалось обновить список известных пользователей.')

    def add_contact(self, contact):
        """ Добавляет новый контакт """
        logger.debug(f'Добавление контакта {contact}')
        with socket_lock:
            req = self.create_message(action='add_contact', 
                                        destination=contact)
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

        # Необходимо дождаться освобождения сокета для отправки сообщения
        with socket_lock:
            send_message(self.socket, message)
            self.process_server_ans(get_message(self.socket))
            logger.info(f'Отправлено сообщение для пользователя {destination}')

    def run(self):
        logger.debug('Запущен процесс - приёмник сообщений с сервера.')
        print('Запущен процесс - приёмник сообщений с сервера.')

        while self.running:
            # Отдыхаем секунду и снова пробуем захватить сокет. Если не сделать тут задержку,
            # то отправка может достаточно долго ждать освобождения сокета.
            time.sleep(1)
            with socket_lock:
                try:
                    self.socket.settimeout(0.5)
                    message = get_message(self.socket)
                except OSError as err:
                    if err.errno:
                        # выход по таймауту вернёт номер ошибки err.errno равный None
                        # поэтому, при выходе по таймауту мы сюда попросту не попадём
                        logger.critical(f'Потеряно соединение с сервером.')
                        self.running = False
                        self.connection_lost.emit()
                # Проблемы с соединением
                except (ConnectionError, ConnectionAbortedError,
                        ConnectionResetError, json.JSONDecodeError, TypeError):
                    logger.debug(f'Потеряно соединение с сервером.')
                    self.running = False
                    self.connection_lost.emit()
                # Если сообщение получено, то вызываем функцию обработчик:
                else:
                    logger.debug(f'Принято сообщение с сервера: {message}')
                    self.process_server_ans(message)
                finally:
                    self.socket.settimeout(5)


if __name__ == '__main__':
    from client_db import ClientDB
    database = ClientDB('test1')
    ClientSocket(7777, '127.0.0.1', database, 'test1')