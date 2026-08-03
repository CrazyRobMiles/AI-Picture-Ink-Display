# Shows how a program can execute two threads at the same time. 

import threading
import time

def evil_worker():
    while(True):
        print("Har Har")

def worker(name):
    print(f"{name}: starting")
    time.sleep(1)
    print(f"{name}: done")

t = threading.Thread(target=worker, args=("Thread-1",))
t.start()
print("Worker has started running")
t.join()  # wait for it to finish
print("Worker has finished")


