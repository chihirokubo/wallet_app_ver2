import socket
import time
import pickle
import threading
import contextlib
import random

import utils
from blockchain import BlockChain
from wallet import Wallet
from p2p.connection_manager import ConnectionManager
from p2p.my_protocol_message_handler import MyProtocolMessageHandler
from p2p.message_manager import (
    MSG_NEW_TRANSACTION,
    MSG_NEW_BLOCK,
    MSG_REQUEST_FULL_CHAIN,
    RSP_FULL_CHAIN,
    MSG_ENHANCED,
)

STATE_INIT = 0
STATE_STANDBY = 1
STATE_CONNECTED_TO_NETWORK = 2
STATE_SHUTTING_DOWN = 3

MINING_SENDER = 'THE BLOCKCHAIN'
MINING_TIMER_SEC = 20
MINING_REWARD = 1.0



class ServerCore:

    def __init__(self, my_port=50082, core_node_host=None, core_node_port=None):
        self.server_state = STATE_INIT
        print('Initializing server...')
        self.my_ip = self.__get_myip()
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
                self.__mining()
                mining_interval = self.blockchain.mining_speed + random.uniform(9.8, 10.3)
                loop = threading.Timer(round(mining_interval), self.start_mining)
                loop.start()

    def stop_mining(self):
        print('mining thread is stopped')
        

    def __mining(self):
        start_mining = time.time()
        self.blockchain.add_transaction(
            sender_blockchain_address=MINING_SENDER,
            recipient_blockchain_address=self.blockchain.blockchain_address,
            value=MINING_REWARD,
            timestamp=time.time())
        nonce = self.blockchain.proof_of_work()
        if nonce == -1:
            return False
        previous_hash = self.blockchain.hash(self.blockchain.get_my_chain()[-1])
        new_block = self.blockchain.create_block(nonce, previous_hash)
        print({'action': 'mining', 'status':'success'})

        msg_new_block = self.cm.get_message_text(MSG_NEW_BLOCK, pickle.dumps(new_block,0).decode())
        self.cm.send_msg_to_all_peer(msg_new_block)
        self.blockchain.transaction_pool = []

        end_mining = time.time()
        elapse = round(end_mining - start_mining, 4)
        #TODO difficultyの同期は必要？
        self.blockchain.difficulty_adjustment(elapse)
        
        print(self.blockchain.chain)
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
            print('Send our latest blockchain for reply to : ', peer)
            my_chain = self.blockchain.get_my_chain()
            chain_data = pickle.dumps(my_chain, 0).decode()
            new_message = self.cm.get_message_text(RSP_FULL_CHAIN, chain_data)
            self.cm.send_msg(peer, new_message)
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
                current_transactions = self.blockchain.get_my_transaction_pool()
                if new_transaction in current_transactions:
                    print('transaction is already in pool')
                    return
                else:
                    self.blockchain.add_transaction(
                        payload['sender_blockchain_address'],
                        payload['recipient_blockchain_address'],
                        payload['value'],payload['timestamp'],
                        payload['sender_public_key'], payload['signature']
                    )
                    
                    if not is_core:
                        m_type = MSG_NEW_TRANSACTION
                        new_message = self.cm.get_message_text(m_type, json.dumps(new_transaction))
                        self.cm.send_msg_to_all_peer(new_message)                
            elif msg[2] == MSG_NEW_BLOCK:
                print('NEW_BLOCK command is called')
                if not is_core:
                    return

                guess_block = pickle.loads(msg[4].encode('utf8'))
                print('guess_block', guess_block)
                transactions = guess_block['transactions']
                nonce = guess_block['nonce']
                previous_hash = guess_block['previous_hash']
                if self.blockchain.valid_proof(transactions, previous_hash, nonce):
                    if self.is_mining_now:
                        self.flag_stop_mining = True
                    self.blockchain.chain.append(guess_block)
                else:
                    self.get_all_chains_for_resolve_conflicts()
            elif msg[2] == RSP_FULL_CHAIN:
                print('RSP_FULL_CHAIN command is called')
                if not is_core:
                    return

                new_block_chain = pickle.loads(msg[4].encode('utf8'))
                result = self.blockchain.resolve_conflicts(new_block_chain)
                print('blockchain receive')

    def __get_myip(self):
        """
            Google先生から自分のIPアドレスを取得する。内部利用のみを想定
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
