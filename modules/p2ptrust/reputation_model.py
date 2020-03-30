from statistics import mean


def compute_peer_reputation(trust, score, confidence):
    return trust * score * confidence


def normalize_peer_reputations(peers):
    rep_sum = sum(peers)
    w = 1/rep_sum

    rep_avg = mean(peers)

    # now the reputations will sum to 1
    weighted_reputations = [w*x for x in peers]
    return rep_sum, rep_avg, weighted_reputations


def assemble_peer_opinion(data):
    reports = []
    reporters = []

    for peer_report in data:
        report_score, report_confidence, reporter_trust, reporter_score, reporter_confidence = peer_report
        reports.append((report_score, report_confidence))
        reporters.append(compute_peer_reputation(reporter_trust, reporter_score, reporter_confidence))

    report_sum, report_avg, weighted_reporters = normalize_peer_reputations(reporters)

    combined_score = sum([r[0]*w for r, w, in zip(reports, weighted_reporters)])
    combined_confidence = sum([r[1]*w for r, w, in zip(reports, weighted_reporters)])

    network_score = report_avg

    return network_score, combined_score, combined_confidence
