Client module
==============

Клиентское приложение для обмена сообщениями. Поддерживает
отправку сообщений пользователям которые находятся в сети.

Поддерживает аргументы коммандной строки:

``python client.py {адрес сервера} {порт} -n или --name {имя пользователя} -p или -password {пароль}``

1. {имя сервера} - адрес сервера сообщений, не обязательный аргумент, по умолчанию 127.0.0.1
2. {порт} - порт для подключения, не обязательное поле, по умолчанию 7777
3. -n или --name - имя пользователя, обязательное поле
4. -p или --password - пароль пользователя, обязательное поле


Примеры использования:

*Запуск приложения с пользователем test1 и паролем 123, адрес сервера и порт по умолчанию:*

* ``python -n test1 -p 123``


*Запуск приложения с пользователем test1 и паролем 123 и указанием подключаться к серверу по адресу ip_address:port*

* ``python client.py ip_address port -n test1 -p 123``


client.py
~~~~~~~~~

Запускаемый модуль,содержит парсер аргументов командной строки и функционал инициализации приложения.

client. **arg_parser** ()
    Парсер аргументов командной строки, возвращает кортеж из 4 элементов:
    
	* адрес сервера
	* порт
	* имя пользователя
	* пароль
	
    Выполняет проверку на корректность номера порта и не пустых аргументов имени пользователя и пароля.
    При запуске создает клиентское приложение, создает подключение к базе данных и сокет для подключения к серверу.


Submodules
----------

client.client\_db module
------------------------

.. automodule:: client.client_db
   :members:
   :undoc-members:
   :show-inheritance:

client.client\_socket module
----------------------------

.. automodule:: client.client_socket
   :members:
   :undoc-members:
   :show-inheritance:


client.win\_main module
-----------------------

.. automodule:: client.win_main
   :members:
   :undoc-members:
   :show-inheritance:



client.win\_main\_code module
-----------------------------

.. automodule:: client.win_main_code
   :members:
   :undoc-members:
   :show-inheritance:



client.win\_contact\_add module
-------------------------------

.. automodule:: client.win_contact_add
   :members:
   :undoc-members:
   :show-inheritance:

client.win\_contact\_del module
-------------------------------

.. automodule:: client.win_contact_del
   :members:
   :undoc-members:
   :show-inheritance:



Module contents
---------------

.. automodule:: client
   :members:
   :undoc-members:
   :show-inheritance:

Subpackages
-----------

.. toctree::
   :maxdepth: 4

   client.logs
