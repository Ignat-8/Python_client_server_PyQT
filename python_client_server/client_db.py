from sqlalchemy import create_engine, Column, Integer, \
    String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime, os
from pprint import pprint

class ClientDB:
    Base = declarative_base()
    
    class Contacts(Base):
        __tablename__ = 'contacts'
        id = Column(Integer, primary_key=True)
        login = Column(String, unique=True)

        def __init__(self, login):
            self.login = login

    class MessageIn(Base):
        __tablename__ = 'message_in'
        id = Column(Integer, primary_key=True)
        contact_id = Column(Integer, ForeignKey('contacts.id'))
        message = Column(Text)
        date = Column(DateTime)

        def __init__(self, contact_id, message):
            self.contact_id = contact_id
            self.message = message
            self.date = datetime.datetime.now()

    class MessageOut(Base):
        __tablename__ = 'message_out'
        id = Column(Integer, primary_key=True)
        contact_id = Column(Integer, ForeignKey('contacts.id'))
        message = Column(Text)
        date = Column(DateTime)

        def __init__(self, contact_id, message):
            self.contact_id = contact_id
            self.message = message
            self.date = datetime.datetime.now()

    def __init__(self, path):
        # Создаём движок базы данных
        self.engine = create_engine(f'sqlite:///{path}', 
                                    echo=False, 
                                    pool_recycle=7200,
                                    connect_args={'check_same_thread': False})

        self.Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    # Функция добавления контактов
    def add_contact(self, login):
        if not self.session.query(self.Contacts) \
                            .filter_by(login=login) \
                            .count():
            contact_row = self.Contacts(login)
            self.session.add(contact_row)
            self.session.commit()
    
    # Функция удаления контакта
    def del_contact(self, login):
        self.session.query(self.Contacts) \
                    .filter_by(login=login) \
                    .delete()
        self.session.commit()

    # Функция проверяет наличие пользователя в таблице Контактов
    def check_contact(self, login):
        if self.session.query(self.Contacts) \
                        .filter_by(login=login) \
                        .count():
            return True
        else:
            return False

    # Функция сохраняет Incomming сообщения
    def save_message_in(self, login, message):
        contact = self.session.query(self.Contacts) \
                            .filter_by(login=login) 

        # Если имя пользователя есть в списке контактов
        if contact.count():
            contact = contact.first()
            message_row = self.MessageIn(contact.id, message)
            self.session.add(message_row)
            self.session.commit()
        else:
            print('Incomming message from unknown user')

    # Функция сохраняет Outcomming сообщения
    def save_message_out(self, login, message):
        contact = self.session.query(self.Contacts) \
                            .filter_by(login=login) 

        # Если имя пользователя есть в списке контактов
        if contact.count():
            contact = contact.first()
            message_row = self.MessageOut(contact.id, message)
            self.session.add(message_row)
            self.session.commit()
        else:
            print('Outcomming message to unknown user')

    # Функция возвращает историю переписки
    def get_history(self, login=None):
        history = [('type_message', 'login', 'message', 'date')]
        query_in = self.session.query(self.Contacts.id,
                                        self.Contacts.login, 
                                        self.MessageIn.message,
                                        self.MessageIn.date) \
                                .join(self.Contacts)
        query_out = self.session.query(self.Contacts.id,
                                        self.Contacts.login, 
                                        self.MessageOut.message,
                                        self.MessageOut.date) \
                                .join(self.Contacts)

        if login:
            contact = self.session.query(self.Contacts) \
                                .filter_by(login=login) 
            # Если имя пользователя есть в списке контактов
            if contact.count():
                contact = contact.first()
                query_in = query_in.filter_by(id=contact.id)
                query_out = query_out.filter_by(id=contact.id)
            else:
                print("Такого пользователя нет в списке контактов")
                return history

        [history.append(('in', row.login, row.message, row.date))
                        for row in query_in.all()]
        [history.append(('out', row.login, row.message, row.date))
                        for row in query_out.all()]
        return history
        

if __name__ == '__main__':
    path = os.path.dirname(os.path.abspath(__file__))
    login = 'test_1'
    db = ClientDB(os.path.join(path, f'client_db_{login}.bd3'))
    print(50*'=')
    print('Add contacts')
    for i in ['test1', 'test2', 'test3']:
        db.add_contact(i)
    
    print(50*'=')
    print('Delete contact')
    db.del_contact('test5')

    print(50*'=')
    print('Save incomming message')
    db.save_message_in('test1', 'Incomming message from user test1')
    db.save_message_in('test2', 'Incomming message from user test2')

    print(50*'=')
    print('Save Outcomming message')
    db.save_message_out('test1', 'Outcomming message to user test1')
    db.save_message_out('test3', 'Outcomming message to user test3')

    print(50*'=')
    print('History all messages')
    pprint(db.get_history(), compact=True)

    print(50*'=')
    print('History messages with user "test1"')
    pprint(db.get_history('test1'), compact=True)

    print(50*'=')
    print('History messages with user "test2"')
    pprint(db.get_history('test2'), compact=True)

    print(50*'=')
    print('History messages with user "test3"')
    pprint(db.get_history('test3'), compact=True)
