import os
import sys
import unittest
sys.path.insert(0, os.path.join(os.getcwd(), '..'))
from client import create_presence, process_ans


class TestCreatePresence(unittest.TestCase):
    def test_equal(self):
        self.assertEqual(create_presence()['action'], 'presence')
        self.assertEqual(create_presence()['user']['account_name'], 'Guest')
        self.assertEqual(create_presence('User1')['user']['account_name'], 'User1')

    def test_not_equal(self):
        self.assertNotEqual(create_presence('User1')['user']['account_name'], 'Guest')

    def test_isinstance(self):
        self.assertIsInstance(create_presence(), dict)
        self.assertIsInstance(create_presence()['action'], str)
        self.assertIsInstance(create_presence()['time'], float)
        self.assertIsInstance(create_presence()['user'], dict)
        self.assertIsInstance(create_presence()['user']['account_name'], str)



class TestProcessAns(unittest.TestCase):
    def test_isinstance(self):
        message = {'response': 200}
        self.assertIsInstance(process_ans(message), dict)

    def test_equal(self):
        message_ok = {'response': 200}
        message_er = {'response': 201, 'error': 'bad request'}
        self.assertEqual(process_ans(message_ok), {'200': 'ok'})
        self.assertEqual(process_ans(message_er), '400: bad request')

    def test_not_equal(self):
        message_ok = {'response': 200}
        message_er = {'response': 201, 'error': 'bad request'}
        self.assertNotEqual(process_ans(message_ok), {'200': ''})
        self.assertNotEqual(process_ans(message_er), 'bad request')

    def test_raises(self):
        message_ok = {'rsponse': 200}
        self.assertRaises(ValueError, process_ans, message_ok)


if __name__ == '__main__':
    unittest.main()
