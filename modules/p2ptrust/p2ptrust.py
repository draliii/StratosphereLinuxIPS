import multiprocessing
import configparser
import platform
import time

from slips.core.database import __database__
from slips.common.abstracts import Module

import modules.p2ptrust.trustdb as trustdb
from modules.p2ptrust.printer import Printer
import modules.p2ptrust.reputation_model as reputation_model
import modules.p2ptrust.go_listener as go_listener
import modules.p2ptrust.utils as utils


def validate_slips_data(message_data: str) -> (str, int):
    """
    Check that message received from slips channel has correct format: ip, timeout

    The message should contain an IP address (string), followed by a space and an integer timeout. If the message is
    correct, the two values are returned as a tuple (str, int). If not, (None, None) is returned.
    :param message_data: data from slips request channel
    :return: parsed values or None tuple
    """

    try:
        ip_address, time_since_cached = message_data.split(" ", 1)
        time_since_cached = int(time_since_cached)

        if not utils.validate_ip_address(ip_address):
            return None, None

        return ip_address, time_since_cached

    except ValueError:
        # message has wrong format
        return None, None


class Trust(Module, multiprocessing.Process):
    # Name: short name of the module. Do not use spaces
    name = 'p2ptrust'
    description = 'Enables sharing detection data with other Slips instances'
    authors = ['Dita']

    def __init__(self, output_queue: multiprocessing.Queue, config: configparser.ConfigParser):
        multiprocessing.Process.__init__(self)

        self.printer = Printer(output_queue, self.name)

        self.output_queue = output_queue
        # In case you need to read the slips.conf configuration file for your own configurations
        self.config = config
        # To which channels do you want to subscribe? When a message arrives on the channel the module will wakeup
        # The options change, so the last list is on the slips/core/database.py file. However common options are:
        # - new_ip
        # - tw_modified
        # - evidence_added

        self.print("Starting p2ptrust")

        self.pubsub = __database__.r.pubsub()
        self.pubsub.subscribe('ip_info_change')
        self.pubsub.subscribe('p2p_data_request')

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

        self.trust_db = trustdb.TrustDB(r"trustdb.db", self.printer, drop_tables_on_startup=True)
        self.reputation_model = reputation_model.ReputationModel(self.printer, self.trust_db, self.config)

        self.go_listener_process = go_listener.GoListener(self.printer, self.trust_db, self.config)
        self.go_listener_process.start()

    def print(self, text: str, verbose: int = 1, debug: int = 0) -> None:
        self.printer.print(text, verbose, debug)

    def run(self):
        try:
            # Main loop function
            while True:
                message = self.pubsub.get_message(timeout=None)
                # skip control messages, such as subscribe notifications
                if message['type'] != "message":
                    continue

                data = message['data']

                # listen to slips kill signal and quit
                if data == 'stop_process':
                    self.print("Received stop signal from slips, stopping")
                    self.trust_db.__del__()
                    self.go_listener_process.kill()
                    return True

                if message["channel"] == "ip_info_change":
                    self.print("IP info was updated in slips for ip: " + data)
                    self.handle_update(message["data"])
                    continue

                if message["channel"] == "p2p_data_request":
                    self.handle_data_request(message["data"])
                    continue

        except KeyboardInterrupt:
            return True
        except Exception as inst:
            self.print('Problem on the run()', 0, 1)
            self.print(str(type(inst)), 0, 1)
            self.print(str(inst.args), 0, 1)
            self.print(str(inst), 0, 1)
            return True


    def handle_update(self, ip_address: str) -> None:
        """
        Handle IP scores changing in Slips received from the ip_info_change channel

        This method checks if new score differs from opinion known to the network, and if so, it means that it is worth
        sharing and it will be shared. Additionally, if the score is serious, the node will be blamed
        :param ip_address: The IP address sent through the ip_info_change channel (if it is not valid IP, it returns)
        """

        # abort if the IP is not valid
        if not utils.validate_ip_address(ip_address):
            self.print("IP validation failed")
            return

        score, confidence = utils.get_ip_info_from_slips(ip_address)
        if score is None:
            self.print("IP doesn't have any score/confidence values in DB")
            return

        # insert data from slips to database
        # TODO: remove debug timestamps
        self.trust_db.insert_slips_score(ip_address, score, confidence, timestamp=3)

        # TODO: discuss - only share score if confidence is high enough?
        # compare slips data with data in go
        data_already_reported = True
        try:
            cached_opinion = self.trust_db.get_cached_network_opinion("ip", ip_address)
            cached_score, cached_confidence, network_score, timestamp = cached_opinion
            if cached_score is None:
                data_already_reported = False
            elif abs(score - cached_score) < 0.1:
                data_already_reported = False
        except KeyError:
            data_already_reported = False
        except IndexError:
            # data saved in local db have wrong structure, this is an invalid state
            return

        # TODO: in the future, be smarter and share only when needed. For now, we will always share
        # if not data_already_reported:
        #     send_evaluation_to_go(ip_address, score, confidence, "*")
        utils.send_evaluation_to_go(ip_address, score, confidence, "*")

        # TODO: discuss - based on what criteria should we start blaming?
        if score > 0.8 and confidence > 0.6:
            utils.send_blame_to_go(ip_address, score, confidence)

    def handle_data_request(self, message_data: str) -> None:
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
        If not, the database is checked. An ASK query is sent to the network and responses are collected and saved into
        the redis database.

        :param message_data: The data received from the redis channel `p2p_data_response`
        :return: None, the result is saved into the redis database under key `p2p4slips`
        """

        # make sure that IP address is valid and cache age is a valid timestamp from the past
        ip_address, cache_age = validate_slips_data(message_data)
        if ip_address is None:
            # TODO: send error notice to the channel?
            return

        # if data is in cache and is recent enough, nothing happens and Slips should just check the database
        score, confidence, network_score, timestamp = self.trust_db.get_cached_network_opinion("ip", ip_address)
        if score is not None and time.time() - timestamp < cache_age:
            # cached value is ok, do nothing
            return

        # if cached value is old, ask the peers

        # TODO: in some cases, it is not necessary to wait, specify that and implement it
        #       I do not remember writing this comment. I have no idea in which cases there is no need to wait? Maybe
        #       when everybody responds asap?
        utils.send_request_to_go(ip_address)

        # go will send a reply in no longer than 10s (or whatever the timeout there is set to). The reply will be
        # processed by an independent process in this module and database will be updated accordingly
        time.sleep(10)

        # get data from db, processed by the trust model
        combined_score, combined_confidence, network_score = self.reputation_model.get_opinion_on_ip(ip_address)

        # no data in db - this happens when testing, if there is not enough data on peers
        if combined_score is None:
            self.print("No data received from network :(")
        else:
            self.print("Network shared some data, saving it now!")
            utils.save_ip_report_to_db(ip_address, combined_score, combined_confidence, network_score)
