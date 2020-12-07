import contextlib
import hashlib
import json
import logging
import sys
import random
import time
import threading

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

# Added & Deleted By コンセンサス班
#MINING_DIFFICULTY = 3
MINING_SENDER = 'THE BLOCKCHAIN'
MINING_REWARD = 1.0
MINING_TIMER_SEC = 20

BLOCKCHAIN_PORT_RANGE = (5000, 5003)
NEIGHBOURS_IP_RANGE_NUM = (0, 1)
BLOCKCHAIN_NEIGHBOURS_SYNC_TIME_SEC = 20

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


class BlockChain(object):

    def __init__(self, blockchain_address=None, port=None):
        self.transaction_pool = []
        self.chain = []
        self.neighbours = []
        self.difficulty = 3     # Added By コンセンサス
        self.mining_speed = 0.0 # Added By コンセンサス
        self.create_block(0, self.hash({}))
        self.blockchain_address = blockchain_address
        self.port = port
        self.mining_semaphore = threading.Semaphore(1)
        self.sync_neighbours_semaphore = threading.Semaphore(1)

    def run(self):
        self.sync_neighbours()
        self.resolve_conflicts()
        self.start_mining()

    # 共通
    def set_neighbours(self):
        self.neighbours = utils.find_neighbours(
            utils.get_host(), self.port,
            NEIGHBOURS_IP_RANGE_NUM[0], NEIGHBOURS_IP_RANGE_NUM[1],
            BLOCKCHAIN_PORT_RANGE[0], BLOCKCHAIN_PORT_RANGE[1])
        logger.info({
            'action': 'set_neighbours', 'neighbours': self.neighbours
        })

    # 共通
    def sync_neighbours(self):
        is_acquire = self.sync_neighbours_semaphore.acquire(blocking=False)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self.sync_neighbours_semaphore.release)
                self.set_neighbours()
                loop = threading.Timer(
                    BLOCKCHAIN_NEIGHBOURS_SYNC_TIME_SEC, self.sync_neighbours)
                loop.start()

    # 共通
    def create_block(self, nonce, previous_hash):
        block = utils.sorted_dict_by_key({
            'timestamp': time.time(),
            'transactions': self.transaction_pool,
            'nonce': nonce,
            'previous_hash': previous_hash
        })
        self.chain.append(block)
        self.transaction_pool = []

        for node in self.neighbours:
            requests.delete(f'http://{node}/transactions')

        return block

    # 共通
    def hash(self, block):
        sorted_block = json.dumps(block, sort_keys=True)
        return hashlib.sha256(sorted_block.encode()).hexdigest()

    # 共通
    def add_transaction(self, sender_blockchain_address,
                        recipient_blockchain_address, value,
                        sender_public_key=None, signature=None):

        transaction = utils.sorted_dict_by_key({
            'sender_blockchain_address': sender_blockchain_address,
            'recipient_blockchain_address': recipient_blockchain_address,
            'value': float(value)
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
            return True
        return False

    # 共通
    def create_transaction(self, sender_blockchain_address,
                           recipient_blockchain_address, value,
                           sender_public_key, signature):

        is_transacted = self.add_transaction(
            sender_blockchain_address, recipient_blockchain_address,
            value, sender_public_key, signature)

        if is_transacted:
            for node in self.neighbours:
                requests.put(
                    f'http://{node}/transactions',
                    json={
                        'sender_blockchain_address': sender_blockchain_address,
                        'recipient_blockchain_address': recipient_blockchain_address,
                        'value': value,
                        'sender_public_key': sender_public_key,
                        'signature': signature,
                    }
                )
        return is_transacted
        

    # Changed By 暗号班
    def verify_transaction_signature(
            self, sender_public_key, signature, transaction):
        """ 署名の検証のスクラッチ化
        esdsaの内部で行なっていた計算をここで行っているイメージ
        返り値はbool型
        """
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
    def valid_proof(self, transactions, previous_hash, nonce):
        guess_block = utils.sorted_dict_by_key({
            'transactions': transactions,
            'nonce': nonce,
            'previous_hash': previous_hash
        })
        guess_hash = self.hash(guess_block)
        return guess_hash[:self.difficulty] == '0'*self.difficulty

    # Changed By コンセンサス
    def proof_of_work(self):
        transactions = self.transaction_pool.copy()
        previous_hash = self.hash(self.chain[-1])
        nonce = 0
        start = time.time()
        while self.valid_proof(transactions, previous_hash, nonce) is False:
            nonce += 1
            elapse = time.time() - start
            if elapse >= 10.0:
                self.difficulty -= 1
                return -1
        return nonce


    # Changed By コンセンサス
    def mining(self):
        # if not self.transaction_pool:
        #    return False
        start = time.time()
        self.add_transaction(
            sender_blockchain_address=MINING_SENDER,
            recipient_blockchain_address=self.blockchain_address,
            value=MINING_REWARD)
        nonce = self.proof_of_work()
        if nonce == -1:
            return False
        previous_hash = self.hash(self.chain[-1])
        self.create_block(nonce, previous_hash)
        logger.info({'action': 'mining', 'status': 'success'})

        for node in self.neighbours:
            requests.put(f'http://{node}/consensus')

        elapse = round(time.time() - start, 4)
        self.difficulty_adjustment(elapse)

        # print('mining speed : ', str(round(self.mining_speed, 3)))
        # print('difficult : ', str(self.difficulty))

        return True

    # Changed by コンセンサス
    def start_mining(self):
        is_acquire = self.mining_semaphore.acquire(blocking=False)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self.mining_semaphore.release)
                self.mining()
                mining_interval = self.mining_speed + random.uniform(9.8, 10.3)
                loop = threading.Timer(round(mining_interval), self.start_mining)
                loop.start()

    # 共通
    def calculate_total_amount(self, blockchain_address):
        total_amount = 0.0
        for block in self.chain:
            for transaction in block['transactions']:
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
                return False

            if not self.valid_proof(
                block['transactions'], block['previous_hash'],
                block['nonce']):
                return False

            pre_block = block
            current_index += 1
        return True

    # 共通
    def resolve_conflicts(self):
        longest_chain = None
        max_length = len(self.chain)
        for node in self.neighbours:
            response = requests.get(f'http://{node}/chain')
            if response.status_code == 200:
                response_json = response.json()
                chain = response_json['chain']
                chain_length = len(chain)
                if chain_length > max_length and self.valid_chain(chain):
                    max_length = chain_length
                    longest_chain = chain

        if longest_chain:
            self.chain = longest_chain
            logger.info({'action': 'resolve_conflicts', 'status': 'replaced'})
            return True

        logger.info({'action': 'resolve_conflicts', 'status': 'not_replaced'})
        return False


