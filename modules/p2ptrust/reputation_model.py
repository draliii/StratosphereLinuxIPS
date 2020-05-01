import configparser
from statistics import mean

from modules.p2ptrust.trustdb import TrustDB


class ReputationModel:
    """Model for computing reputations of peers and IP addresses

    This class provides a set of methods that get data from the database and compute a reputation based on that. Methods
    from this class are requested by the main module process on behalf on SLIPS, when SLIPS wants to know the network's
    opinion on peer or IP address."""

    # this should be made into an interface, so different models can be easily switched.
    def __init__(self, trustdb: TrustDB, config: configparser.ConfigParser):
        # TODO: add proper OutputProcess printing
        self.trustdb = trustdb
        self.config = config

    def get_opinion_on_ip(self, ipaddr: str):
        # get report on that ip that is at most max_age old
        # if no such report is found:

        reports_on_ip = self.trustdb.get_opinion_on_ip(ipaddr)
        if len(reports_on_ip) == 0:
            return None, None, None
        network_score, combined_score, combined_confidence = self.assemble_peer_opinion(reports_on_ip)

        self.trustdb.update_cached_network_opinion("ip", ipaddr, combined_score, combined_confidence, network_score)
        return combined_score, combined_confidence, network_score

    def compute_peer_reputation(self, trust: float, score: float, confidence: float):
        return trust * score * confidence

    def normalize_peer_reputations(self, peers: list):
        rep_sum = sum(peers)
        w = 1/rep_sum

        rep_avg = mean(peers)

        # now the reputations will sum to 1
        weighted_reputations = [w*x for x in peers]
        return rep_sum, rep_avg, weighted_reputations

    def assemble_peer_opinion(self, data: list):
        reports = []
        reporters = []

        for peer_report in data:
            # TODO: the following line crashes
            report_score, report_confidence, reporter_trust, reporter_score, reporter_confidence = peer_report
            reports.append((report_score, report_confidence))
            reporters.append(self.compute_peer_reputation(reporter_trust, reporter_score, reporter_confidence))

        report_sum, report_avg, weighted_reporters = self.normalize_peer_reputations(reporters)

        combined_score = sum([r[0]*w for r, w, in zip(reports, weighted_reporters)])
        combined_confidence = sum([r[1]*w for r, w, in zip(reports, weighted_reporters)])

        network_score = report_avg

        return network_score, combined_score, combined_confidence
