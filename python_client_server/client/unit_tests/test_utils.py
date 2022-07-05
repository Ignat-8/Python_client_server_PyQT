import unittest
import json
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), '..'))
from common.utils import get_message, send_message
from common.settings import ENCODING


class TestSocket:
    def __init__(self, test_dic):
        self.test_dic = test_dic
        self.encoded_message = None
        self.received_message = None

    def send(self, message_to_send):
        json_test_message = json.dumps(self.test_dic)
        self.encoded_message = json_test_message.encode(ENCODING)
        self.received_message = message_to_send

    def recv(self, max_len):
        json_test_message = json.dumps(self.test_dic)
        return json_test_message.encode(ENCODING)


class TestUtils(unittest.TestCase):
    test_dic_send = {
        'action': 'presence',
        'time': 111.111,
        'user':{
            'account_name': 'test_user',
        },
    }

    response_ok = {'response': 200}
    response_err = {'response': 400, 'error': 'bad request'}

    def test_send_message_true(self):
        test_socket = TestSocket(self.test_dic_send)
        send_message(test_socket, self.test_dic_send)
        self.assertEqual(test_socket.encoded_message, test_socket.received_message)

    def test_send_message_with_error(self):
        test_socket = TestSocket(self.test_dic_send)
        send_message(test_socket, self.test_dic_send)
        self.assertRaises(TypeError, send_message, test_socket, 'wrong_dict')

    def test_get_message_ok(self):
        test_socket_ok = TestSocket(self.response_ok)
        self.assertEqual(get_message(test_socket_ok), self.response_ok)

    def test_get_message_err(self):
        test_socket_err = TestSocket(self.response_err)
        self.assertEqual(get_message(test_socket_err), self.response_err)


if __name__ == '__main__':
    unittest.main()