import logging

SA_ENGINE_URI = 'sqlite:////tmp/test.db'
PRIV_KEY = "L4vB5fomsK8L95wQ7GFzvErYGht49JsCPJyJMHpB4xGM6xgi2jvG"
PUB_KEY = "1F26pNMrywyZJdr22jErtKcjF8R3Ttt55G"
BASEPATH = ""
LOGFILE = "/tmp/server.log"
LOGLEVEL = logging.DEBUG

BITCOIN_RPC_URL = "http://%s:%s@127.0.0.1:8332"%('bitcoinrpc', '')
DASH_RPC_URL = "http://%s:%s@127.0.0.1:8332"%('dashrpc', '')
