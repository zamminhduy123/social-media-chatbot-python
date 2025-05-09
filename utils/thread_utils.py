import threading
import time

def delayed_call(delay, callback, *args, **kwargs):
    def wrapper():
        time.sleep(delay)
        callback(*args, **kwargs)

    threading.Thread(target=wrapper).start()