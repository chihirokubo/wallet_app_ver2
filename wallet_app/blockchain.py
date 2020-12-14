import contextlib
import hashlib
import json
import logging
import sys
import random
import time
import threading
import copy

# Deleted by 暗号班
# 楕円曲線暗号と署名検証はスクラッチ実装したので不必要
# from ecdsa import NIST256p
# from ecdsa import VerifyingKey
import requests

import utils
# Added By 暗号班
# 公開鍵生成に使用
from crypt import S256Point
from crypt import G
from crypt import N

MINING_SENDER = 'THE BLOCKCHAIN'
MINING_TIMER_SEC = 50
MINING_REWARD = 1.0

# マイニング系はcore/server_coreに移動

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


class BlockChain(object):

    def __init__(self, blockchain_address=None):
        self.transaction_pool = []
        self.chain = []
        self.neighbours = []
        self.previous_hash = self.hash({})
        self.difficulty = 3     # Added By コンセンサス
        self.mining_speed = 0.0 # Added By コンセンサス
        self.create_block(0, self.previous_hash)
        self.blockchain_address = blockchain_address

    # 共通
    def create_block(self, nonce, previous_hash):
        """
        ブロック生成
        returns:
            is_created: ブロックが正常に追加
            block: 追加されたブロック
        """
        block = utils.sorted_dict_by_key({
            'transactions': json.dumps(self.transaction_pool),
            'nonce': nonce,
            'previous_hash': previous_hash,
            'difficulty': self.difficulty
        })
        self.previous_hash = self.hash(block)
        self.chain.append(block)
        return block

    # 共通
    def hash(self, block):
        sorted_block = json.dumps(block, sort_keys=True)
        return hashlib.sha256(sorted_block.encode()).hexdigest()

    # 共通
    def add_transaction(self, sender_blockchain_address,
                        recipient_blockchain_address, value, timestamp,
                        sender_public_key=None, signature=None):

        print('add_transaction is called')
        transaction = utils.sorted_dict_by_key({
            'sender_blockchain_address': sender_blockchain_address,
            'recipient_blockchain_address': recipient_blockchain_address,
            'value': float(value),
            'timestamp': timestamp
        })

        if sender_blockchain_address == MINING_SENDER:
            self.transaction_pool.append(transaction)
            return True

        if self.verify_transaction_signature(
            sender_public_key, signature, transaction):

            if (self.calculate_total_amount(sender_blockchain_address)
                    < float(value)):
                logger.error(
                        {'action': 'add_transaction', 'error': 'no_value'})
                return False

            self.transaction_pool.append(transaction)
            logger.info({'action':'add_transaction', 'status': 'success'})
            return True
        print('yea not verified')
        return False

    # Changed By 暗号班
    def verify_transaction_signature(
            self, sender_public_key, signature, transaction):
        """ 署名の検証のスクラッチ化
        esdsaの内部で行なっていた計算をここで行っているイメージ
        返り値はbool型
        """
        print('verifying transaction signature is called')
        sha256 = hashlib.sha256()
        sha256.update(str(transaction).encode('utf-8'))
        message = sha256.digest()
        msg_hex = message.hex()
        msg_hex_str = str(msg_hex)
        msg_hex_str_0x = '0x' + msg_hex_str
        z = int(msg_hex_str_0x, 0)
        s_inv = pow(signature[1], N - 2, N)
        # u = z / s
        # v = r / s
        u = (z * s_inv) % N
        v = (signature[0] * s_inv) % N

        # 文字列から公開鍵を再構築
        x = '0x' + sender_public_key[:64]
        y = '0x' + sender_public_key[64:]
        x = int(x, 0)
        y = int(y, 0)
        P = S256Point(x, y)
        total = u * G + v * P
        return total.x.num == signature[0]

    # Added By コンセンサス
    # 採掘難易度の調整
    def difficulty_adjustment(self, speed):
        if self.difficulty < 3:
            self.difficulty = 3
            return True
        else:
            if speed < 0.0478:
                self.difficulty += 1
                self.mining_speed = speed + random.uniform(5.0, 5.3)
            elif 0.0478 <= speed and speed <= 0.5957:
                self.difficulty = 3
                self.mining_speed = speed + 5.0
            elif speed > 0.5957:
                self.difficulty -= 1
                self.mining_speed = speed + random.uniform(4.4, 4.7)
                if self.mining_speed >= 5.5:
                    self.mining_speed -= random.uniform(0.5, 1.0)
            logger.info({'action': 'changing difficulty', 'status': 'success'})
            return True
        
    # Changed By コンセンサス
    def valid_proof(self, transactions, previous_hash, nonce, difficulty):
        guess_block = utils.sorted_dict_by_key({
            'transactions': json.dumps(transactions),
            'nonce': nonce,
            'previous_hash': previous_hash,
            'difficulty': difficulty
        })
        guess_hash = self.hash(guess_block)
        result = guess_hash[:difficulty] == '0'*difficulty
        return result

    # Changed By コンセンサス
    def proof_of_work(self):
        transactions = self.transaction_pool.copy()
        print('transaction pool : ',transactions)
        previous_hash = self.previous_hash
        nonce = 0
        start = time.time()
        while self.valid_proof(transactions, previous_hash, nonce, self.difficulty) is False:
            nonce += 1
            elapse = time.time() - start
            if elapse >= 10.0:
                self.difficulty -= 1
                return -1
        
        return nonce

    # マイニングはcore/Server_core.pyに移動

    # 共通
    def calculate_total_amount(self, blockchain_address):
        total_amount = 0.0
        for block in self.chain:
            for transaction in json.loads(block['transactions']):
                value = float(transaction['value'])
                if blockchain_address == transaction['recipient_blockchain_address']:
                    total_amount += value
                if blockchain_address == transaction['sender_blockchain_address']:
                    total_amount -= value
        return total_amount

    # Chaged By コンセンサス
    def valid_chain(self, chain):
        pre_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            if block['previous_hash'] != self.hash(pre_block):
                print('previous hash conflict')
                return False

            if current_index > 2 and not self.valid_proof(
                json.loads(block['transactions']), block['previous_hash'],
                block['nonce'], block['difficulty']):
                print('proof conflict')
                return False

            pre_block = block
            current_index += 1
        return True

    # p2pばん
    def resolve_conflicts(self, chain):
        print('resolve conflicts is called')
        my_chain_len = len(self.chain)
        new_chain_len = len(chain)

        pool_for_orphan_blocks = self.chain.copy()
        has_orphan = False

        if new_chain_len > my_chain_len and self.valid_chain(chain):
            print('overwrite blockchain')
            self.chain = chain
            self.previous_hash = self.hash(chain[-1])
            for tx in chain:
                for tx1 in pool_for_orphan_blocks:
                    if tx == tx1:
                        pool_for_orphan_blocks.remove(tx1)

            return self.previous_hash, pool_for_orphan_blocks
        return None, []
 
    def get_my_chain(self):
        return self.chain

    def get_my_transaction_pool(self):
        return self.get_my_transaction_pool

    def remove_useless_transaction(self, transaction_pool):
        """
            自分が管理するチェーンに含まれるトランザクションを除いたリストを返す
        """
        if len(transaction_pool) != 0:
            current_index = 1
            while current_index < len(self.chain):
                block = self.chain[current_index]
                transactions = block['transactions']
                for t in transactions:
                    for t2 in transaction_pool:
                        if t == json.dumps(t2):
                            print('already exist in my blockchain :', t2)
                            transaction_pool.remove(t2)
                current_index+=1
            return transaction_pool
        else:
            print('no transaction to be removed')
            return []

    def renew_transaction_pool(self):
        print('renew_transaction_pool is called')
        tp = self.transaction_pool.copy()
        self.transaction_pool = self.remove_useless_transaction(tp)

    @property
    def stored_transactions(self):
        current_index = 1
        stored_transactions_in_chain = []

        while current_index < len(self.chain):
            block = self.chain[current_index]
            transactions = block['transactions']
            
            for t in transactions:
                stored_transactions_in_chain.append(t)
            
            current_index+=1
        
        return stored_transactions_in_chain

    def append_block_to_mychain(self,block):
        self.chain.append(block)

    def block_check(self, block):
        stored_tx = self.stored_transactions
        txs = json.loads(block['transactions'])
        print(txs)
        for tx in txs:
            if tx in stored_tx:
                return False
        return True

