import socket
import time
import pickle
import json

import utils
from blockchain import BlockChain
from wallet import Wallet
from p2p.connection_manager_4edge import ConnectionManager4Edge
from p2p.message_manager import (
    MessageManager,
    RSP_FULL_CHAIN,
    MSG_KEY_INFO,
    MSG_REQUEST_KEY_INFO,
    MSG_REQUEST_FULL_CHAIN,
    MSG_NEW_TRANSACTION
)


STATE_INIT = 0
STATE_ACTIVE = 1
STATE_SHUTTING_DOWN = 2


class ClientCore:

    def __init__(self, my_port=50082, c_host=None, c_port=None, callback=None):
        self.client_state = STATE_INIT
        print('Initializing ClientCore...')
        self.my_ip = utils.get_host()
        print('Server IP address is set to ... ', self.my_ip)
        self.my_port = my_port
        self.my_core_host = c_host
        self.my_core_port = c_port
        self.blockchain = BlockChain()
        self.wallet = Wallet()
        self.cm = ConnectionManager4Edge(self.my_ip, self.my_port, c_host, c_port, self.__handle_message)
        self.callback = callback

    def start(self, my_pubkey=None):
        """
            Edgeノードとしての待受を開始する（上位UI層向け
        """
        self.client_state = STATE_ACTIVE
        self.cm.start()
        self.cm.connect_to_core_node()
        # |TODO  鍵

    def shutdown(self):
        """
            待ち受け状態のServer Socketを閉じて終了する（上位UI層向け
        """
        self.client_state = STATE_SHUTTING_DOWN
        print('Shutdown edge node ...')
        self.cm.connection_close()

    def send_req_full_chain(self):
        """
            接続コアノードに対してフルチェーンを要求
        """
        msg_txt = self.cm.get_message_text(MSG_REQUEST_FULL_CHAIN)
        self.cm.send_msg((self.my_core_host, self.my_core_port), msg_txt)

    def send_req_key_info(self):
        """
            コアノードに鍵情報の送信願いを送信
        """
        msg_type = MSG_REQUEST_KEY_INFO
        self.send_message_to_my_core_node(msg_type)

    def send_new_transaction(self, msg):
        """
            接続コアノードに対してトランザクションを送信
            msg: json
        """
        msg_type = MSG_NEW_TRANSACTION
        self.send_message_to_my_core_node(msg_type, msg)

    def send_message_to_my_core_node(self, msg_type, msg=None):
        """
            接続中のCoreノードに対してメッセージを送付する（上位UI層向け

            Params:
                msg_type : MessageManagerで規定のメッセージ種別を指定する
                msg : メッセージ本文。文字列化されたJSONを想定
        """
        msg_txt = self.cm.get_message_text(msg_type, msg)
        print(msg_txt)
        self.cm.send_msg((self.my_core_host, self.my_core_port), msg_txt)

    def get_my_blockchain(self):
        return self.blockchain.chain

    def __handle_message(self, msg):
        """
            ConnectionManager4Edgeに引き渡すコールバックの中身。
        """
        if msg[2] == RSP_FULL_CHAIN:
            new_block_chain = json.loads(msg[4])
            result = self.blockchain.resolve_conflicts(new_block_chain)
            if result is not None:
                self.callback()
            else:
                print('received chain is invalid')
        elif msg[2] == MSG_KEY_INFO:
            miner_wallet = pickle.loads(msg[4].encode('utf8'))
            self.wallet = miner_wallet