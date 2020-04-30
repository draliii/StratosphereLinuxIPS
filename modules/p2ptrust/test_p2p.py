import configparser
import time
from modules.p2ptrust.p2ptrust import Trust
from slips.core.database import Database
import modules.p2ptrust.json_data as json_data


def init_tests():
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
    print("Initialization complete")

    return module_process, __database__


def set_ip_data(database: Database, ip: str, data: dict):
    database.setNewIP(ip)
    database.setInfoForIPs(ip, data)


def test_slips_integration():
    module_process, database = init_tests()

    # add a new peer abcsakughroiauqrghaui on IP 192.168.0.4
    module_process.sqlite_db.insert_go_score("abcsakughroiauqrghaui", 1, 0)
    module_process.sqlite_db.insert_go_ip_pairing("abcsakughroiauqrghaui", "192.168.0.4", 1) #B
    set_ip_data(database, "192.168.0.4", {"score": 0.1, "confidence": 1})

    # add a new peer anotherreporterspeerid on IP 192.168.0.5
    module_process.sqlite_db.insert_go_score("anotherreporterspeerid", 0.8, 0)
    module_process.sqlite_db.insert_go_ip_pairing("anotherreporterspeerid", "192.168.0.5", 1) #C
    set_ip_data(database, "192.168.0.5", {"score": 0.1, "confidence": 1})

    # slips makes some detections
    set_ip_data(database, "1.2.3.4", {"score": 0.3, "confidence": 1})
    set_ip_data(database, "1.2.3.6", {"score": 0.7, "confidence": 0.7})
    time.sleep(1)
    print()

    # network shares some detections
    # {"key_type": "ip", "key": "1.2.3.40", "evaluation_type": "score_confidence", "evaluation": { "score": 0.9, "confidence": 0.6 }}
    # {"key_type": "ip", "key": "1.2.3.5", "evaluation_type": "score_confidence", "evaluation": { "score": 0.9, "confidence": 0.7 }}
    data = json_data.two_correct
    database.publish("p2p_gopy", "GO_DATA %s" % data)
    time.sleep(1)
    print()

    # slips asks for data about 1.2.3.5
    database.publish("p2p_data_request", "1.2.3.5 1000")
    time.sleep(1)
    print()

    # network asks for data about 1.2.3.4
    data = json_data.ok_request
    database.publish("p2p_gopy", "GO_DATA %s" % data)
    time.sleep(100000)
    print()

    # shutdown
    database.publish("p2p_data_request", "stop_process")
    print()


def test_inputs():

    module_process, __database__ = init_tests()

    for test_case_name, test_case in json_data.__dict__.items():
        if test_case_name.startswith("_"):
            continue
        else:
            print()
            print("#########################")
            print("Running test case:", test_case_name)
            print("-------------------------")
            __database__.publish("p2p_gopy", "go_data " + test_case)
            # the sleep is not needed, but it makes the log more readable
            time.sleep(1)

    print("Tests done.")


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
    print("Running slips listener test")

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
    # test_inputs()
    test_slips_integration()

    print(time.time() - t)
