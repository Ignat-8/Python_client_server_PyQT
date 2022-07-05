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
        os.chdir('server')
        PROCESS_LIST.append(
            Popen('python core.py', 
                    creationflags=CREATE_NEW_CONSOLE)
            )

        os.chdir('../client')
        for _ in range(3):
            PROCESS_LIST.append(Popen(f'python client.py -n user_{_+1} -p 11111{_+1}'
                                        , creationflags=CREATE_NEW_CONSOLE))
        
    elif ACTION == 'x':
        for p in PROCESS_LIST:
            p.kill()
        PROCESS_LIST.clear()
        