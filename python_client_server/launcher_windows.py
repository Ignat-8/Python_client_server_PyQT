"""
Служебный скрипт запуска/останова нескольких клиентских приложений
"""
import os
from subprocess import Popen, CREATE_NEW_CONSOLE


PROCESS_LIST = []

while True:
    ACTION = input("Запустить клиентов (s) / Закрыть клиентов (x) / Выйти (q) ")

    if ACTION == 'q':
        break
    elif ACTION == 's':
        PROCESS_LIST.append(
            Popen('python server.py', 
                    creationflags=CREATE_NEW_CONSOLE)
            )

        print(os.getcwd())
        os.chdir('client')
        for _ in range(3):
            PROCESS_LIST.append(Popen(f'python client.py -n user_{_+1}', creationflags=CREATE_NEW_CONSOLE))
        
    elif ACTION == 'x':
        for p in PROCESS_LIST:
            p.kill()
        PROCESS_LIST.clear()
        