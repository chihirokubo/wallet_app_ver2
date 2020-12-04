import contextlib
import hashlib
import json
import logging
import sys
import random
import time
import threading

# Deleted by 暗号班
# 楕円曲線からの鍵生成をスクラッチ実装したため
#from ecdsa import NIST256p
#from ecdsa import VerifyingKey
import requests

import utils
# 鍵をつくるために必要なクラス By 暗号班
from S256 import S256Point
from S256 import G
from S256 import N

# Added & Deleted By コンセンサス班
#MINING_DIFFICULTY = 3
MINING_SENDER = 'THE BLOCKCHAIN'
MINING_REWARD = 1.0
#MINING_TIMER_SEC = 20

BLOCKCHAIN_PORT_RANGE = (5000, 5003)
NEIGHBOURS_IP_RANGE_NUM = (0, 1)
BLOCKCHAIN_NEIGHBOURS_SYNC_TIME_SEC = 20

# Added By コンセンサス
ILLEGAL_TIMER_SEC = 20
HACKING = 'HACKER'

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


class BlockChain(object):

    def __init__(self, blockchain_address=None, port=None):
        """
        self.transaction_pool = []
        self.chain = []
        self.neighbours = []
        self.create_block(0, self.hash({}))
        self.blockchain_address = blockchain_address
        self.port = port
        self.mining_semaphore = threading.Semaphore(1)
        self.sync_neighbours_semaphore = threading.Semaphore(1)
        """
        self.transaction_pool = []
        self.chain = []
        self.neighbours = []
        self.mining_speed = random.uniform(5.0, 5.3) # Added By コンセンサス
        self.difficulty = 3                          # Added By コンセンサス
        self.create_block(0, self.hash({}))
        self.blockchain_address = blockchain_address
        self.port = port
        self.mining_semaphore = threading.Semaphore(1)
        self.sync_neighbours_semaphore = threading.Semaphore(1)

    def run(self):
        self.sync_neighbours()
        self.resolve_conflicts()
        self.start_mining()
        # self.carry_on_illegal() # Added By コンセンサス班

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

    #採掘難度の調整 Added By コンセンサス
    def daa(self, speed):
        if 6.0 < speed:
            self.mining_speed -= random.random()
            self.difficulty -= 1
        elif speed > 5.0 and speed < 6.0:
            self.mining_speed -= random.random()
            if self.mining_speed < 5.0:
                self.difficulty += 1
        elif speed > 4.0 and speed < 5.0:
            self.mining_speed += random.random()
            if self.mining_speed > 5.6:
                self.difficulty -= 1
        else:
            self.mining_speed = 5.0 + random.uniform(0.0, 0.4)
        return self.mining_speed
        
    # Changed By コンセンサス
    def valid_proof(self, transactions, previous_hash, nonce):
        guess_block = utils.sorted_dict_by_key({
            'transactions': transactions,
            'nonce': nonce,
            'previous_hash': previous_hash
        })
        guess_hash = self.hash(guess_block)
        return guess_hash[:self.difficulty] == '0'*self.difficulty

    # 共通
    def proof_of_work(self):
      # transactions = copy.deepcopy(self.transaction_pool) # ここだけAdded By コンセンサス
        transactions = self.transaction_pool.copy()
        previous_hash = self.hash(self.chain[-1])
        nonce = 0
        while self.valid_proof(transactions, previous_hash, nonce) is False:
            nonce += 1
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
        previous_hash = self.hash(self.chain[-1])
        self.create_block(nonce, previous_hash)

        elapse = round(time.time() - start)
        self.mining_speed = round(random.uniform(4.95, 5.05)+elapse, 3)

        logger.info({'action': 'mining', 'status': 'success'})
        for node in self.neighbours:
            requests.put(f'http://{node}/consensus')

        self.daa(self.mining_speed)

        # print('mining time : ' + str(round(self.mining_speed, 3)))
        # print('difficulty : ', str(self.difficulty))

        stop = round(self.mining_speed)
        time.sleep(stop)

        return True


    """ 
    # Added By コンセンサス
    def illegal(self, recipient_blockchain_address, value):
        if self.add_transaction:
            if self.chain == []:
                logger.info({'action': 'illegal', 'status': 'chain is empty'})
                return False
            for block in self.chain:
                for transaction in block['transaction']:
                    if transaction['recipient_blockchain_address'] == recipient_blockchain_address:
                        transaction['value'] = value
                        logger.info({'action': 'illegal', 'status': 'success'})
                        return True
                logger.info({'action': 'illegal', 'status': 'fail'})
                return False
        return False
    
    def carry_on_illegal(self):
        while True:
            self.illegal(HACKING, 1000)
            time.sleep(ILLEGAL_TIMER_SEC)     
    """

    # Changed by コンセンサス
    def start_mining(self):
        is_acquire = self.mining_semaphore.acquire(blocking=False)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self.mining_semaphore.release)
                self.mining()
                loop = threading.Timer(self.mining_speed, self.start_mining)
                loop.start()

    # 共通
    def calculate_total_amount(self, blockchain_address):
        total_amount = 0.0
        for block in self.chain:
            for transaction in block['transactions']:
                value = float(transaction['value'])
                if blockchain_address == \
                        transaction['recipient_blockchain_address']:
                    total_amount += value
                if blockchain_address == \
                        transaction['sender_blockchain_address']:
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

    
