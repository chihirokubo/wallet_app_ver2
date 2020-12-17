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
from p2p.message_manager import (
    MSG_NEW_TRANSACTION,
    MSG_NEW_BLOCK,
    MSG_REQUEST_FULL_CHAIN,
    RSP_FULL_CHAIN,
    MSG_KEY_INFO,
    MSG_REQUEST_KEY_INFO,
    MSG_DELETE_TRANSACTION
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
        self.core_node_host = core_node_host
        self.core_node_port = core_node_port
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

    def start(self):
        """
            Coreノードとしての待受を開始
        """
        self.server_state = STATE_STANDBY
        self.cm.start()
        self.start_mining()

    def join_network(self):
        """
            事前に取得した情報に従い拠り所となる他のCoreノードに接続
        """
        if self.core_node_host is not None:
            self.server_state = STATE_CONNECTED_TO_NETWORK
            self.cm.join_network(self.core_node_host, self.core_node_port)
        else:
            print('This server is runnning as Genesis Core Node...')

    def shutdown(self):
        """
            待ち受け状態のServer Socketを閉じて終了
        """
        self.server_state = STATE_SHUTTING_DOWN
        print('Shutdown server...')
        self.cm.connection_close()

    
    def start_mining(self):
        print('start mining')
        is_acquire = self.mining_semaphore.acquire(blocking=False)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self.mining_semaphore.release)
                self.__mining()
                mining_interval = self.blockchain.mining_speed + random.uniform(9.8, 10.3)
                loop = threading.Timer(round(mining_interval), self.start_mining)
                loop.start()

    def __mining(self):
        start = time.time()
        self.blockchain.add_transaction(
            sender_blockchain_address=MINING_SENDER,
            recipient_blockchain_address=self.blockchain.blockchain_address,
            value=MINING_REWARD)
        nonce = self.blockchain.proof_of_work()
        if nonce == -1:
            return False
        previous_hash = self.blockchain.hash(self.blockchain.chain[-1])
        is_created, block = self.blockchain.create_block(nonce, previous_hash)
        if not is_created:
            return False
        self.delete_transaction_for_all_peer()

        print({'action': 'mining', 'status': 'success'})
        utils.pprint(self.blockchain.chain)

        self.send_all_chain_for_consensus()

        elapse = round(time.time() - start, 4)
        self.blockchain.difficulty_adjustment(elapse)

        # print('mining speed : ', str(round(self.mining_speed, 3)))
        # print('difficult : ', str(self.difficulty))

        return True


    def delete_transaction_for_all_peer(self):
        """
            ノードのトランザクションプールをからにするメッセージの送信
        """
        new_message = self.cm.get_message_text(MSG_DELETE_TRANSACTION)
        self.cm.send_msg_to_all_peer(new_message)

    def send_all_chain_for_consensus(self):
        """
            チェーンを全てのノードに送信してコンセンサス
        """
        my_chain = self.blockchain.chain
        chain_data = json.dumps(my_chain)
        new_message = self.cm.get_message_text(RSP_FULL_CHAIN, chain_data)
        self.cm.send_msg_to_all_peer(new_message)

    def __handle_message(self, msg, is_core, peer=None):
        """
            ConnectionManagerに引き渡すコールバックの中身。
        """
        print('message_type : ', msg[2])
        if peer is not None:
            if msg[2] == MSG_REQUEST_FULL_CHAIN:
                # walletのチェーンを同期
                print('Send our latest blockchain for reply to : ', peer)
                my_chain = self.blockchain.chain
                chain_data = json.dumps(my_chain)
                new_message = self.cm.get_message_text(RSP_FULL_CHAIN, chain_data)
                self.cm.send_msg(peer, new_message)
            elif msg[2] == MSG_REQUEST_KEY_INFO:
                # walletにminerの鍵情報を渡す
                key_info = pickle.dumps(self.miners_wallet, 0).decode()
                m_type = MSG_KEY_INFO
                message = self.cm.get_message_text(m_type, key_info)
                self.cm.send_msg(peer, message)
            elif msg[2] == MSG_DELETE_TRANSACTION:
                # transaction poolを空に
                print('DELETE_TRANSACTION is called')
                self.blockchain.transaction_pool = []
        else:
            if msg[2] == MSG_NEW_TRANSACTION:
                print('NEW_TRANSACTION command is called')
                payload = json.loads(msg[4])
                new_transaction = utils.sorted_dict_by_key({
                    'sender_blockchain_address': payload['sender_blockchain_address'],
                    'recipient_blockchain_address': payload['recipient_blockchain_address'],
                    'value': float(payload['value'])
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
                        payload['value'],
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
            elif msg[2] == RSP_FULL_CHAIN:
                print('RSP_FULL_CHAIN command is called')
                if not is_core:
                    return

                new_block_chain = json.loads(msg[4])
                self.blockchain.resolve_conflicts(new_block_chain)