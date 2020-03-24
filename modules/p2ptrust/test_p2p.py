import configparser

import time
import random

from modules.p2ptrust.p2ptrust import Trust


def get_default_config():
    cfg = configparser.ConfigParser()
    cfg.read_file(open("slips.conf"))
    return cfg


def make_data():
    data = [{"peer": "10.0.0.4", "credibility": 0.5, "data": '{"remote_ip": "8.8.8.8", "score":0.0, "confidence":0.9}'},
            {"peer": "10.0.0.9", "credibility": 0.9, "data": '{"remote_ip": "8.8.8.8", "score":0.1, "confidence":0.8}'}]

    # the data is a list of reports from multiple peers. Each report contains information about the remote peer (his IP
    # and his credibility), and the data the peer sent. From slips, we know that the data sent contains the IP address
    # the peer is reporting (attacker), the score the peer assigned to that ip (how malicious does he find him) and the
    # confidence he has in his score evaluation.
    pass


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
    module_process = Trust(outputProcessQueue, config)

    module_process.start()

    time.sleep(1)

    # invalid command
    __database__.publish("p2p_gopy", "foooooooooo")
    __database__.publish("p2p_gopy", "")

    # invalid command with parameters
    __database__.publish("p2p_gopy", "foooooooooo bar 3")

    # valid command, no parameters
    __database__.publish("p2p_gopy", "UPDATE")

    # valid update
    __database__.publish("p2p_gopy", "UPDATE ipaddress 1 1")
    __database__.publish("p2p_gopy", "UPDATE ipaddress 1.999999999999999 3")

    # update with unparsable parameters
    __database__.publish("p2p_gopy", "UPDATE ipaddress 1 five")
    __database__.publish("p2p_gopy", "UPDATE ipaddress 3")

    data = make_data()
    __database__.publish("p2p_gopy", "GO_DATA %s" % data)

    # stop instruction
    __database__.publish("p2p_gopy", "stop_process")


if __name__ == "__main__":
    t = time.time()
    slips_listener_test()

    print(time.time() - t)
