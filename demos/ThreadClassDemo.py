import threading
import time

import threading
import time

class Worker(threading.Thread):
    def __init__(self):
        super().__init__()
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            print("-- worker working")
            time.sleep(0.5)

w = Worker()
w.start()
print("Worker has started running")
time.sleep(2)
print("Stopping the worker thread")
w.stop()
w.join()
print("Worker has stopped")
