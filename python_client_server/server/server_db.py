import os
import datetime
from sqlalchemy import create_engine, Column, Integer, \
                       String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pprint import pprint


class ServerDB:
    Base = declarative_base()

    class AllUsers(Base):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        login = Column(String, unique=True)
        passwd_hash = Column(String, default=None)
        pubkey = Column(String, default=None)
        ip = Column(String, default='0.0.0.0')
        port = Column(Integer, default=0)
        is_active = Column(Integer, default=0)
        last_conn = Column(DateTime)

        def __init__(self, login, passwd_hash, pubkey, ip, port):
            self.login = login
            self.passwd_hash = passwd_hash
            self.pubkey = pubkey
            self.ip = ip
            self.port = port
            self.is_active = 1
            self.last_conn = datetime.datetime.now()

    class UsersContacts(Base):
        __tablename__ = 'contacts'
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey('users.id'))
        contact = Column(Integer, ForeignKey('users.id'))

        def __init__(self, user_id, contact):
            self.user_id = user_id
            self.contact = contact

    class LoginHistory(Base):
        __tablename__ = 'login_history'
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey('users.id'))
        ip = Column(String)
        port = Column(Integer)
        last_conn = Column(DateTime)

        def __init__(self, user_id, ip, port, last_conn):
            self.user_id = user_id
            self.ip = ip
            self.port = port
            self.last_conn = last_conn

    class MessageHistory(Base):
        __tablename__ = 'message_history'
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey('users.id'))
        cnt_sent = Column(Integer)
        cnt_receive = Column(Integer)

        def __init__(self, user_id):
            self.user_id = user_id
            self.cnt_sent = 0
            self.cnt_receive = 0

    class Messages(Base):
        __tablename__ = 'messages'
        id = Column(Integer, primary_key=True)
        sender = Column(Integer, ForeignKey('users.id'))
        destination = Column(Integer, ForeignKey('users.id'))
        text = Column(String)
        date = Column(DateTime)

        def __init__(self, sender, destination, text, date):
            self.sender = sender
            self.destination = destination
            self.text = text
            self.date = date

    def __init__(self, path):
        # Создаём движок базы данных
        self.engine = create_engine(
            f'sqlite:///{path}',
            echo=False,
            pool_recycle=7200,
            connect_args={'check_same_thread': False})

        self.Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # Если в таблице активных пользователей есть записи,
        # то их необходимо удалить
        # Когда устанавливаем соединение, очищаем таблицу
        # активных пользователей
        # self.session.query(self.ActiveUsers).delete()
        self.session.query(self.AllUsers).update({'is_active': 0})
        self.session.commit()

    # Функция выполняется при входе пользователя,
    # фиксирует в базе сам факт входа
    def user_login(self, username, password, pubkey, ip_address, port):
        # Запрос в таблицу пользователей на наличие там
        # пользователя с таким именем
        result = self.session.query(self.AllUsers) \
                             .filter_by(login=username)

        # Если имя пользователя уже присутствует в таблице,
        # проверяем пароль и обновляем время последнего входа
        if result.count():
            user = result.first()
            if password == user.passwd_hash:
                user.ip = ip_address
                user.port = port
                user.is_active = 1
                user.last_conn = datetime.datetime.now()
                user.pubkey = pubkey
            else:
                return False  # пароль не совпадает
        else:  # Если нет, то создаём нового пользователя
            user = self.AllUsers(username,
                                 password,
                                 pubkey,
                                 ip_address,
                                 port)
            self.session.add(user)
            # Коммит здесь нужен, чтобы в db записался ID
            self.session.commit()
            user_in_message_history = self.MessageHistory(user.id)
            self.session.add(user_in_message_history)

        # и сохранить в историю входов
        # Создаем экземпляр класса self.LoginHistory,
        # через который передаем данные в таблицу
        history = self.LoginHistory(user.id,
                                    ip_address,
                                    port,
                                    datetime.datetime.now())
        self.session.add(history)
        self.session.commit()
        return True  # успешная регистрация

    # Функция фиксирует отключение пользователя
    def user_logout(self, username):
        # Запрашиваем пользователя, что покидает нас
        # получаем запись из таблицы AllUsers
        # print(f'user_logout({username})')
        user = self.session.query(self.AllUsers) \
                           .filter_by(login=username) \
                           .first()
        user.is_active = 0
        # Применяем изменения
        self.session.commit()

    # Функция возвращает список активных пользователей
    def active_users_list(self):
        # Запрашиваем соединение таблиц и собираем тюплы
        # имя, адрес, порт, время.
        query = self.session.query(self.AllUsers.login,
                                   self.AllUsers.ip,
                                   self.AllUsers.port,
                                   # self.AllUsers.is_active,
                                   self.AllUsers.last_conn) \
                            .filter_by(is_active=1)
        # Возвращаем список тюплов
        return query.all()

    # Функция возвращает историю входов по пользователю
    # или по всем пользователям
    def login_history(self, username=None):
        # Запрашиваем историю входа
        query = self.session.query(self.AllUsers.login,
                                   self.LoginHistory.last_conn,
                                   self.LoginHistory.ip,
                                   self.LoginHistory.port
                                   ).join(self.AllUsers)
        # Если было указано имя пользователя, то фильтруем по нему
        if username:
            query = query.filter(self.AllUsers.login == username)
        return query.all()

    # Функция возвращает количество переданных и полученных сообщений
    def message_history(self):
        query = self.session.query(
            self.AllUsers.login,
            self.AllUsers.last_conn,
            self.MessageHistory.cnt_sent,
            self.MessageHistory.cnt_receive
        ).join(self.AllUsers)
        # Возвращаем список кортежей
        return query.all()

    # Функция фиксирует передачу сообщения
    # и делает соответствующие отметки в БД
    def process_message(self, message):
        #
        sender = message['user']['account_name']
        destination = message['destination']
        text = message['text']
        # Получаем ID отправителя и получателя
        sender = self.session.query(self.AllUsers) \
                             .filter_by(login=sender) \
                             .first().id
        destination = self.session.query(self.AllUsers) \
                                  .filter_by(login=destination) \
                                  .first().id
        # Запрашиваем строки из истории и увеличиваем счётчики
        sender_row = self.session.query(self.MessageHistory) \
                                 .filter_by(user_id=sender) \
                                 .first()
        sender_row.cnt_sent += 1
        recipient_row = self.session.query(self.MessageHistory) \
                                    .filter_by(user_id=destination) \
                                    .first()
        recipient_row.cnt_receive += 1
        # сохраняем сообщение
        row = self.Messages(sender, destination, text, datetime.datetime.now())
        self.session.add(row)
        self.session.commit()

    # Функция возвращает всю переписку пользователя
    def get_messages(self, username):
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers) \
                                .filter_by(login=username) \
                                .first()
        # список исходящих сообщений для sender
        req_1 = self.session.query(self.Messages) \
                            .filter_by(sender=user.id)
        # список входящих сообщений для sender
        req_2 = self.session.query(self.Messages) \
                            .filter_by(destination=user.id)
        # sender, destination, text, date
        messages = []
        for el in req_1.all():
            # 2022-06-26 15:02:52
            messages.append(('out',
                             el.destination,
                             el.text,
                             el.date.strftime('%Y-%m-%d %H:%M:%S')))

        for el in req_2.all():
            messages.append(('in',
                             el.sender,
                             el.text,
                             el.date.strftime('%Y-%m-%d %H:%M:%S')))
        # print(messages)
        return messages

    # Функция добавляет контакт для пользователя.
    def add_contact(self, login, contact):
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers) \
                           .filter_by(login=login) \
                           .first()
        contact = self.session.query(self.AllUsers) \
                              .filter_by(login=contact) \
                              .first()
        # Проверяем что не дубль и что контакт может
        # существовать (полю пользователь мы доверяем)
        if not contact:
            return 0  # такого пользователя нет в системе

        if self.session.query(self.UsersContacts) \
                       .filter_by(user_id=user.id,
                                  contact=contact.id) \
                       .count():
            return 2  # такой контакт уже есть
        # Создаём объект и заносим его в базу
        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()
        return 1  # контакт добавлен

    # Функция удаляет контакт из базы данных
    def del_contact(self, login, contact):
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers) \
                           .filter_by(login=login) \
                           .first()
        contact = self.session.query(self.AllUsers) \
                              .filter_by(login=contact) \
                              .first()

        # Проверяем что контакт может существовать
        # (полю пользователь мы доверяем)
        if not contact:
            return 0  # такого пользователя нет в системе

        if not self.session.query(self.UsersContacts) \
                           .filter_by(user_id=user.id,
                                      contact=contact.id) \
                           .count():
            return 2  # такой контакт не существует

        # Удаляем требуемое
        self.session.query(self.UsersContacts) \
                    .filter(self.UsersContacts.user_id == user.id,
                            self.UsersContacts.contact == contact.id) \
                    .delete()
        self.session.commit()
        return 1

    def get_contacts(self, login):
        # Запрашиваем указанного пользователя
        user = self.session.query(self.AllUsers) \
                           .filter_by(login=login) \
                           .first()

        # Запрашиваем его список контактов
        query = self.session.query(self.UsersContacts,
                                   self.AllUsers.login) \
                            .filter_by(user_id=user.id) \
                            .join(self.AllUsers,
                                  self.UsersContacts.contact
                                  == self.AllUsers.id)

        # выбираем только имена пользователей и возвращаем их.
        return [contact[1] for contact in query.all()]

    # Функция возвращает список известных пользователей
    # со временем последнего входа.
    def get_userlist(self):
        query = self.session.query(
            self.AllUsers.login,
            self.AllUsers.last_conn,
        )
        # Возвращаем список тюплов
        # return query.all()
        return [contact[0] for contact in query.all()]

    def get_hash(self, login):
        """Метод получения хэша пароля пользователя."""
        user = self.session.query(self.AllUsers) \
                           .filter_by(login=login) \
                           .first()
        return user.passwd_hash

    def get_pubkey(self, login):
        """Метод получения публичного ключа пользователя."""
        user = self.session.query(self.AllUsers) \
                           .filter_by(login=login) \
                           .first()
        return user.pubkey


if __name__ == '__main__':
    path = os.path.dirname(os.path.abspath(__file__))
    db = ServerDB(os.path.join(path, 'server_db.db3'))

    print(50*'=')
    print('login user test_1')
    db.user_login('test_1', b'password_test_1',
                  b'public key test_1', '192.168.1.4', 8888)
    print('login user test_2')
    db.user_login('test_2', b'password_test_2',
                  b'public key test_2', '192.168.1.5', 7777)
    print('login user test_3')
    db.user_login('test_3', b'password_test_3',
                  b'public key test_3', '192.168.1.6', 7778)

    # выводим список активных пользователей
    print(50*'=')
    print('active users list:')
    pprint(db.active_users_list())

    # выполянем 'отключение' пользователя
    print(50*'=')
    print('logout user test_1')
    db.user_logout('test_1')

    # выводим список всех пользователей
    print(50*'=')
    print('all users list:')
    pprint(db.get_userlist())

    # выводим список активных пользователей
    print(50*'=')
    print('active users list:')
    pprint(db.active_users_list())

    print(50*'=')
    print('logout user test_2')
    db.user_logout('test_2')

    print(50*'=')
    print('all users list:')
    pprint(db.get_userlist())

    print(50*'=')
    print('active users list:')
    pprint(db.active_users_list())

    print(50*'=')
    print('login user test_1 with wrong password')
    if db.user_login('test_1', b'password_test1',
                     b'public key test_1', '192.168.1.4', 8888):
        print('success')
    else:
        print('not success')

    # запрашиваем историю входов по пользователю
    print(50*'=')
    print('login history for user test_1:')
    pprint(db.login_history('test_1'))

    print(50*'=')
    print('add contacts test_2 - test_1')
    db.add_contact('test_2', 'test_1')
    print('add contacts test_1 - test_3')
    db.add_contact('test_1', 'test_3')
    print('add contacts test_1 - test_6')
    db.add_contact('test_1', 'test_6')

    print(50*'=')
    print('print contacts user test_1')
    pprint(db.get_contacts('test_1'))
    print()
    print('print contacts user test_2')
    pprint(db.get_contacts('test_2'))

    print(50*'=')
    print('remove contacts test_1 - test_3')
    db.del_contact('test_1', 'test_3')
    print('print contacts user test_1')
    pprint(db.get_contacts('test_1'))

    print(50*'=')
    print('send message from test_1 to test_3')
    message = {'action': 'message',
               'time': datetime.datetime.now(),
               'user': {'account_name': 'test_1'},
               'destination': 'test_3',
               'text': 'some message from test_1 to test_3'}
    db.process_message(message)

    print(50*'=')
    print('get messages test_1 - test_3')
    db.get_messages('test_1')

    print(50*'=')
    print('get messages test_3 - test_1')
    db.get_messages('test_3')
