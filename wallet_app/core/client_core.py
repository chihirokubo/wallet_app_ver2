import socket
import time
import pickle

from blockchain import BlockChain
from wallet import Wallet
from p2p.connection_manager_4edge import ConnectionManager4Edge
from p2p.my_protocol_message_handler import MyProtocolMessageHandler
from p2p.message_manager import (
    MessageManager,
    RSP_FULL_CHAIN,
    MSG_ENHANCED,
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
        self.my_ip = self.__get_myip()
        print('Server IP address is set to ... ', self.my_ip)
        self.my_port = my_port
        self.my_core_host = c_host
        self.my_core_port = c_port
        self.blockchain = BlockChain()
        self.wallet = Wallet()
        self.cm = ConnectionManager4Edge(self.my_ip, self.my_port, c_host, c_port, self.__handle_message)
        self.mpm = MyProtocolMessageHandler()
        self.my_protocol_message_store = []
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

    def get_my_current_state(self):
        """
            現在のEdgeノードの状態を取得する（上位UI層向け
        """
        return self.client_state

    def send_req_full_chain(self):
        """
            接続コアノードに対してフルチェーンを要求
        """
        msg_txt = self.cm.get_message_text(MSG_REQUEST_FULL_CHAIN)
        self.cm.send_msg((self.my_core_host, self.my_core_port), msg_txt)

    def send_new_transaction(self, msg):
        """
            接続コアノードに対してトランザクションを送信
        """
        msg_type = MSG_NEW_TRANSACTION
        self.send_message_to_my_core_node(msg_type, msg)

    def send_message_to_my_core_node(self, msg_type, msg):
        """
            接続中のCoreノードに対してメッセージを送付する（上位UI層向け

            Params:
                msg_type : MessageManagerで規定のメッセージ種別を指定する
                msg : メッセージ本文。文字列化されたJSONを想定
        """
        msg_txt = self.cm.get_message_text(msg_type, msg)
        print(msg_txt)
        self.cm.send_msg((self.my_core_host, self.my_core_port), msg_txt)

    def get_my_protocol_messages(self):
        """
            拡張メッセージとして送信されてきたメッセージを格納しているリストを取得する
            （現状未整備で特に意図した利用用途なし）
        """

        if self.my_protocol_message_store != []:
            return self.my_protocol_message_store
        else:
            return None

    def get_my_blockchain(self):
        return self.blockchain.get_my_chain()

    def __client_api(self, request, message):
        """
            MyProtocolMessageHandlerで呼び出すための拡張関数群（現状未整備）

            params:
                request : MyProtocolMessageHandlerから呼び出されるコマンドの種別
                message : コマンド実行時に利用するために引き渡されるメッセージ
        """
        if request == 'pass_message_to_client_application':
            self.my_protocol_message_store.append(message)
        elif request == 'api_type':
            return 'client_core_api'
        else:
            print('not implemented api was used')

    def __handle_message(self, msg):
        """
            ConnectionManager4Edgeに引き渡すコールバックの中身。
        """
        print(msg)
        if msg[2] == RSP_FULL_CHAIN:
            new_block_chain = pickle.loads(msg[4].encode('utf8'))
            result, _ = self.blockchain.resolve_conflicts(new_block_chain)
            if result:
                self.callback()
            else:
                print('received chain is invalid')

        elif msg[2] == MSG_ENHANCED:
            # P2P Network を単なるトランスポートして使っているアプリケーションが独自拡張したメッセージはここで処理する。
            # SimpleBitcoin としてはこの種別は使わない
            self.mpm.handle_message(msg[4], self.__client_api)

    def __get_myip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
