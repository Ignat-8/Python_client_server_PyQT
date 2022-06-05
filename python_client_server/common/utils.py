import json
from  common.settings import MAX_PACKAGE_LENGTH, ENCODING
from common.decors import log
import common.errors as my_err


@log
def get_message(client):
    # print(f'function get_message, client = {client}')
    encoded_response = client.recv(MAX_PACKAGE_LENGTH)
    # print(f'получено сообщение encoded_response = {encoded_response}')
    if isinstance(encoded_response, bytes):
        json_response = encoded_response.decode(ENCODING)
        # print(f'Декодированное сообщение {json_response}')
        if isinstance(json_response, str):
            response = json.loads(json_response)
            if isinstance(response, dict):
                return response
            raise my_err.NonDictError
        raise my_err.NonStrError
    raise my_err.NonBytesError


@log
def send_message(sock, message):
    if not isinstance(message, dict):
        raise my_err.NonDictError
    js_message = json.dumps(message)
    encoded_message = js_message.encode(ENCODING)
    sock.send(encoded_message)
    return True
