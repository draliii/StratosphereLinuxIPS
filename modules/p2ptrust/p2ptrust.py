# Must imports
import multiprocessing
import platform

# Your imports
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

        self.c1 = pubsub = __database__.r.pubsub()
        pubsub.subscribe('ip_info_change')
        # when the channels are oficially added (needs discussing with other slips developers),
        # self.c1 = __database__.subscribe('p2p_gopy')

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
                message = self.c1.get_message(timeout=None)
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
                    # TODO: kill go process as well
                    self.go_listener_process.kill()
                    return True

                if message["channel"] == "ip_info_change":
                    self.handle_update(message["data"])

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

    def handle_update(self, parameters: str):
        """
        Handle IP scores changing in Slips received from the ip_info_change channel

        This method checks if new score differs from opinion known to the network, and if so, it means that it is worth
        sharing and it will be shared. Additionally, if the score is serious, the node will be blamed
        :param parameters:
        :return:
        """

        # abort if the IP is not valid
        if not validate_ip_address(parameters):
            return

        # poll new info from redis
        ip_info = __database__.getIPData(parameters)

        slips_score, slips_confidence = read_data_from_ip_info(ip_info)
        # check that both values were provided
        if slips_score is None:
            return

        # TODO: implement a cache
        # fetch ip data from the cache/db

        # compare slips data with data in go
        # if data is different from network opinion and not shared recently, share with network

        # call proper function in rep model to update IP info

        # validate inputs
        try:
            ip, score, confidence = parameters.split(" ", 2)
            score = float(score)
            confidence = float(confidence)
        except ValueError as e:
            print("Parsing parameters failed, expected str, float, float:", parameters)
            return
        except TypeError as e:
            print("Parsing parameters failed, expected 3 values (ip, score, confidence):", parameters)
            return

        # if value is significant (different from cached, or completely new)

        # TODO: discuss - only share score if confidence is high enough?

        # if value is significant for a blame
        if score > 0.8 and confidence > 0.6:
            # TODO: justify the numbers
            # TODO: also, the score will not be reported, if it was already blamed before - is this what we want?
            self.publish("BLAME %s" % ip)
        else:
            self.publish("BROADCAST %s %f %f" % (ip, score, confidence))

        # TODO: it might also be worth here to share the data with the library, right...

    def handle_slips_ask(self, ip):
        # is in cache?
        # return from cache

        # otherwise

        # TODO: this is not verified to be an IP address, check that go does that
        self.publish("ASK %s" % ip)

        # go will send a reply in no longer than 10s (or whatever the timeout there is set to). The reply will be
        # processed by this module and database will be updated accordingly

    def handle_go_ask(self, parameters):
        # TODO: return value from redis directly
        pass

    def handle_go_data(self, parameters):
        # TODO: parse the json
        # process all peer responses
        # find outliers and adjust peer scores?
        # update data for ip in the cache
        # this is the place where some trust decisions can again be made
        pass
