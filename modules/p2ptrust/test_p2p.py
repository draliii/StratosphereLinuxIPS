import configparser

import time
import random

from modules.p2ptrust.p2ptrust import Trust


def get_default_config():
    cfg = configparser.ConfigParser()
    cfg.read_file(open("slips.conf"))
    return cfg


def slips_listener_test():
    """
    A function to test if the retry queue is working as intended. Needs human interaction (disable network when asked)
    Test overview:
     - check ip A (will be cached successfully)
     - disable network
     - check ips B and C (they should be queued)
     - check ip from the same network as A (this should load from cache without errors, but not trigger retrying)
     - enable network
     - check ip from the same network as B (this will run and be cached, and trigger retrying. While retrying is in
         progress, it should check ip B and return cached result and then run a new query for C)
    :return: None
    """
    print("Running retry queue test")

    # to test the database properly and use channels, whoisip must be run as a module (not in the testing mode)
    from slips.core.database import __database__
    from multiprocessing import Queue
    from outputProcess import OutputProcess

    config = get_default_config()
    outputProcessQueue = Queue()
    outputProcessThread = OutputProcess(outputProcessQueue, 0, 1, config)
    outputProcessThread.start()

    __database__.setOutputQueue(outputProcessQueue)

    ModuleProcess = Trust(outputProcessQueue, config)
    ModuleProcess.start()

    print("check SEZNAM (should be cached successfully)")
    __database__.publish("new_ip", "77.75.75.172")

    time.sleep(1)
    print("[#######] Please disable the network, test will resume in 10s")
    time.sleep(10)
    print("[#######] Resuming test")

    print("check ALZA and CZNIC (they should be queued)")
    __database__.publish("new_ip", "185.181.176.19")  # alza
    __database__.publish("new_ip", "217.31.205.50")  # cznic

    time.sleep(1)
    print("check another SEZNAM IP (should be read from cache)")
    __database__.publish("new_ip", "77.75.75.173")

    time.sleep(1)
    print("[#######] Please enable the network, test will resume in 10s")
    time.sleep(10)
    print("[#######] Resuming test")

    print("check ip from the same network as B (this will run and be cached, and trigger retrying. While retrying is in"
          " progress, it should check ip B and return cached result and then run a new query for C)")
    __database__.publish("new_ip", "185.181.176.20")  # alza


if __name__ == "__main__":
    t = time.time()
    slips_listener_test()

    print(time.time() - t)
