import requests
import time

from blockchain.wallet import Wallet
from blockchain.blocks import Input, Output, Tx

while True:
    for port in [8001,8002,8000]:
        try:
            print(requests.get(f"http://127.0.0.1:{port}/chain/status").json()['block_hash'])
        except:
            pass
    print('===============================================================')
    time.sleep(2)