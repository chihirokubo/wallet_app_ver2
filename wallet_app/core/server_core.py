import socket
import time
import pickle
import json
import threading
import contextlib
import random

import utils
from blockchain import (
    BlockChain,
    MINING_REWARD,
    MINING_SENDER,
    MINING_TIMER_SEC
)
from wallet import Wallet
from p2p.connection_manager import ConnectionManager
from p2p.my_protocol_message_handler import MyProtocolMessageHandler
from p2p.message_manager import (
    MSG_NEW_TRANSACTION,
    MSG_NEW_BLOCK,
    MSG_REQUEST_FULL_CHAIN,
    RSP_FULL_CHAIN,
    MSG_KEY_INFO,
    MSG_REQUEST_KEY_INFO,
    MSG_ENHANCED,
)

STATE_INIT = 0
STATE_STANDBY = 1
STATE_CONNECTED_TO_NETWORK = 2
STATE_SHUTTING_DOWN = 3

class ServerCore:

    def __init__(self, my_port=50082, core_node_host=None, core_node_port=None):
        self.server_state = STATE_INIT
        print('Initializing server...')
        self.my_ip = utils.get_host()
        print('Server IP address is set to ... ', self.my_ip)
        self.my_port = my_port
        self.cm = ConnectionManager(self.my_ip, self.my_port, self.__handle_message)
        self.mpm = MyProtocolMessageHandler()
        self.core_node_host = core_node_host
        self.core_node_port = core_node_port
        self.my_protocol_message_store = []
        self.is_mining_now = False
        self.flag_stop_mining = False
        self.miners_wallet = Wallet()
        self.blockchain = BlockChain(self.miners_wallet.blockchain_address)
        self.mining_semaphore = threading.Semaphore(1)
        self.__print_info()
        
    def __print_info(self):
        print({
            'private_key': self.miners_wallet.private_key,
            'public_key': self.miners_wallet.public_key,
            'blockchain_address': self.miners_wallet.blockchain_address
        })

    def start_mining(self):
        is_acquire = self.mining_semaphore.acquire(blocking=False)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self.mining_semaphore.release)
                if not self.flag_stop_mining:
                    self.__mining()
                else:
                    self.flag_stop_mining = True
                mining_interval = self.blockchain.mining_speed + random.uniform(9.8, 10.3)
                self.mining_loop = threading.Timer(round(mining_interval), self.start_mining)
                self.mining_loop.start()

    def stop_mining(self):
        print('stop mining')
        self.mining_loop.cancel()

    def __mining(self):
        start_mining_time = time.time()
        result = self.blockchain.transaction_pool.copy()
        if len(result) == 0:
            print('transaction pool is empty')
        
        self.blockchain.transaction_pool = self.blockchain.remove_useless_transaction(result)
        self.blockchain.add_transaction(
            sender_blockchain_address=MINING_SENDER,
            recipient_blockchain_address=self.blockchain.blockchain_address,
            value=MINING_REWARD,
            timestamp=time.time())
        nonce = self.blockchain.proof_of_work()
        if nonce == -1:
            return False
        previous_hash = self.blockchain.previous_hash

        if previous_hash != self.blockchain.hash(self.blockchain.chain[-1]):
            return False
        new_block = self.blockchain.create_block(nonce, previous_hash)
        print({'action': 'mining', 'status':'success'})        

        if self.blockchain.block_check(new_block):
            print('append block success')
            msg_new_block = self.cm.get_message_text(MSG_NEW_BLOCK, json.dumps(new_block))
            self.cm.send_msg_to_all_peer(msg_new_block)
            self.blockchain.transaction_pool = []
        else :
            print('append block not success')

        end_mining_time = time.time()
        elapse = round(end_mining_time - start_mining_time, 4)
        #TODO difficultyの同期は必要？
        self.blockchain.difficulty_adjustment(elapse)
        
        return True

        

    def start(self):
        """
            Coreノードとしての待受を開始する（上位UI層向け
        """
        self.server_state = STATE_STANDBY
        self.cm.start()
        self.start_mining()

    def join_network(self):
        """
            事前に取得した情報に従い拠り所となる他のCoreノードに接続する（上位UI層向け
        """
        if self.core_node_host is not None:
            self.server_state = STATE_CONNECTED_TO_NETWORK
            self.cm.join_network(self.core_node_host, self.core_node_port)
        else:
            print('This server is runnning as Genesis Core Node...')

    def shutdown(self):
        """
            待ち受け状態のServer Socketを閉じて終了する（上位UI層向け
        """
        self.server_state = STATE_SHUTTING_DOWN
        self.flag_stop_mining = True
        print('Shutdown server...')
        self.cm.connection_close()
        self.stop_mining()

    def get_my_current_state(self):
        """
            現在のCoreノードの状態を取得する（上位UI層向け。多分使う人いない
        """
        return self.server_state

    def get_all_chains_for_resolve_conflicts(self):
        new_message = self.cm.get_message_text(MSG_REQUEST_FULL_CHAIN)
        self.cm.send_msg_to_all_peer(new_message)

    def __core_api(self, request, message):
        """
            MyProtocolMessageHandlerで呼び出すための拡張関数群（現状未整備）

            params:
                request : MyProtocolMessageHandlerから呼び出されるコマンドの種別
                message : コマンド実行時に利用するために引き渡されるメッセージ
        """

        msg_type = MSG_ENHANCED

        if request == 'send_message_to_all_peer':
            new_message = self.cm.get_message_text(msg_type, message)
            self.cm.send_msg_to_all_peer(new_message)
            return 'ok'
        elif request == 'send_message_to_all_edge':
            new_message = self.cm.get_message_text(msg_type, message)
            self.cm.send_msg_to_all_edge(new_message)
            return 'ok'
        elif request == 'api_type':
            return 'server_core_api'

    def __handle_message(self, msg, is_core, peer=None):
        """
            ConnectionManagerに引き渡すコールバックの中身。
        """
        if peer is not None:
            if msg[2] == MSG_REQUEST_FULL_CHAIN:
                print('Send our latest blockchain for reply to : ', peer)
                my_chain = self.blockchain.get_my_chain()
                chain_data = json.dumps(my_chain)
                new_message = self.cm.get_message_text(RSP_FULL_CHAIN, chain_data)
                self.cm.send_msg(peer, new_message)
            elif msg[2] == MSG_REQUEST_KEY_INFO:
                key_info = pickle.dumps(self.miners_wallet, 0).decode()
                m_type = MSG_KEY_INFO
                message = self.cm.get_message_text(m_type, key_info)
                self.cm.send_msg(peer, message)
        else:
            if msg[2] == MSG_NEW_TRANSACTION:
                print('NEW_TRANSACTION command is called')
                payload = json.loads(msg[4])
                new_transaction = utils.sorted_dict_by_key({
                    'sender_blockchain_address': payload['sender_blockchain_address'],
                    'recipient_blockchain_address': payload['recipient_blockchain_address'],
                    'value': float(payload['value']),
                    'timestamp': payload['timestamp']
                })
                current_transactions = self.blockchain.transaction_pool.copy()
                print('new transaction : ', new_transaction)
                if new_transaction in current_transactions:
                    print('transaction is already in pool')
                    return
                else:
                    signature = pickle.loads(payload['signature'].encode('utf8'))
                    print('signature', signature)
                    is_transacted = self.blockchain.add_transaction(
                        payload['sender_blockchain_address'],
                        payload['recipient_blockchain_address'],
                        payload['value'],payload['timestamp'],
                        payload['sender_public_key'], signature
                    )
                    if is_transacted:
                        print('new transaction is generated')
                        print('\n\ntransaction_pool', self.blockchain.transaction_pool)
                    if not is_core:
                        # ウォレットからのトランザクションはブロードキャスト
                        print('transaction bloadcasted')
                        m_type = MSG_NEW_TRANSACTION
                        new_message = self.cm.get_message_text(m_type, msg[4])
                        self.cm.send_msg_to_all_peer(new_message)             
            elif msg[2] == MSG_NEW_BLOCK:
                print('NEW_BLOCK command is called')
                if not is_core:
                    return

                guess_block = json.loads(msg[4])
                transactions = guess_block['transactions']
                print('transactions: ', transactions)
                nonce = guess_block['nonce']
                print('nonce: ', nonce)
                previous_hash = guess_block['previous_hash']
                print('previous_hash: ', previous_hash)
                difficulty = guess_block['difficulty']
                if self.blockchain.valid_proof(transactions, previous_hash, nonce, difficulty):
                    self.flag_stop_mining = True
                    self.blockchain.append_block_to_mychain(guess_block)
                    #self.transaction_pool = []
                    print('transaction_pool is renewed')
                    self.blockchain.renew_transaction_pool()
                else:
                    self.get_all_chains_for_resolve_conflicts()
            elif msg[2] == RSP_FULL_CHAIN:
                print('RSP_FULL_CHAIN command is called')
                if not is_core:
                    return

                new_block_chain = json.loads(msg[4])
                result, pool_for_orphan_blocks = self.blockchain.resolve_conflicts(new_block_chain)
                print({'result': result, 'pool_for_orphan_blocks':pool_for_orphan_blocks})
                if result is not None:
                    if len(pool_for_orphan_blocks)!=0:
                        print('orphan_block is exist')

    def __get_myip(self):
        """
            Google先生から自分のIPアドレスを取得する。内部利用のみを想定
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
