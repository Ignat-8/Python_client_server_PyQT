""" Программа сервера для получения приветствия от клиента
и отправки ответа """

import sys
import os
import socket
import logging
import binascii
import hmac
from select import select
from threading import Thread
from configparser import ConfigParser
from PyQt5.QtWidgets import QApplication, QMessageBox
from server_gui import MainWindow, LoginHistoryWindow, \
                        MessageHistoryWindow, ConfigWindow, \
                        gui_create_model, create_stat_login, \
                        create_stat_message
sys.path.append('../')
import common.settings as cmnset
import common.utils as cmnutils
from common.decors import login_required
from metaclasses import ServerMaker
from server_db import ServerDB


# Инициализация серверного логера
SERVER_LOGGER = logging.getLogger('server')


class PortVerifi:

    def __set__(self, instance, value):
        if value < 1024 and value > 65535:
            SERVER_LOGGER.error('Номер порта за пределами \
                                    диапазона 1024-65535')
            print('Ошибка: номер порта за пределами \
                            диапазона 1024-65535')
            sys.exit(1)
        else:
            instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        # owner - <class '__main__.Server'>
        # name - port
        self.name = name


class MyServer(Thread, metaclass=ServerMaker):
    port = PortVerifi()

    def __init__(self, listen_address, listen_port, database):
        # Параметры подключения
        self.addr = listen_address
        self.port = listen_port
        # База данных сервера
        self.database = database
        # список подключенных клиентов
        self.clients = []
        # список активных пользователей и их сообщения
        self.messages = dict()
        # messages = {account_name:{'socket': client, 'message': message}}

        # Конструктор предка
        super().__init__()

    def init_socket(self):
        SERVER_LOGGER.info('Готовим сокет')
        # готовим сокет
        SERV_SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # в таком варианте не проходит проверка в метаклассе
        # SERV_SOCK = socket(AF_INET, SOCK_STREAM)
        SERV_SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        SERV_SOCK.bind((self.addr, self.port))
        SERV_SOCK.settimeout(1)
        # Начинаем слушать сокет.
        self.SERV_SOCK = SERV_SOCK
        self.SERV_SOCK.listen(cmnset.MAX_CONNECTIONS)

    def run(self):
        # Инициализация Сокета
        self.init_socket()

        while True:  # Основной цикл программы сервера
            try:
                client, client_address = self.SERV_SOCK.accept()
            except OSError:
                pass
            else:
                print(f"Получен запрос на соединение от \
                    {str(client_address)}")
                self.clients.append(client)
            finally:
                wait = 0
                clients_read = []
                clients_write = []
                try:
                    clients_read, clients_write, errors = select(self.clients,
                                                                 self.clients,
                                                                 [],
                                                                 wait)
                except Exception:
                    pass

                for client_read in clients_read:
                    try:
                        message_from_client = cmnutils.get_message(client_read)
                        SERVER_LOGGER.debug("Получено сообщение от клиента \
                                                %s: %s",
                                            client_read,
                                            message_from_client)
                        print("Получено сообщение от клиента:\n",
                              client, message_from_client)
                    except Exception:
                        SERVER_LOGGER.info(f'Клиент {client_read} отключился \
                                                от сервера.')
                        print(f'Клиент {client_read} отключился от сервера.')
                        self.clients.remove(client_read)
                        # ищем имя клиента
                        user_name_delete = ''
                        for key in self.messages.keys():
                            if self.messages[key]['socket'] == client_read:
                                user_name_delete = key
                        # удаляем клиента из активных
                        if user_name_delete:
                            del self.messages[user_name_delete]
                            self.database.user_logout(user_name_delete)
                    else:
                        self.process_client_message(
                            message_from_client,
                            client_read)

                for sender in self.messages:
                    # print('sender:', sender)
                    # messages = {account_name:{'socket': client,
                    #                           'message': message}}
                    if 'message' in self.messages[sender] \
                            and self.messages[sender]['message']['text']:
                        if self.messages[sender]['message']['destination'] in self.messages.keys():
                            try:
                                recipient = self.messages[sender]['message']['destination']
                                cmnutils.send_message(self.messages[recipient]['socket'],
                                                      self.messages[sender]['message'])
                                self.messages[sender]['message']['text'] = ''
                                SERVER_LOGGER.debug(
                                    "Сообщение отправлено клиенту %s",
                                    self.messages[sender]['message']['destination'])
                                cmnutils.send_message(
                                    self.messages[sender]['socket'],
                                    {'response': 200,
                                     'text': 'Сообщение отправлено'})
                            except Exception:
                                SERVER_LOGGER.error(
                                    "Не удается отправить сообщение клиенту %s",
                                    self.messages[sender]['message']['destination'])
                                print(f"Не удается отправить сообщение клиенту \
                                        {self.messages[sender]['message']['destination']}")

                                self.clients.remove(self.messages[recipient]['socket'])
                                self.messages[sender]['message']['text'] = ''
                                cmnutils.send_message(
                                    self.messages[sender]['socket'],
                                    {'response': 400,
                                     'text': 'Сообщение не отправлено'})
                        else:
                            cmnutils.send_message(
                                self.messages[sender]['socket'],
                                {'response': 201,
                                 'text': 'Получатель с таким именем не активен'})
                            self.messages[sender]['message']['text'] = ''

    @login_required
    def process_client_message(self, message, client):
        SERVER_LOGGER.info('проверка сообщения от клента')
        if 'action' in message \
                and 'time' in message \
                and 'user' in message:

            # авторизация и регистрация пользователя
            if message['action'] == 'presence':
                # если такого имени еще не было,
                # т.е. пользователь не активен или не зарегистрирован
                login = message['user']['account_name']
                if login not in self.messages.keys():
                    # проводим авторизацию
                    response = {'response': 511}
                    random_str = binascii.hexlify(os.urandom(64))
                    # В словарь байты нельзя, декодируем
                    # (json.dumps -> TypeError)
                    response['data'] = random_str.decode('ascii')
                    # формируем секретный ключ для авторизации на сервере
                    line_bytes = open('../common/utils.py', 'rb').readlines()
                    secret_key = b""
                    for el in line_bytes:
                        secret_key += el
                    # вычисляем хэш ключай
                    hash = hmac.new(secret_key, random_str, 'MD5')
                    digest = hash.digest()
                    try:  # Обмен с клиентом
                        cmnutils.send_message(client, response)
                        ans = cmnutils.get_message(client)
                    except OSError as err:
                        SERVER_LOGGER.debug('Error in auth, data:',
                                            exc_info=err)
                        self.socket.close()
                        return

                    client_digest = binascii.a2b_base64(ans['data'])
                    # Если ответ клиента корректный, то сохраняем его
                    # в список пользователей.
                    if 'response' in ans and ans['response'] == 511 and \
                            hmac.compare_digest(digest, client_digest):

                        # messages = {account_name:{'socket': client,
                        #                           'message': message}}
                        login = message['user']['account_name']
                        self.messages[login] = {'socket': client}

                        # добавляем клиента в список активных
                        username = message['user']['account_name']
                        password = message['user']['password']
                        pubkey = message['user']['public_key']
                        client_ip, client_port = client.getpeername()
                        login_success = self.database \
                                            .user_login(username,
                                                        password,
                                                        pubkey,
                                                        client_ip,
                                                        client_port)
                        if login_success:
                            response = {'response': 200}
                        else:
                            response = {'response': 400,
                                        'text': 'Не верное имя пользователя \
                                        или пароль'}
                        # отправляем сообщение клиенту
                        cmnutils.send_message(client, response)
                    else:
                        response = {'response': 400,
                                    'text': 'Не успешная авторизация'}
                        # отправляем сообщение клиенту
                        cmnutils.send_message(client, response)
                else:
                    SERVER_LOGGER.error('Имя пользователя %s уже занято',
                                        message['user']['account_name'])
                    response = {'response': 400,
                                'text': 'Имя пользователя уже занято'}
                    cmnutils.send_message(client, response)
                    return response

            # Отправка сообщения другому пользователю
            if message['action'] == 'message' \
                    and 'text' in message \
                    and 'destination' in message \
                    and message['destination']:

                # сохраняем сообщение в базе данных
                self.database.process_message(message)

                # если получатель активен, то запоминаем сообщение для отправки
                login = message['user']['account_name']
                if client == self.messages[login]['socket']:
                    # messages = {account_name:{'socket': client,
                    #                           'message': message}}
                    user_name = message['user']['account_name']
                    self.messages[user_name]['message'] = message
                    response = {'response': 200,
                                'text': 'сообщение поставлено \
                                в очередь отправки'}
                    # cmnutils.send_message(client, response)
                    return response
                else:
                    SERVER_LOGGER.error(f"Пользователь \
                                        {message['user']['account_name']} \
                                        с сокетом {client} не активен")
                    print(f"Пользователь {message['user']['account_name']} \
                            с сокетом {client} не активен")
                    response = {'response': 400,
                                'text': 'Пользователь не активен'}
                    cmnutils.send_message(client, response)
                    return response

            # Запрос переписки пользователя
            if message['action'] == 'get_messages' \
                    and message['user']['account_name']:
                # логин пользователя, для которого выгружаем переписку
                user_login = message['user']['account_name']
                # формируем сообщение для отправки
                response = {'response': 200}
                response['text'] = self.database.get_messages(user_login)
                print('!!!! get_messages:', response)
                # отправляем сообщение
                cmnutils.send_message(client, response)
                return(response)

            # Запрос списка контактов для пользователя
            if message['action'] == 'get_contacts':
                response = {'response': 200}
                user_login = message['user']['account_name']
                response['text'] = self.database.get_contacts(user_login)
                cmnutils.send_message(client, response)
                return(response)

            # Запрос списка всех пользователей
            if message['action'] == 'get_userlist':
                response = {'response': 200}
                response['text'] = self.database.get_userlist()
                print(response)
                cmnutils.send_message(client, response)
                return(response)

            # Добавление контакта
            if message['action'] == 'add_contact' \
                    and 'destination' in message \
                    and message['destination']:

                user_login = message['user']['account_name']
                contact = message['destination']

                if self.database.add_contact(user_login, contact) == 1:
                    response = {'response': 200,
                                'text': 'пользователь добавлен в контакты'}
                elif self.database.add_contact(user_login, contact) == 2:
                    response = {'response': 200,
                                'text': 'такой контакт уже существует'}
                elif self.database.add_contact(user_login, contact) == 0:
                    response = {'response': 400,
                                'text': 'такого пользователя нет'}
                cmnutils.send_message(client, response)
                return response

            # Удаление контакта
            if message['action'] == 'del_contact' \
                    and 'destination' in message \
                    and message['destination']:

                user_login = message['user']['account_name']
                contact = message['destination']

                if self.database.del_contact(user_login, contact) == 1:
                    response = {'response': 200,
                                'text': 'пользователь удален из контактов'}
                elif self.database.del_contact(user_login, contact) == 2:
                    response = {'response': 400,
                                'text': 'такого контакта не существует'}
                elif self.database.del_contact(user_login, contact) == 0:
                    response = {'response': 400,
                                'text': 'такого пользователя нет'}
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
                    'text': 'bad request'}


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
    SERVER_LOGGER.info('Определяем параметры сервера')
    config = ConfigParser()

    dir_path = os.path.dirname(os.path.abspath(__file__))
    config.read(os.path.join(dir_path, 'server.ini'),
                encoding='utf-8')
    DEFAULT_PORT = int(config['SETTINGS']['default_port'])
    DEFAULT_ADDR = config['SETTINGS']['listen_address']

    try:
        if '-p' in sys.argv:
            listen_port = int(sys.argv[sys.argv.index('-p') + 1])
        else:
            SERVER_LOGGER.debug('Используется порт по умолчанию %d',
                                DEFAULT_PORT)
            listen_port = DEFAULT_PORT
    except IndexError:
        SERVER_LOGGER.error('После параметра -\'p\' необходимо \
                            указать номер порта.')
        sys.exit(1)

    try:
        if '-a' in sys.argv:
            listen_address = int(sys.argv[sys.argv.index('-a') + 1])
        else:
            SERVER_LOGGER.info('Используется адрес по умолчанию')
            listen_address = DEFAULT_ADDR
    except IndexError:
        SERVER_LOGGER.error('После параметра -\'а\' необходимо \
                            указать адрес для прослушивания сервером.')
        sys.exit(1)

    # Инициализация базы данных
    database = ServerDB(
                    os.path.join(
                        config['SETTINGS']['database_path'],
                        config['SETTINGS']['database_file'])
                    )

    # Создание экземпляра класса - сервера.
    server = MyServer(listen_address, listen_port, database)
    server.daemon = True
    server.start()

    def server_gui():
        # Создаём графическое окружение для сервера:
        server_app = QApplication(sys.argv)
        main_window = MainWindow()

        # Функция, обновляющая список подключённых клиентов
        def list_update():
            main_window.active_clients_table \
                .setModel(gui_create_model(database))
            main_window.active_clients_table \
                .resizeColumnsToContents()
            main_window.active_clients_table \
                .resizeRowsToContents()

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
                message_box.warning(config_window,
                                    'Ошибка',
                                    'Порт должен быть числом')
            else:
                config['SETTINGS']['listen_address'] = config_window.ip.text()
                if 1023 < port < 65536:
                    config['SETTINGS']['default_port'] = str(port)
                    with open('server.ini', 'w', encoding='utf-8') as conf:
                        config.write(conf)
                        message_box.information(
                            config_window,
                            'OK',
                            'Настройки успешно сохранены!')
                else:
                    message_box.warning(
                        config_window,
                        'Ошибка',
                        'Порт должен быть от 1024 до 65536')

        # Связываем кнопки с процедурами
        main_window.refresh_button \
            .triggered \
            .connect(list_update)
        main_window.login_history_button \
            .triggered \
            .connect(login_statistics)
        main_window.message_history_button \
            .triggered \
            .connect(message_statistics)
        main_window.config_btn \
            .triggered \
            .connect(server_config)

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
                print(f'Пользователь {user[0]}, \
                      последний вход: {user[1]}')
        elif command == 'connected':
            for user in sorted(database.active_users_list()):
                print(f'Пользователь {user[0]}, \
                      подключен: {user[1]}:{user[2]}, \
                      время установки соединения: {user[3]}')
        elif command == 'loghist':
            name = input('Введите имя пользователя для просмотра истории. '
                         'Для вывода всей истории, просто нажмите Enter: ')
            for user in sorted(database.login_history(name)):
                print(f'Пользователь: \
                        {user[0]} время входа: {user[1]}. \
                        Вход с: {user[2]}:{user[3]}')
        else:
            print('Команда не распознана.')


if __name__ == '__main__':
    main()
