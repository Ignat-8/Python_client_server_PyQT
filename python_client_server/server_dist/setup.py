from setuptools import setup, find_packages

setup(name="ib_message_server",
      version="0.0.8",
      description="Server part of Server to client messanger",
      author="Igor Burakov",
      author_email="iburako8@yandex.ru",
      packages=find_packages(),
      url='https://pypi.org/project/ib-message-server/',
      install_requires=['PyQt5',
                        'sqlalchemy',
                        'pycryptodome',
                        'pycryptodomex'],
      scripts=['server/server_run']
      )
