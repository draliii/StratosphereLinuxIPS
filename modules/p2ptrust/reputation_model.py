import base64
import binascii
import ipaddress
import json
import multiprocessing
import time

from slips.core.database import Database as SlipsDatabase
from statistics import mean

from modules.p2ptrust.trustdb import TrustDB


class ReputationModel(multiprocessing.Process):
    # this should be made into an interface
    def __init__(self, trustdb: TrustDB, redis_database: SlipsDatabase, config):
        super().__init__()
        # TODO: add proper OutputProcess printing
        self.trustdb = trustdb
        self.rdb = redis_database
        self.config = config
        self.rdb_channel = self.rdb.r.pubsub()
        self.rdb_channel.subscribe('p2p_gopy')

        self.evaluation_processors = {"score_confidence": self.process_evaluation_score_confidence}
        self.key_type_processors = {"ip": validate_ip_address}

    def run(self):
        while True:
            # listen for messages from the go part
            # TODO: figure out what to do with Slips request for data
            #       - Slips wants to know about an IP
            # TODO: handle errors here

            message = self.rdb_channel.get_message(timeout=None)

            if message["type"] != "message":
                continue

            print("RM:", message)

            data = message['data']

            # separate control instruction and its parameters
            try:
                command, parameters = data.split(" ", 1)
                command = command.lower()
                print("Command is:", command)

            # ignore the instruction, if no parameters were provided
            except ValueError:
                print("Invalid command: ", data)
                continue

            if command == "update":
                # TODO: this will be called as a function
                # this is not something that go is sending. this is data update from slips (kami's channel).
                self.handle_update(parameters)
                continue

            if command == "slips_ask":
                # TODO: no idea now how this will be called
                # however, the function that does the job is get_opinion_on_ip
                ask_process = multiprocessing.Process(target=self.handle_slips_ask, args=(parameters,))
                ask_process.start()
                continue

            if command == "go_ask":
                self.handle_go_ask(parameters)
                continue

            if command == "go_data":
                self.handle_go_data(parameters)
                continue

            print("Invalid command: ", data)

    def handle_go_ask(self, parameters):
        # TODO: parse IP from parameters
        ip = "1.2.3.4"
        ip_data = self.rdb.getIPData(ip)
        self.send_message_to_go(ip_data)

    def handle_go_data(self, parameters):
        reports = []
        try:
            reports = json.loads(parameters)
        except:
            # TODO: specify json error
            print("Go send invalid json")
            return

        if type(reports) != list:
            print("Expected list, got something else")
            return

        if len(reports) == 0:
            print("Data list is empty")
            return

        for report in reports:
            # report is the dictionary containing reporter, version, report_time and message

            # if intersection of a set of expected keys and the actual keys has four items, it means all keys are there
            key_reporter = "reporter"
            key_report_time = "report_time"
            key_message = "message"

            expected_keys = {key_reporter, key_report_time, key_message}
            # if the overlap of the two sets is smaller than the set of keys, some keys are missing. The & operator
            # picks the items that are present in both sets: {2, 4, 6, 8, 10, 12} & {3, 6, 9, 12, 15} = {3, 12}
            if len(expected_keys & set(report.keys())) != 3:
                print("Some key is missing in report")
                return

            if not validate_timestamp(report[key_report_time]):
                print("Invalid timestamp")
                return

            self.process_message(report[key_reporter],
                                 report[key_report_time],
                                 report[key_message]
                                 )
            # TODO: evaluate data from peer and asses if it was good or not.
            #       For invalid base64 etc, note that the node is bad

    def get_opinion_on_ip(self, ipaddress, max_age):
        # get report on that ip that is at most max_age old
        # if no such report is found:

        reports_on_ip = self.trustdb.get_opinion_on_ip(ipaddress, update_cache=True)
        network_score, combined_score, combined_confidence = self.assemble_peer_opinion(reports_on_ip)

        self.trustdb.update_network_opinion("ip", ipaddress, combined_score, combined_confidence, network_score)

    def compute_peer_reputation(self, trust, score, confidence):
        return trust * score * confidence

    def normalize_peer_reputations(self, peers):
        rep_sum = sum(peers)
        w = 1/rep_sum

        rep_avg = mean(peers)

        # now the reputations will sum to 1
        weighted_reputations = [w*x for x in peers]
        return rep_sum, rep_avg, weighted_reputations

    def assemble_peer_opinion(self, data):
        reports = []
        reporters = []

        for peer_report in data:
            report_score, report_confidence, reporter_trust, reporter_score, reporter_confidence = peer_report
            reports.append((report_score, report_confidence))
            reporters.append(self.compute_peer_reputation(reporter_trust, reporter_score, reporter_confidence))

        report_sum, report_avg, weighted_reporters = self.normalize_peer_reputations(reporters)

        combined_score = sum([r[0]*w for r, w, in zip(reports, weighted_reporters)])
        combined_confidence = sum([r[1]*w for r, w, in zip(reports, weighted_reporters)])

        network_score = report_avg

        return network_score, combined_score, combined_confidence

    def send_message_to_go(self, ip_data):
        # TODO: send data to p2p_pygo channel
        pass

    def process_message(self, reporter, report_time, message):

        # message is in base64
        try:
            decoded = base64.b64decode(message)
        except binascii.Error:
            # TODO: lower reputation
            print("base64 cannot be parsed properly")
            return

        # validate json
        print(decoded)
        try:
            data = json.loads(decoded)
        except:
            # TODO: lower reputation
            print("Peer sent invalid json")
            return

        print("peer json ok")

        # validate keys in message
        try:
            key = data["key"]
            key_type = data["key_type"]
            evaluation_type = data["evaluation_type"]
            evaluation = data["evaluation"]
        except:
            print("Correct keys are missing in the message")
            # TODO: lower reputation
            return

        # validate keytype and key
        if key_type not in self.key_type_processors:
            print("Module can't process given type")
            return

        if not self.key_type_processors[key_type](key):
            print("Provided key isn't a valid value for it's type")
            # TODO: lower reputation
            return

        # validate evaluation type
        if evaluation_type not in self.evaluation_processors:
            print("Module can't process given evaluation type")
            return

        self.evaluation_processors[evaluation_type](reporter, report_time, key_type, key, evaluation)

    def process_evaluation_score_confidence(self, reporter, report_time, key_type, key, evaluation):
        # check that both fields are present
        try:
            score = evaluation["score"]
            confidence = evaluation["confidence"]
        except:
            print("Score or confidence are missing")
            # TODO: lower reputation
            return

        # validate data types
        try:
            score = float(score)
            confidence = float(confidence)
        except:
            print("Score or confidence have wrong data type")
            # TODO: lower reputation
            return

        # validate value ranges (must be from <0, 1>)
        if score < 0 or score > 1:
            print("Score value is out of bounds")
            # TODO: lower reputation
            return

        if confidence < 0 or confidence > 1:
            print("Confidence value is out of bounds")
            # TODO: lower reputation
            return

        # TODO: save data to sqlite db
        result = "Data processing ok: reporter {}, report time {}, key {} ({}), score {}, confidence {}".format(reporter, report_time, key, key_type, score, confidence)
        print(result)
        pass

def validate_ip_address(ip):
    try:
        # this fails on invalid ip address
        ipaddress.ip_address(ip)
    except:
        return False

    return True


def validate_timestamp(timestamp):
    try:
        int_timestamp = int(timestamp)
    except:
        print("Timestamp is not int")
        return False


    if int_timestamp > time.time() or int_timestamp < 0:
        print("Invalid timestamp value")
        return False

    return True
