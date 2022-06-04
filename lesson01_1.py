"""
1. Написать функцию host_ping(), в которой с помощью утилиты ping
будет проверяться доступность сетевых узлов.
Аргументом функции является список, в котором каждый сетевой узел
должен быть представлен именем хоста или ip-адресом.
В функции необходимо перебирать ip-адреса и проверять
их доступность с выводом соответствующего сообщения
(«Узел доступен», «Узел недоступен»). При этом ip-адрес
сетевого узла должен создаваться с помощью функции ip_address().
"""

import platform
import subprocess
import time
from threading import Thread
from ipaddress import ip_address
import socket

result = {'Доступные узлы': '', 'Недоступные узлы': ''}


def ping(host, ipv4, result):
    """
    Проверка доступности хостов
    :param host: имя проверяемого хоста
    :param ipv4: ip адрес проверяемого хоста
    :param ip_check: результат проверки на корректность ip адреса
    """
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    response = subprocess.Popen(["ping", param, '10', '-w', '1', str(ipv4)],
                                stdout=subprocess.PIPE)
    if response.wait() == 0:
        if str(host) != str(ipv4):
            print(f"{host}({ipv4}) - узел доступен")
            result['Доступные узлы'] += f"{host}({ipv4})\n"
        else:
            print(f"{host} - узел доступен")
            result['Доступные узлы'] += f"{host}\n"
    else:
        if str(host) != str(ipv4):
            print(f"{host}({ipv4}) - узел не доступен")
            result['Недоступные узлы'] += f"{host}({ipv4})\n"
        else:
            print(f"{host} - узел не доступен")
            result['Недоступные узлы'] += f"{host}\n"


def host_ping(hosts_list):
    """
    Проверка доступности хостов
    :param hosts_list: список хостов
    """
    threads = []
    for host in hosts_list:  
        try:  # проверяем, является ли значение ip-адресом
            ipv4 = socket.gethostbyname(host)
            ipv4 = ip_address(ipv4)
        except ValueError:
            print(f'{host} - не корректный ip адрес или имя хоста')
            continue
        else:
            # print(f'{host} - корректный ip адрес')

            thread = Thread(target=ping, args=(host, ipv4, result), daemon=True)
            threads.append(thread)
            thread.start()
            print('start thread')
            
    print('join threads')
    for thread in threads:
        thread.join()
    return result


if __name__ == '__main__':
    # список проверяемых хостов
    hosts_list = ['192.168.8.1', '8.8.8.8', 'yandex.ru', 'google.com',
                  '0.0.0.1', '0.0.0.2', '0.0.0.3', '0.0.0.4', '0.0.0.5',
                  '0.0.0.6', '0.0.0.7', '0.0.0.8', '0.0.0.9', '0.0.1.0']
    start = time.time()
    print(host_ping(hosts_list))
    end = time.time()
    print(f'total time: {int(end - start)}')
