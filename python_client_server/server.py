""" Программа сервера для получения приветствия от клиента и отправки ответа """
import sys, os, time
# from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
import socket
from select import select
import logging
from urllib import response
import logs.conf_server_log
from threading import Thread
from configparser import ConfigParser
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer 
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from server_gui import MainWindow, LoginHistoryWindow, MessageHistoryWindow, ConfigWindow, \
                        gui_create_model, create_stat_login, create_stat_message

import common.settings as cmnset
import common.utils as cmnutils
from common.decors import log
from metaclasses import ServerMaker
from server_db import ServerDB


# Инициализация серверного логера
SERVER_LOGGER = logging.getLogger('server')


class PortVerifi:
    def __set__(self, instance, value):
        if value < 1024 and value > 65535:
            SERVER_LOGGER.error(f'Номер порта за пределами диапазона 1024-65535')
            print(f'Ошибка: номер порта за пределами диапазона 1024-65535')
            sys.exit(1)
        else:
            instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        # owner - <class '__main__.Server'>
        # name - port
        self.name = name


class Server(Thread, metaclass=ServerMaker):
    port = PortVerifi()

    def __init__(self, listen_address, listen_port, database):
        # Параметры подключения
        self.addr = listen_address
        self.port = listen_port
         # База данных сервера
        self.database = database
        # список подключенных клиентов
        self.clients = []
        # список зарегистрированных пользователей и их сообщения
        self.messages = dict()
        # messages = {account_name:{'socket': client, 'message': message}}

        # Конструктор предка
        super().__init__()

    def init_socket(self):
        SERVER_LOGGER.info(f'Готовим сокет')
        # готовим сокет
        SERV_SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # SERV_SOCK = socket(AF_INET, SOCK_STREAM)  # в таком варианте не проходит проверка в метаклассе
        SERV_SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
        SERV_SOCK.bind((self.addr, self.port))
        SERV_SOCK.settimeout(1)
        # Начинаем слушать сокет.
        self.SERV_SOCK = SERV_SOCK
        self.SERV_SOCK.listen(cmnset.MAX_CONNECTIONS)

    def run(self):
        # Инициализация Сокета
        self.init_socket()
        
        while True: # Основной цикл программы сервера
            try:
                client, client_address = self.SERV_SOCK.accept()
            except OSError as err:
                pass
            else:
                print(f"Получен запрос на соединение от {str(client_address)}")
                self.clients.append(client)
            finally:
                wait = 0
                clients_read = []
                clients_write = []
                try:
                    clients_read, clients_write, errors = select(self.clients, self.clients, [], wait)
                except Exception as e:
                    # print(e)
                    pass

                for client_read in clients_read:
                    try:
                        message_from_client = cmnutils.get_message(client_read)
                        SERVER_LOGGER.debug("Получено сообщение от клиента %s: %s", client_read, message_from_client)
                        print(f"Получено сообщение от клиента:\n", client, message_from_client)
                    except Exception:
                        SERVER_LOGGER.info(f'Клиент {client_read} отключился от сервера.')
                        print(f'Клиент {client_read} отключился от сервера.')
                        self.clients.remove(client_read)
                        # ищем имя клиента
                        for key in self.messages.keys():
                            if self.messages[key]['socket'] == client_read:
                                user_name_delete = key
                        # удаляем клиента из активных
                        if user_name_delete:
                            del self.messages[user_name_delete]
                            self.database.user_logout(user_name_delete)
                    else:
                        # print('Параметры функции process_client_message:')
                        # print('message_from_client:', message_from_client)
                        # print('messages:', self.messages)
                        # print('client_read:', client_read)
                        # print('clients:', self.clients)
                        response = self.process_client_message(message_from_client, client_read)
                        print(f'Ответ клиенту {client_read}:\n{response}')
                
                for sender in self.messages:
                    # print('sender:', sender)
                    # messages = {account_name:{'socket': client, 'message': message}}
                    if 'message' in self.messages[sender] and self.messages[sender]['message']['text']:
                        if self.messages[sender]['message']['destination'] in self.messages.keys():
                            try:
                                recipient = self.messages[sender]['message']['destination']
                                cmnutils.send_message(self.messages[recipient]['socket'], \
                                                        self.messages[sender]['message'])
                                self.messages[sender]['message']['text'] = ''
                                SERVER_LOGGER.debug("Сообщение отправлено клиенту %s", \
                                                    self.messages[sender]['message']['destination'])
                            except:
                                SERVER_LOGGER.error("Не удается отправить сообщение клиенту %s", \
                                                    self.messages[sender]['message']['destination'])
                                print(f"Не удается отправить сообщение клиенту \
                                        {self.messages[sender]['message']['destination']}")

                                self.clients.remove(self.messages[recipient]['socket'])
                                self.messages[sender]['message']['text'] = ''
                        else:
                            cmnutils.send_message(self.messages[sender]['socket'], 
                                                    {'response':301, 
                                                    'error':'Получатель с таким имененм не активен'})
                            self.messages[sender]['message']['text'] = ''
    
    def process_client_message(self, message, client):
        SERVER_LOGGER.info(f'проверка сообщения от клента')
        if 'action' in message \
                and 'time' in message \
                and 'user' in message:

            # регистрация пользователя
            if message['action'] == 'presence':
                # если такого имени еще не было
                if message['user']['account_name'] not in self.messages.keys():
                    # messages = {account_name:{'socket': client, 'message': message}}
                    self.messages[message['user']['account_name']] = {'socket': client}
                    
                    # добавляем клиента в базу данных
                    username = message['user']['account_name']
                    client_ip, client_port = client.getpeername()
                    self.database.user_login(username, client_ip, client_port)

                    # отправляем сообщение клиенту
                    response = {'response': 200}
                    cmnutils.send_message(client, response)
                else:
                    SERVER_LOGGER.error('Имя пользователя %s уже занято', message['user']['account_name'])
                    response = {'response': 300,
                                'error': 'Имя пользователя уже занято'}
                    cmnutils.send_message(client, response)
                    return response
            
            # Отправка сообщения другому пользователю
            if message['action'] == 'message' \
                    and 'text' in message \
                    and 'destination' in message \
                    and message['destination']:

                # если получатель активен, то запоминаем сообщение для отправки
                if client == self.messages[message['user']['account_name']]['socket']:
                    self.messages[message['user']['account_name']]['message'] = message
                    # messages = {account_name:{'socket': client, 'message': message}}
                    self.database.process_message(message['user']['account_name'],
                                                message['destination'])
                else:
                    SERVER_LOGGER.error('Пользователь %s с сокетом %s не зарегистрирован', message['user']['account_name'], client)
                    response = {'response': 400,
                            'error': 'Пользователь не активен'}
                    return response

            # Запрос списка контактов
            if message['action'] == 'get_contacts':
                response = {'response': 200}
                user_login = message['user']['account_name']
                response['text'] = self.database.get_contacts(user_login)
                cmnutils.send_message(client, response)
                return(response)

            # Добавление контакта
            if message['action'] == 'add_contact' \
                    and 'destination' in message \
                    and message['destination']:
                
                user_login = message['user']['account_name']
                contact = message['destination']
                
                if self.database.add_contact(user_login, contact) == 1:
                    response = {'response': 200, 'text': 'пользователь добавлен в контакты'}
                elif self.database.add_contact(user_login, contact) == 2:
                    response = {'response': 200, 'text': 'такой контакт уже существует'}
                elif self.database.add_contact(user_login, contact) == 0:
                    response = {'response': 400, 'error': 'такого пользователя нет'}
                cmnutils.send_message(client, response)
                return response
            
            # Удаление контакта
            if message['action'] == 'del_contact' \
                    and 'destination' in message \
                    and message['destination']:

                user_login = message['user']['account_name']
                contact = message['destination']

                if self.database.del_contact(user_login, contact) == 1:
                    response = {'response': 200, 'text': 'пользователь удален из контактов'}
                elif self.database.del_contact(user_login, contact) == 2:
                    response = {'response': 200, 'text': 'такого контакта не существует'}
                elif self.database.del_contact(user_login, contact) == 0:
                    response = {'response': 400, 'error': 'такого пользователя нет'}
                cmnutils.send_message(client, response)
                return response

            # выход клиента с сервера
            if message['action'] == 'exit':
                self.clients.remove(client)
                client.close() 
                # удаляем клиента из активных
                del self.messages[message['user']['account_name']]
                self.database.user_logout(message['user']['account_name'])

            SERVER_LOGGER.debug('сообщение от клента правильное')
            return {'response': 200}
        else:
            SERVER_LOGGER.error('сообщение от клента не правильное')
            return {'response': 400,
                    'error': 'bad request'}


def print_help():
    print(50*'=')
    print('Поддерживаемые комманды:')
    print('gui       - графический интерфейс сервера')
    print('users     - список известных пользователей')
    print('connected - список подключённых пользователей')
    print('loghist   - история входов пользователя')
    print('exit      - завершение работы сервера.')
    print('help      - вывод справки по поддерживаемым командам')
    print(50*'=')


def main():
    SERVER_LOGGER.info(f'Определяем параметры сервера')
    config = ConfigParser()

    dir_path = os.path.dirname(os.path.abspath(__file__))
    config.read(os.path.join(dir_path, 'server.ini'), encoding='utf-8')
    DEFAULT_PORT = int(config['SETTINGS']['default_port'])
    DEFAULT_ADDR = config['SETTINGS']['listen_address']

    try:
        if '-p' in sys.argv:
            listen_port = int(sys.argv[sys.argv.index('-p') + 1])
        else:
            SERVER_LOGGER.debug('Используется порт по умолчанию %d', DEFAULT_PORT)
            listen_port = DEFAULT_PORT
    except IndexError:
        SERVER_LOGGER.error(f'После параметра -\'p\' необходимо указать номер порта.')
        sys.exit(1)

    try:
        if '-a' in sys.argv:
            listen_address = int(sys.argv[sys.argv.index('-a') + 1])
        else:
            SERVER_LOGGER.info(f'Используется адрес по умолчанию')
            listen_address = DEFAULT_ADDR
    except IndexError:
        SERVER_LOGGER.error('После параметра -\'а\' необходимо указать адрес для прослушивания сервером.')
        sys.exit(1)

    # Инициализация базы данных
    database = ServerDB(
                    os.path.join(
                        config['SETTINGS']['database_path'],
                        config['SETTINGS']['database_file'])
                    )

    # Создание экземпляра класса - сервера.
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    def server_gui():
        # Создаём графическое окружение для сервера:
        server_app = QApplication(sys.argv)
        main_window = MainWindow()

        # Функция, обновляющая список подключённых клиентов
        def list_update():
            main_window.active_clients_table.setModel(gui_create_model(database))
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
        
        # Инициализируем параметры окна
        main_window.statusBar().showMessage('Server Working')
        list_update()

        # Функция, создающая окно со статистикой клиентов
        def login_statistics():
            global stat_window
            stat_window = LoginHistoryWindow()
            stat_window.history_table.setModel(create_stat_login(database))
            stat_window.history_table.resizeColumnsToContents()
            stat_window.history_table.resizeRowsToContents()
            stat_window.show()

        def message_statistics():
            global stat_window
            stat_window = MessageHistoryWindow()
            stat_window.history_table.setModel(create_stat_message(database))
            stat_window.history_table.resizeColumnsToContents()
            stat_window.history_table.resizeRowsToContents()
            stat_window.show()

        # Функция создающяя окно с настройками сервера.
        def server_config():
            global config_window
            # Создаём окно и заносим в него текущие параметры
            config_window = ConfigWindow()
            config_window.db_path.insert(config['SETTINGS']['database_path'])
            config_window.db_file.insert(config['SETTINGS']['database_file'])
            config_window.port.insert(config['SETTINGS']['default_port'])
            config_window.ip.insert(config['SETTINGS']['listen_address'])
            config_window.save_btn.clicked.connect(save_server_config)

        # Функция сохранения настроек
        def save_server_config():
            global config_window
            message_box = QMessageBox()
            config['SETTINGS']['database_path'] = config_window.db_path.text()
            config['SETTINGS']['database_file'] = config_window.db_file.text()

            try:
                port = int(config_window.port.text())
            except ValueError:
                message_box.warning(config_window, 'Ошибка', 'Порт должен быть числом')
            else:
                config['SETTINGS']['listen_address'] = config_window.ip.text()
                if 1023 < port < 65536:
                    config['SETTINGS']['default_port'] = str(port)
                    with open('server.ini', 'w', encoding='utf-8') as conf:
                        config.write(conf)
                        message_box.information(
                            config_window, 'OK', 'Настройки успешно сохранены!')
                else:
                    message_box.warning(
                        config_window,
                        'Ошибка',
                        'Порт должен быть от 1024 до 65536')

        # Связываем кнопки с процедурами
        main_window.refresh_button.triggered.connect(list_update)
        main_window.login_history_button.triggered.connect(login_statistics)
        main_window.message_history_button.triggered.connect(message_statistics)
        main_window.config_btn.triggered.connect(server_config)

        # Таймер, обновляющий список клиентов 1 раз в секунду
        # timer = QTimer()
        # timer.timeout.connect(list_update)
        # timer.start(1000)
        
        # Запускаем GUI
        server_app.exec_()

    # консольная часть
    print('Сервер запущен!')
    # Печатаем справку:
    print_help()
    
    # Основной цикл сервера:
    while True:
        command = input('Введите команду: ')
        if command == 'help':
            print_help()
        elif command == 'exit':
            break
        elif command == 'gui':
            server_gui()
        elif command == 'users':
            for user in sorted(database.users_list()):
                print(f'Пользователь {user[0]}, последний вход: {user[1]}')
        elif command == 'connected':
            for user in sorted(database.active_users_list()):
                print(f'Пользователь {user[0]}, подключен: {user[1]}:{user[2]}, время установки соединения: {user[3]}')
        elif command == 'loghist':
            name = input('Введите имя пользователя для просмотра истории. '
                            'Для вывода всей истории, просто нажмите Enter: ')
            for user in sorted(database.login_history(name)):
                print(f'Пользователь: {user[0]} время входа: {user[1]}. Вход с: {user[2]}:{user[3]}')
        else:
            print('Команда не распознана.')


if __name__ == '__main__':
    main()
