""" Программа сервера для получения приветствия от клиента и отправки ответа """
import sys
# from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
import socket
from select import select
import logging
from urllib import response
import logs.conf_server_log
from threading import Thread
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
                else:
                    SERVER_LOGGER.error('Пользователь %s с сокетом %s не зарегистрирован', message['user']['account_name'], client)
                    response = {'response': 400,
                            'error': 'Пользователь не активен'}
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
    print('Поддерживаемые комманды:')
    print('users - список известных пользователей')
    print('connected - список подключённых пользователей')
    print('loghist - история входов пользователя')
    print('exit - завершение работы сервера.')
    print('help - вывод справки по поддерживаемым командам')


def main():
    SERVER_LOGGER.info(f'Определяем параметры сервера')
    try:
        if '-p' in sys.argv:
            listen_port = int(sys.argv[sys.argv.index('-p') + 1])
        else:
            SERVER_LOGGER.debug('Используется порт по умолчанию %d', cmnset.DEFAULT_PORT)
            listen_port = cmnset.DEFAULT_PORT
    except IndexError:
        SERVER_LOGGER.error(f'После параметра -\'p\' необходимо указать номер порта.')
        sys.exit(1)

    try:
        if '-a' in sys.argv:
            listen_address = int(sys.argv[sys.argv.index('-a') + 1])
        else:
            SERVER_LOGGER.info(f'Используется адрес по умолчанию')
            listen_address = ''
    except IndexError:
        SERVER_LOGGER.error('После параметра -\'а\' необходимо указать адрес для прослушивания сервером.')
        sys.exit(1)

    # Инициализация базы данных
    database = ServerDB()

    # Создание экземпляра класса - сервера.
    server = Server(listen_address, listen_port, database)
    server.daemon = True
    server.start()

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
