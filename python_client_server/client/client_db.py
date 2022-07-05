import os
import datetime
from sqlalchemy import create_engine, Column, Integer, \
    String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pprint import pprint


class ClientDB:
    Base = declarative_base()

    class Users(Base):
        __tablename__ = 'users'
        id = Column(Integer, primary_key=True)
        login = Column(String, unique=True, nullable=False)
        is_contact = Column(Integer, default=0)

        def __init__(self, login):
            self.login = login

    class Messages(Base):
        __tablename__ = 'messages'
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey('users.id'))
        message = Column(Text)
        message_type = Column(Text)  # (in, out)
        date = Column(DateTime, default=datetime.datetime.now())

        def __init__(self, user_id, message, message_type):
            self.user_id = user_id
            self.message = message
            self.message_type = message_type
            # self.date = datetime.datetime.now()

    def __init__(self, user_name):
        # Создаём движок базы данных
        path = os.path.dirname(os.path.realpath(__file__))
        filename = f'client_{user_name}.db3'
        self.engine = create_engine(
            f'sqlite:///{os.path.join(path, filename)}',
            echo=False,
            pool_recycle=7200,
            connect_args={'check_same_thread': False})

        self.Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    # Функция добавления пользователя
    def add_users(self, user_list):
        print(50*'=' + ' client_db.add_users')
        print('user_list:', user_list)
        self.session.query(self.Users).delete()
        for user in user_list:
            user_row = self.Users(user)
            self.session.add(user_row)
        self.session.commit()

    # Функция добавления контактов
    def add_contact(self, login):
        self.session.query(self.Users) \
                    .filter_by(login=login) \
                    .first() \
                    .is_contact = 1
        self.session.commit()

    # Функция удаления контакта
    def del_contact(self, login):
        self.session.query(self.Users) \
                    .filter_by(login=login) \
                    .first() \
                    .is_contact = 0
        self.session.commit()

    # Функция проверяет наличие пользователя в таблице Контактов
    def check_contact(self, login):
        print('check_contact for ligin:', login)
        if self.session.query(self.Users) \
                       .filter_by(login=login, is_contact=1) \
                       .count():
            print('return True')
            return True
        else:
            print('return False')
            return False

    # Функция, возвращающая контакты
    def get_contacts(self):
        return [contact[0] for contact in
                self.session.query(self.Users.login)
                            .filter_by(is_contact=1)
                            .all()]

    # Функция, возвращающая список известных пользователей
    def get_users(self):
        return [user[0] for user in
                self.session.query(self.Users.login).all()]

    # Функция сохраняет сообщение
    def save_message(self, login, message_text, message_type):
        contact = self.session.query(self.Users) \
                              .filter_by(login=login, is_contact=1)

        # Если имя пользователя есть в списке контактов
        if contact.count() and message_type in ('in', 'out'):
            contact = contact.first()
            message_row = self.Messages(contact.id,
                                        message_text,
                                        message_type)
            self.session.add(message_row)
            self.session.commit()
        else:
            print(f'client_db.save_message: login="{login}", \
                    text="{message_text}", \
                    message_type="{message_type}"')

    # Функция возвращает историю переписки
    def get_history(self, login=None):
        # history = [('message_type', 'login', 'message', 'date')]
        history = []
        query = self.session.query(self.Users.id,
                                   self.Users.login,
                                   self.Messages.message,
                                   self.Messages.message_type,
                                   self.Messages.date) \
                            .join(self.Users)

        if login:
            contact = self.session.query(self.Users) \
                                  .filter_by(login=login, is_contact=1)
            # Если имя пользователя есть в списке контактов
            if contact.count():
                contact = contact.first()
                query = query.filter_by(id=contact.id)
            else:
                print("Такого пользователя нет в списке контактов")
                return history

        [history.append((row.message_type,
                         row.login,
                         row.message,
                         row.date))
         for row in query.all()]

        return history

    # Функция обновления переписки c пользователем
    # список берем с сервера
    def update_messages(self, messages):
        print('!!!!! update_messages =', messages)
        # удаляем текущие сообщения с этим пользователем
        self.session.query(self.Messages) \
                    .delete()
        # записываем сообщения из списка
        for el in messages:
            message_type = el[0]
            user_id = el[1]
            text = el[2]
            date = datetime.datetime.fromisoformat(el[3])

            mess_row = self.Messages(user_id, text, message_type)
            mess_row.date = date
            self.session.add(mess_row)
        # сохраняем изменения в БД
        self.session.commit()


if __name__ == '__main__':
    path = os.path.dirname(os.path.abspath(__file__))
    login = 'test_1'
    db = ClientDB(login)

    # print(50*'=')
    # print('Add users')
    # user_list = ['test_1', 'test_2', 'test_3']
    # db.add_users(user_list)

    # print(50*'=')
    # print('Add contact')
    # db.add_contact('test_1')
    # db.add_contact('test_2')

    # print(50*'=')
    # print('Delete contact')
    # db.del_contact('test_1')

    print(50*'=')
    print('Save incomming message')
    db.save_message('test_2', 'Incomming message from user test_2', 'in')
    db.save_message('test_3', 'Incomming message from user test_3', 'in')

    print(50*'=')
    print('Save Outcomming message')
    db.save_message('test_2', 'Outcomming message to user test_2', 'out')
    db.save_message('test_3', 'Outcomming message to user test_3', 'out')

    print(50*'=')
    print('History all messages')
    pprint(db.get_history(), compact=True)

    print(50*'=')
    print('History messages with user "test_1"')
    pprint(db.get_history('test_1'), compact=True)

    print(50*'=')
    print('History messages with user "test_2"')
    pprint(db.get_history('test_2'), compact=True)

    print(50*'=')
    print('History messages with user "test_3"')
    pprint(db.get_history('test_3'), compact=True)

    print(50*'=')
    print('Update messages with user test_2 from server')
    messages = [('in', 'test_2', 'some message from test_2 user',
                 datetime.datetime.now()),
                ('in', 'test_2', 'some message from test_2 user',
                 datetime.datetime.now()),
                ('out', 'test_2', 'some message to test_2 user',
                 datetime.datetime.now())]
    db.update_messages(messages)
    pprint(db.get_history('test_2'), compact=True)
