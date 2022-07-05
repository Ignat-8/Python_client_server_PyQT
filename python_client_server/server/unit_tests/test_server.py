import os
import sys
import unittest
sys.path.insert(0, os.path.join(os.getcwd(), '..'))
from server import process_client_message


class TestProcessClientMessage(unittest.TestCase):
    message = {
            'action': 'presence',
            'time': 111.11,
            'user': {
                'account_name': 'Guest',
            },
        }

    def test_equal(self):
        self.assertEqual(process_client_message(self.message),
                         {'response': 200})
        message_err = self.message
        message_err['action'] = ''  # error message
        self.assertEqual(process_client_message(message_err),
                         {'response': 400,
                          'error': 'bad request'})

    def test_isinstance(self):
        self.assertIsInstance(
            process_client_message(self.message), dict)
        self.assertIsInstance(
            process_client_message(self.message)['response'], int)
        message_err = self.message
        message_err['action'] = ''  # error message
        self.assertIsInstance(
            process_client_message(message_err), dict)
        self.assertIsInstance(
            process_client_message(message_err)['response'], int)
        self.assertIsInstance(
            process_client_message(message_err)['error'], str)


if __name__ == '__main__':
    unittest.main()
