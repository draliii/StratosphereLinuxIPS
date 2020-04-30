import base64
import binascii
import json
import multiprocessing

from modules.p2ptrust.utils import validate_ip_address, validate_go_reports, validate_timestamp, \
    get_ip_info_from_slips, send_evaluation_to_go
from slips.core.database import Database as SlipsDatabase
from modules.p2ptrust.trustdb import TrustDB


class GoListener(multiprocessing.Process):
    """Process that listens to requests and reports from the go part of p2ptrust

    The reports from other peers are processed and inserted into the database directly.
    Requests from other peers are validated, data is read from the database and from slips, and the response is sent.
    If peer sends invalid data, his reputation is lowered.
    """

    def __init__(self, trustdb: TrustDB, redis_database: SlipsDatabase, config):
        super().__init__()

        print("Starting go listener")

        # TODO: add proper OutputProcess printing
        self.trustdb = trustdb
        self.rdb = redis_database
        self.config = config
        self.rdb_channel = self.rdb.r.pubsub()
        self.rdb_channel.subscribe('p2p_gopy')

        # TODO: there should be some better mechanism to add new processing functions.. Maybe load from files?
        self.evaluation_processors = {"score_confidence": self.process_evaluation_score_confidence}
        self.key_type_processors = {"ip": validate_ip_address}

    def run(self):
        while True:
            # listen for messages from the go part

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
                # TODO: lower reputation
                print("Invalid command: ", data)
                continue

            if command == "go_data":
                self.process_go_data(parameters)
                continue

            print("Invalid command: ", data)

    def process_go_data(self, parameters):
        """Process the report received from remote peer

        The report is expected to have the format explained in go_report_format.md. If the message is valid, it is
        inserted into the database. If it does not comply with the format, the reporter's reputation is lowered."""

        # check that the data was parsed correctly in the go part of the app
        # if there were any issues, the reports list will be empty
        reports = validate_go_reports(parameters)
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

        try:
            message_type = data["message_type"]
        except KeyError:
            # TODO: lower reputation
            print("Peer didn't specify message type")
            return

        if message_type == "report":
            self.process_message_report(reporter, report_time, data)

        elif message_type == "request":
            self.process_message_request(reporter, report_time, data)

        elif message_type == "blame":
            print("blame is not implemented yet")

        else:
            # TODO: lower reputation
            print("Peer sent unknown message type")
            return

    def process_message_request(self, reporter, report_time, data):
        # validate keys in message
        try:
            key = data["key"]
            key_type = data["key_type"]
            evaluation_type = data["evaluation_type"]
        except KeyError:
            print("Correct keys are missing in the message")
            # TODO: lower reputation
            return

        # validate keytype and key
        if key_type != "ip":
            print("Module can't process given key type")
            return

        if not self.key_type_processors[key_type](key):
            print("Provided key isn't a valid value for it's type")
            # TODO: lower reputation
            return

        # validate evaluation type
        if evaluation_type != "score_confidence":
            print("Module can't process given evaluation type")
            return

        score, confidence = get_ip_info_from_slips(self.rdb, key)
        if score is not None:
            send_evaluation_to_go(self.rdb, key, score, confidence, reporter)

    def process_message_report(self, reporter, report_time, data):
        # validate keys in message
        try:
            key = data["key"]
            key_type = data["key_type"]
            evaluation_type = data["evaluation_type"]
            evaluation = data["evaluation"]
        except KeyError:
            print("Correct keys are missing in the message")
            # TODO: lower reputation
            return

        # validate keytype and key
        if key_type not in self.key_type_processors:
            print("Module can't process given key type")
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

        self.trustdb.insert_new_go_report(reporter, key_type, key, score, confidence, report_time)
        result = "Data processing ok: reporter {}, report time {}, key {} ({}), score {}, confidence {}".format(
            reporter, report_time, key, key_type, score, confidence)
        print(result)
        pass




