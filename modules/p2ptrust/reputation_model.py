import multiprocessing
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

    def run(self):
        while True:
            # listen for messages from the go part
            # TODO: figure out what to do with Slips request for data
            #       - Slips wants to know about an IP
            # TODO: handle errors here

            message = self.rdb_channel.get_message(timeout=None)
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
        # TODO: parse data from parameters
        #       multiple messages may be aggreagated here, all reporting the same IP
        ip, reporter_peerid, score, confidence = "2.3.4.5", "abiuarhogrqerghorggr", 0.1, 0.3
        # TODO: save data to sqlite db

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
