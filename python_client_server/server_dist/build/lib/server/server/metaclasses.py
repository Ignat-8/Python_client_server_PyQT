"""
В основе метода библиотека dis - анализ кода с помощью его дизассемблирования
(разбор кода на составляющие: в нашем случае - на атрибуты и методы класса)
https://docs.python.org/3/library/dis.html
"""

import dis
from pprint import pprint


class ServerMaker(type):
    """Метакласс для проверки соответствия сервера."""

    def __init__(cls, clsname, bases, clsdict):
        # clsname - экземпляр метакласса - Server
        # bases - кортеж базовых классов - ()
        # clsdict - словарь атрибутов и методов экземпляра метакласса
        # Список методов, которые используются в функциях класса:
        methods = []  # получаем с помощью 'LOAD_GLOBAL'
        # Обычно методы, обёрнутые декораторами попадают
        # не в 'LOAD_GLOBAL', а в 'LOAD_METHOD'
        methods_2 = []  # получаем с помощью 'LOAD_METHOD'
        # Атрибуты, используемые в функциях классов
        attrs = []  # получаем с помощью 'LOAD_ATTR'
        # перебираем ключи
        for func in clsdict:
            try:
                # Возвращает итератор по инструкциям в предоставленной
                # функции, методе, строке исходного кода или объекте
                # кода.
                ret = dis.get_instructions(clsdict[func])
                # Если не функция то ловим исключение
                # (если порт)
            except TypeError:
                pass
            else:
                # Раз функция разбираем код,
                # получая используемые методы и атрибуты.
                for i in ret:
                    # print(i)
                    # opname - имя для операции
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            # заполняем список методами,
                            # использующимися в функциях класса
                            methods.append(i.argval)
                    elif i.opname == 'LOAD_METHOD':
                        if i.argval not in methods_2:
                            # заполняем список атрибутами,
                            # использующимися в функциях класса
                            methods_2.append(i.argval)
                    elif i.opname == 'LOAD_ATTR':
                        if i.argval not in attrs:
                            # заполняем список атрибутами,
                            # использующимися в функциях класса
                            attrs.append(i.argval)
        # print(20*'-', 'methods', 20*'-')
        # pprint(methods)
        # print(20*'-', 'methods_2', 20*'-')
        # pprint(methods_2)
        # print(20*'-', 'attrs', 20*'-')
        # pprint(attrs)
        # print(50*'-')
        # pprint(type(attrs[2]))
        # print(50*'-')
        # Если обнаружено использование недопустимого метода connect,
        # вызываем исключение:
        if 'connect' in methods:
            raise TypeError('Использование метода connect \
                             недопустимо в серверном классе')
        # Если сокет не инициализировался константами
        # SOCK_STREAM(TCP) AF_INET(IPv4), тоже исключение.
        if not ('SOCK_STREAM' in attrs and 'AF_INET' in attrs):
            raise TypeError('Некорректная инициализация сокета.')
        # Обязательно вызываем конструктор предка:
        super().__init__(clsname, bases, clsdict)


# Метакласс для проверки корректности клиентов:
class ClientMaker(type):
    def __init__(cls, clsname, bases, clsdict):
        # Список методов, которые используются в функциях класса:
        methods = []
        for func in clsdict:
            # Пробуем
            try:
                ret = dis.get_instructions(clsdict[func])
                # Если не функция то ловим исключение
            except TypeError:
                pass
            else:
                # Раз функция разбираем код,
                # получая используемые методы.
                for i in ret:
                    if i.opname == 'LOAD_GLOBAL':
                        if i.argval not in methods:
                            methods.append(i.argval)
        pprint(methods)
        # Если обнаружено использование недопустимого метода
        # accept, listen, socket бросаем исключение:
        for command in ('accept', 'listen', 'socket'):
            if command in methods:
                raise TypeError('В классе обнаружено использование \
                                 запрещённого метода')
        # Вызов get_message или send_message из utils
        # считаем корректным использованием сокетов
        if 'get_message' in methods or 'send_message' in methods:
            pass
        else:
            raise TypeError('Отсутствуют вызовы функций, \
                             работающих с сокетами.')
        super().__init__(clsname, bases, clsdict)
