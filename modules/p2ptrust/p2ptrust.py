# Must imports
import ipaddress
import multiprocessing
import platform

# Your imports
import time

from modules.p2ptrust.trustdb import TrustDB
from modules.p2ptrust.go_listener import GoListener
from slips.common.abstracts import Module
from slips.core.database import __database__
from modules.p2ptrust.go_listener import validate_ip_address


def read_data_from_ip_info(ip_info: dict) -> (float, float):
    try:
        score = ip_info["score"]
        confidence = ip_info["confidence"]
        return float(score), float(confidence)
    except KeyError:
        return None, None


def validate_ip_address(ip):
    try:
        # this fails on invalid ip address
        ipaddress.ip_address(ip)
    except:
        return False

    return True


class Trust(Module, multiprocessing.Process):
    # Name: short name of the module. Do not use spaces
    name = 'p2ptrust'
    description = 'Enables sharing detection data with other Slips instances'
    authors = ['Dita']

    def __init__(self, outputqueue, config):
        multiprocessing.Process.__init__(self)
        # All the printing output should be sent to the outputqueue. The outputqueue is connected to another process
        # called OutputProcess
        self.outputqueue = outputqueue
        # In case you need to read the slips.conf configuration file for your own configurations
        self.config = config
        # Start the DB
        __database__.start(self.config)
        # To which channels do you want to subscribe? When a message arrives on the channel the module will wakeup
        # The options change, so the last list is on the slips/core/database.py file. However common options are:
        # - new_ip
        # - tw_modified
        # - evidence_added

        print("Starting p2ptrust")

        self.pubsub = __database__.r.pubsub()
        self.pubsub.subscribe('ip_info_change')
        self.pubsub.subscribe('p2p_data_requests')

        # Set the timeout based on the platform. This is because the pyredis lib does not have officially recognized the
        # timeout=None as it works in only macos and timeout=-1 as it only works in linux
        if platform.system() == 'Darwin':
            # macos
            self.timeout = None
        elif platform.system() == 'Linux':
            # linux
            self.timeout = -1
        else:
            # ??
            self.timeout = None

        self.sqlite_db = TrustDB(r"trustdb.db")

        self.go_listener_process = GoListener(self.sqlite_db, __database__, self.config)
        self.go_listener_process.start()

        # cache for reports sent/received
        # this should contain recent opinions - on each report, the "network opinion" should be recalculated, and saved
        # ip: (timestamp, score, confidence, network trust data..,?)
        self.last_ip_update = {}

        # cache for detections from slips
        # ip: (timestamp, score, confidence)
        # if ip is not here, it should be fetched from slips
        self.slips_opinion = {}

    def print(self, text, verbose=1, debug=0):
        """ 
        Function to use to print text using the outputqueue of slips.
        Slips then decides how, when and where to print this text by taking all the processes into account

        Input
         verbose: is the minimum verbosity level required for this text to be printed
         debug: is the minimum debugging level required for this text to be printed
         text: text to print. Can include format like 'Test {}'.format('here')
        
        If not specified, the minimum verbosity level required is 1, and the minimum debugging level is 0
        """

        vd_text = str(int(verbose) * 10 + int(debug))
        self.outputqueue.put(vd_text + '|' + self.name + '|[' + self.name + '] ' + str(text))

    def run(self):
        try:
            # Main loop function
            while True:
                message = self.pubsub.get_message(timeout=None)
                # skip control messages, such as subscribe notifications
                if message['type'] != "message":
                    continue

                data = message['data']
                print("Trust got a message:", data)
                print(message)

                # listen to slips kill signal and quit
                if data == 'stop_process':
                    print("Received stop signal from slips, stopping")
                    self.sqlite_db.__del__()
                    self.go_listener_process.kill()
                    return True

                if message["channel"] == "ip_info_change":
                    self.handle_update(message["data"])

                if message["channel"] == "p2p_data_requests":
                    self.handle_data_request(message["data"])

        except KeyboardInterrupt:
            return True
        except Exception as inst:
            self.print('Problem on the run()', 0, 1)
            self.print(str(type(inst)), 0, 1)
            self.print(str(inst.args), 0, 1)
            self.print(str(inst), 0, 1)
            return True

    def publish(self, message):
        print("[publish]", message)
        __database__.publish("p2p_pygo", message)

    def handle_update(self, ip_address: str):
        """
        Handle IP scores changing in Slips received from the ip_info_change channel

        This method checks if new score differs from opinion known to the network, and if so, it means that it is worth
        sharing and it will be shared. Additionally, if the score is serious, the node will be blamed
        :param ip_address:
        :return:
        """

        # abort if the IP is not valid
        if not validate_ip_address(ip_address):
            return

        score, confidence = self.get_ip_info(ip_address)
        if score is None:
            return

        # TODO: discuss - only share score if confidence is high enough?
        # compare slips data with data in go
        data_already_reported = True
        try:
            reported_data = self.last_ip_update[ip_address]
            if abs(score - reported_data[1]) < 0.1:
                data_already_reported = False
        except KeyError:
            data_already_reported = False
        except IndexError:
            # data saved in local db have wrong structure, this is an invalid state
            return

        if not data_already_reported:
            # TODO: actually send the data here
            self.publish("BROADCAST %s %f %f" % (ip_address, score, confidence))

        # TODO: discuss - based on what criteria should we start blaming?
        if score > 0.8 and confidence > 0.6:
            # TODO: blame should support score and confidence as well
            self.publish("BLAME %s" % ip_address)

    def get_ip_info(self, ip_address):
        # poll new info from redis
        ip_info = __database__.getIPData(ip_address)

        slips_score, slips_confidence = read_data_from_ip_info(ip_info)
        # check that both values were provided
        if slips_score is None:
            return None, None

        # update data in cache
        self.slips_opinion[ip_address] = (time.time(), slips_score, slips_confidence)

        return slips_score, slips_confidence

    def handle_data_request(self, message_data):
        """
        Read data request from Slips and collect the data.

        Three `arguments` are expected in the redis channel:
            ip_address: str,
            cache_age: int [seconds]
        The return value is sent to the redis channel `p2p_data_response` in the format:
            ip_address: str,
            timestamp: int [time of assembling the response],
            network_opinion: float,
            network_confidence: float,
            network_competence: float,
            network_trust: float

        This method will check if any data not older than `cache_age` is saved in cache. If yes, this data is returned.
        If not, the database is checked. An ASK query is sent to the network and responses are collected and sent to the
        `p2p_data_response` channel.

        :param message_data: The data received from the redis channel `p2p_data_response`
        :return: None, the result is sent via a channel
        """

        ip_address, time_since_cached = message_data.split(" ", 1)



        # is in cache?
        # return from cache

        # otherwise

        # TODO: this is not verified to be an IP address, check that go does that
        self.publish("ASK %s" % ip)

        # go will send a reply in no longer than 10s (or whatever the timeout there is set to). The reply will be
        # processed by this module and database will be updated accordingly
        pass
