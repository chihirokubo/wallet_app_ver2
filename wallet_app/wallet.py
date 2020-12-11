import base58
import codecs
import hashlib
import random
import logging
import sys
import time
import json

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

#from ecdsa import NIST256p
#from ecdsa import SigningKey

from crypt import PrivateKey
from crypt import Signature
from crypt import S256Point
from crypt import P
import utils


class Wallet(object):
    """ 変更点などのメモ
    generate_blockchainaddress()は削除
        公開鍵生成の過程でアドレスも生成するため
    アドレス長が従来と異なる
        もともと65文字で変更後は34文字
        一般的にアドレスは27〜35文字に収まるのでOK
    """
    def __init__(self):
        self._private_key = PrivateKey(secret=random.randint(1, P-1))
        self._public_key = self._private_key.point
        self._blockchain_address = self._public_key.address()

    @property
    def private_key(self):
        return self._private_key.hex()

    @property
    def public_key(self):
        x = self._public_key.x
        y = self._public_key.y
        return str(x) + str(y)

    @property
    def blockchain_address(self):
        return self._blockchain_address

    def log_in(self, public_key, private_key):
        self._public_key = public_key
        self._private_key = private_key
        self._blockchain_address = self._private_key.address()


class Transaction(object):

    def __init__(self, sender_private_key, sender_public_key,
                 sender_blockchain_address, recipient_blockchain_address,
                 value):
        self.sender_private_key = sender_private_key
        self.sender_public_key = sender_public_key
        self.sender_blockchain_address = sender_blockchain_address
        self.recipient_blockchain_address = recipient_blockchain_address
        self.value = value
        self.timestamp = time.time()
        self.signature = self.generate_signature()

    def get_json_msg(self):
        msg = {
            'sender_private_key' : self.sender_private_key,
            'sender_public_key': self.sender_public_key,
            'sender_blockchain_address': self.sender_blockchain_address,
            'recipient_blockchain_address': self.recipient_blockchain_address,
            'value': float(self.value),
            'timestamp': self.timestamp,
            'signature': self.signature
        }
        return json.dupms(msg)

    def generate_signature(self):
        """ 送金者の秘密鍵でトランザクションに署名
        トランザクションをsha256でハッシュ化
        PrivateKey.sign(message_hash)でSignatureオブジェクトを作成
        署名結果のrとsをタプルで返す
        """
        sha256 = hashlib.sha256()
        transaction = utils.sorted_dict_by_key({
            'sender_blockchain_address': self.sender_blockchain_address,
            'recipient_blockchain_address': self.recipient_blockchain_address,
            'value': float(self.value),
            'timestamp': self.timestamp
        })
        sha256.update(str(transaction).encode('utf-8'))
        message = sha256.digest()
        msg_hex = message.hex()
        msg_hex_str = str(msg_hex)
        msg_hex_str_0x = '0x' + msg_hex_str
        priv_int = int('0x'+self.sender_private_key, 0)
        priv = PrivateKey(priv_int)
        sig = priv.sign(int(msg_hex_str_0x, 0))
        return (sig.r, sig.s)

if __name__ == '__main__':
    # ウォレットA→Bへの送金テスト 
    # デバッグの結果は，blockchain.pyのadd_transaction()内で
    # 保有量 < 送金量 でエラー検知する部分をコメントアウトすれば正しく動く
    
    wallet_A = Wallet()
    wallet_B = Wallet()
    wallet_M = Wallet()

    # トランザクションの生成
    t = Transaction(
        wallet_A.private_key,
        wallet_A.public_key,
        wallet_A.blockchain_address,
        wallet_B.blockchain_address,
        1.0
    )

    import blockchain
    block_chain = blockchain.BlockChain(
        blockchain_address=wallet_M.blockchain_address)

    is_added = block_chain.add_transaction(
        wallet_A.blockchain_address,
        wallet_B.blockchain_address,
        1.0,
        wallet_A.public_key,
        t.generate_signature())

    print('Added?', is_added)
    block_chain.mining()
    utils.pprint(block_chain.chain)

    print('A', block_chain.calculate_total_amount(wallet_A.blockchain_address))
    print('B', block_chain.calculate_total_amount(wallet_B.blockchain_address))


    



    



    
