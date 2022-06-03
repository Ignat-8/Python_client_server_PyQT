""" 
2. Написать функцию host_range_ping() (возможности которой основаны на функции из примера 1) 
для перебора ip-адресов из заданного диапазона. Меняться должен только последний октет каждого адреса. 
По результатам проверки должно выводиться соответствующее сообщение.
""" 
from pprint import pprint
from ipaddress import ip_address
from lesson01_1 import host_ping

def host_range_ping():
    while True:
        start_ip = input("Введите первоначальный адрес: ")
        try:
            ipv4_start = ip_address(start_ip)
            last_oct = int(start_ip.split('.')[3])
            break
        except Exception as e:
            print(f'Ошибка:{e}\nвведен не корректный ip адрес')

    while True:
        end_ip = input("Сколько адресов проверить?: ")
        if not end_ip.isnumeric():
            print("Необходимо ввести число")
        else:
            if (last_oct + int(end_ip)) > 256:
                print(f"Можем менять только последний октет, "
                      f"т.е. максимальное число хостов {256 - last_oct}")
            else:
                break

    # формируем список ip
    host_list = []
    [host_list.append(str(ipv4_start + x)) for x in range(int(end_ip))]
    print('Проверяемый список адресов:')
    pprint(host_list)

    print('\nПроверка доступности адресов:')
    return host_ping(host_list)


if __name__ == "__main__":
    host_range_ping()
