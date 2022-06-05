
import unittest
import json
import sys
import os
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR

sys.path.insert(0, os.path.join(os.getcwd(), '..'))
from common.utils import get_message, send_message
from common.settings import ENCODING, MAX_CONNECTIONS, \
                            DEFAULT_ADDRESS, DEFAULT_PORT, \
                            MAX_PACKAGE_LENGTH


class TestUtils(unittest.TestCase):
    test_message = {
        'action': 'presence',
        'time': 11.11,
        'user': {
            'account_name': 'Guest',
        },
    }

    response_ok = {'response': 200, 
                    'alert': 'соединение успешно'}
    response_err = {'response': 400,
                    'error': 'ошибка соединения'}
    
    server_socket = None
    client_socket = None

    def setUp(self) -> None:
        # создаем тестовый сокет для сервера
        self.server_socket = socket(AF_INET, SOCK_STREAM)
        self.server_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.server_socket.bind((DEFAULT_ADDRESS, DEFAULT_PORT))
        self.server_socket.listen(MAX_CONNECTIONS)
        # создаем тестовый сокет для клиента
        self.client_socket = socket(AF_INET, SOCK_STREAM)
        self.client_socket.connect((DEFAULT_ADDRESS, DEFAULT_PORT))
        self.client, self.client_address = self.server_socket.accept()

    def tearDown(self) -> None:
        self.client.close()
        self.client_socket.close()
        self.server_socket.close()

    def test_send_wrong_message_from_client(self):
        self.assertRaises(TypeError, send_message, self.client_socket, 'not dict')

    def test_send_message_client_server(self):
        send_message(self.client_socket, self.test_message)
        test_response = self.client.recv(MAX_PACKAGE_LENGTH)
        test_response = json.loads(test_response.decode(ENCODING))
        self.client.close()
        self.assertEqual(self.test_message, test_response)

    def test_get_message_200(self):
        message = json.dumps(self.response_ok)
        self.client.send(message.encode(ENCODING))
        self.client.close()

        response = get_message(self.client_socket)
        self.assertEqual(self.response_ok, response)

    def test_get_message_400(self):
        message = json.dumps(self.response_err)
        self.client.send(message.encode(ENCODING))
        self.client.close()

        response = get_message(self.client_socket)
        self.assertEqual(self.response_err, response)


if __name__ == '__main__':
    unittest.main()
