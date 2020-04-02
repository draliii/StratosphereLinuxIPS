import multiprocessing
from statistics import mean

from modules.p2ptrust.trustdb import TrustDB


class ReputationModel(multiprocessing.Process):
    # this should be made into an interface
    def __init__(self, trustdb: TrustDB, redis_database, config):
        super().__init__()
        self.trustdb = trustdb
        self.rdb = redis_database
        self.config = config
        self.rdb_channel = self.rdb.r.pubsub()
        self.rdb_channel.subscribe('p2p_gopy')

    def run(self):
        while True:
            message = self.rdb_channel.get_message(timeout=None)
            print("RM:", message)

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
