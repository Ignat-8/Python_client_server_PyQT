from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime, os
from pprint import pprint


class ServerDB:
    Base = declarative_base()

    class AllUsers(Base):
        __tablename__ = 'users_all'
        id = Column(Integer, primary_key=True)
        login = Column(String, unique=True)
        last_conn = Column(DateTime)

        def __init__(self, login):
            self.login = login
            self.last_conn = datetime.datetime.now()

    class ActiveUsers(Base):
        __tablename__ = 'users_active'
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey('users_all.id'), unique=True)
        ip = Column(String)
        port = Column(Integer)
        time_conn = Column(DateTime)

        def __init__(self, user_id, ip, port, time_conn):
            self.user_id = user_id
            self.ip = ip
            self.port = port
            self.time_conn = time_conn
    
    class UsersContacts(Base):
        __tablename__ = 'users_contacts'
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey('users_all.id'))
        contact = Column(Integer, ForeignKey('users_all.id'))

        def __init__(self, user_id, contact):
            self.user_id = user_id
            self.contact = contact

    class LoginHistory(Base):
        __tablename__ = 'login_history'
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey('users_all.id'))
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
        user_id = Column(Integer, ForeignKey('users_all.id'))
        cnt_sent = Column(Integer)
        cnt_receive = Column(Integer)
        
        def __init__(self, user_id):
            self.user_id = user_id
            self.cnt_sent = 0
            self.cnt_receive = 0


    def __init__(self, path):
        # Создаём движок базы данных
        self.engine = create_engine(f'sqlite:///{path}', 
                                    echo=False, 
                                    pool_recycle=7200,
                                    connect_args={'check_same_thread': False})

        self.Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        # Если в таблице активных пользователей есть записи, то их необходимо удалить
        # Когда устанавливаем соединение, очищаем таблицу активных пользователей
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()

    # Функция выполняется при входе пользователя, фиксирует в базе сам факт входа
    def user_login(self, username, ip_address, port):
        # Запрос в таблицу пользователей на наличие там пользователя с таким именем
        result = self.session.query(self.AllUsers).filter_by(login=username)
         
        # Если имя пользователя уже присутствует в таблице, обновляем время последнего входа
        if result.count():
            user = result.first()
            user.last_conn = datetime.datetime.now()
        # Если нет, то создаём нового пользователя
        else:
            # Создаем экземпляр класса self.AllUsers, через который передаем данные в таблицу
            user = self.AllUsers(username)
            self.session.add(user)
            # Коммит здесь нужен, чтобы в db записался ID
            self.session.commit()
            user_in_message_history = self.MessageHistory(user.id)
            self.session.add(user_in_message_history)

        # Теперь можно создать запись в таблицу активных пользователей о факте входа.
        # Создаем экземпляр класса self.ActiveUsers, через который передаем данные в таблицу
        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(new_active_user)

        # и сохранить в историю входов
        # Создаем экземпляр класса self.LoginHistory, через который передаем данные в таблицу
        history = self.LoginHistory(user.id, ip_address, port, datetime.datetime.now())
        self.session.add(history)

        # Сохраняем изменения
        self.session.commit()

    # Функция фиксирует отключение пользователя
    def user_logout(self, username):
        # Запрашиваем пользователя, что покидает нас
        # получаем запись из таблицы AllUsers
        # print(f'user_logout({username})')
        user = self.session.query(self.AllUsers).filter_by(login=username).first()

        # Удаляем его из таблицы активных пользователей.
        if user:  # если есть такой поьзователь
            self.session.query(self.ActiveUsers).filter_by(user_id=user.id).delete()

        # Применяем изменения
        self.session.commit()

    # Функция возвращает список известных пользователей со временем последнего входа.
    def users_list(self):
        query = self.session.query(
            self.AllUsers.login,
            self.AllUsers.last_conn,
        )
        # Возвращаем список тюплов
        return query.all()

    # Функция возвращает список активных пользователей
    def active_users_list(self):
        # Запрашиваем соединение таблиц и собираем тюплы имя, адрес, порт, время.
        query = self.session.query(
            self.AllUsers.login,
            self.ActiveUsers.ip,
            self.ActiveUsers.port,
            self.ActiveUsers.time_conn
            ).join(self.AllUsers)
        # Возвращаем список тюплов
        return query.all()

    # Функция возвращает историю входов по пользователю или по всем пользователям
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

     # Функция фиксирует передачу сообщения и делает соответствующие отметки в БД
    def process_message(self, sender, destination):
        # Получаем ID отправителя и получателя
        sender = self.session.query(self.AllUsers).filter_by(login=sender).first().id
        destination = self.session.query(self.AllUsers).filter_by(login=destination).first().id
        # Запрашиваем строки из истории и увеличиваем счётчики
        sender_row = self.session.query(self.MessageHistory).filter_by(user_id=sender).first()
        sender_row.cnt_sent += 1
        recipient_row = self.session.query(self.MessageHistory).filter_by(user_id=destination).first()
        recipient_row.cnt_receive += 1
        self.session.commit()

    # Функция добавляет контакт для пользователя.
    def add_contact(self, login, contact):
        # Получаем ID пользователей
        user = self.session.query(self.AllUsers).filter_by(login=login).first()
        contact = self.session.query(self.AllUsers).filter_by(login=contact).first()
        # Проверяем что не дубль и что контакт может существовать (полю пользователь мы доверяем)
        if not contact:
            return 0  # такого пользователя нет в системе

        if self.session.query(self.UsersContacts) \
                        .filter_by(user_id=user.id, contact=contact.id) \
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
        user = self.session.query(self.AllUsers).filter_by(login=login).first()
        contact = self.session.query(self.AllUsers).filter_by(login=contact).first()

        # Проверяем что контакт может существовать (полю пользователь мы доверяем)
        if not contact:
            return 0  # такого пользователя нет в системе

        if not self.session.query(self.UsersContacts) \
                        .filter_by(user_id=user.id, contact=contact.id) \
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
        user = self.session.query(self.AllUsers).filter_by(login=login).first()

        # Запрашиваем его список контактов
        query = self.session.query(self.UsersContacts, self.AllUsers.login) \
                            .filter_by(user_id=user.id) \
                            .join(self.AllUsers, self.UsersContacts.contact == self.AllUsers.id)

        # выбираем только имена пользователей и возвращаем их.
        return [contact[1] for contact in query.all()]


if __name__ == '__main__':
    path = os.path.dirname(os.path.abspath(__file__))
    db = ServerDB(os.path.join(path, 'server_db.bd3'))
    print(50*'=')
    print('login user test_1')
    db.user_login('test_1', '192.168.1.4', 8888)
    print('login user test_2')
    db.user_login('test_2', '192.168.1.5', 7777)
    db.user_login('test_3', '192.168.1.6', 7778)
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
    pprint(db.users_list())
    # выводим список активных пользователей
    print(50*'=')
    print('active users list:')
    pprint(db.active_users_list())

    print(50*'=')
    print('logout user test_2')
    db.user_logout('test_2')

    print(50*'=')
    print('all users list:')
    pprint(db.users_list())

    print(50*'=')
    print('active users list:')
    pprint(db.active_users_list())

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
    # db.process_message('McG2', '1111')
