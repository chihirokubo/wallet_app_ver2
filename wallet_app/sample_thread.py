import time
import threading

difficulty = 30

class yea:
	def __init__(self):
		self.self.mining_semaphore = threading.Semaphore(1)
		self.cnt = 0

	def start_mining(self):
        is_acquire = self.mining_semaphore.acquire(blocking=False)
        if is_acquire:
            with contextlib.ExitStack() as stack:
                stack.callback(self.mining_semaphore.release)
                self.mining_thread = threading.Thread(target=self.__minig)
                mining_interval = 20
                loop = threading.Timer(round(mining_interval), self.start_mining)
                loop.start()

    def __minig(self):
    	for i in range(10000):
    		self.cnt += 1

    def stop_mining(self):
    	self.mining_thread
