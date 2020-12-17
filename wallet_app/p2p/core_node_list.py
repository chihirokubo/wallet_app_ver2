import threading


class CoreNodeList:

    def __init__(self):
        self.lock = threading.Lock()
        self.list = set()

    def add(self, peer):
        """
        Coreノードをリストに追加
        """
        with self.lock:
            print('Adding peer: ', peer)
            self.list.add((peer))
            print('Current Core List: ', self.list)


    def remove(self, peer):
        """
        Coreノードをリストから削除
        """
        with self.lock:
            if peer in self.list:
                print('Removing peer: ', peer)
                self.list.remove(peer)
                print('Current Core list: ', self.list)

    def overwrite(self, new_list):
        """
        Coreノードリストを上書き
        """
        with self.lock:
            print('core node list will be going to overwrite')
            self.list = new_list
            print('Current Core list: ', self.list)


    def get_list(self):
        """
        現在接続状態にあるPeerを返す
        """
        return self.list

    def get_length(self):
        return len(self.list)


    def get_c_node_info(self):
        """
        リストのトップにあるPeerを返す
        """
        return list(self.list)[0]

    def has_this_peer(self,peer):
        """
        peerがリストに含まれているかをチェック
        """
        return peer in self.list