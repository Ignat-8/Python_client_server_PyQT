from setuptools import setup, find_packages

setup(name="ib_message_client",
      version="0.0.3",
      description="Client part of Server to client messanger",
      author="Igor Burakov",
      author_email="iburako8@yandex.ru",
      packages=find_packages(),
      url='https://pypi.org/project/ib-message-client/',
      install_requires=['PyQt5', 'sqlalchemy', 'pycryptodome', 'pycryptodomex'],
      scripts=['client/client_run']
      )
