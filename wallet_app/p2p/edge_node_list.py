import threading


class EdgeNodeList:

    def __init__(self):
        self.lock = threading.Lock()
        self.list = set()

    def add(self, edge):
        """
        Edgeノードをリストに追加
        """
        with self.lock:
            print('Adding edge: ', edge)
            self.list.add((edge))
            print('Current Edge List: ', self.list)

    def remove(self, edge):
        """
        Edgeノードをリストから削除
        """
        with self.lock:
            if edge in self.list:
                print('Removing edge: ', edge)
                self.list.remove(edge)
                print('Current Edge list: ', self.list)

    def overwrite(self, new_list):
        """
        Edgeノードを上書き
        """
        with self.lock:
            print('edge node list will be going to overwrite')
            self.list = new_list
            print('Current Edge list: ', self.list)

    def get_list(self):
        """
        現在接続状態にあるEdgeノードの一覧を返す
        """
        return self.list
