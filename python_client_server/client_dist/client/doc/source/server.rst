Server module
==============

Серверное приложение для обмена сообщениями.
Содержит консольную часть и графическую часть.

В консольном режиме поддерживает следующие команды:

* **gui**       - графический интерфейс сервера
* **users**     - список известных пользователей
* **connected** - список подключённых пользователей
* **loghist**   - история входов пользователя
* **exit**      - завершение работы сервера
* **help**      - вывод справки по поддерживаемым командам 



server.core module
------------------

Основной класс **MyServer** создания серверного приложения.
Содержит класс **PortVerifi** проверки корректности введенного номера порта.
 
 
**MyServer.process_client_message**

Функция обработки сообщений от клиентов. Производит авторизацию приложения клиента,
регистрацию клиента по логину и паролю. Пароль клиента хранится в виде хеша в БД.
Производит отправку сообщений между пользователями и сохранение переписки.



.. automodule:: server.core
   :members:
   :undoc-members:
   :show-inheritance:



server.server\_db module
------------------------

.. automodule:: server.server_db
   :members:
   :undoc-members:
   :show-inheritance:

server.server\_gui module
-------------------------

.. automodule:: server.server_gui
   :members:
   :undoc-members:
   :show-inheritance:


server.metaclasses module
-------------------------

.. automodule:: server.metaclasses
   :members:
   :undoc-members:
   :show-inheritance:


Module contents
---------------

.. automodule:: server
   :members:
   :undoc-members:
   :show-inheritance:
