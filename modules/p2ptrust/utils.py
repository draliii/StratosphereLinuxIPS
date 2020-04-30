import base64
import ipaddress
import time
import json


#
# DATA VALIDATION METHODS
#


def validate_ip_address(ip):
    try:
        # this fails on invalid ip address
        ipaddress.ip_address(ip)
    except:
        return False

    return True


def validate_timestamp(timestamp):
    try:
        # originally, I wanted to accept only strict ints, not flaots. But for unix, it doesn't even matter. Also, the
        # int() function turns it into int, so any floating point stuff is removed.
        int_timestamp = int(timestamp)
    except:
        print("Timestamp is not a number")
        return False

    if int_timestamp > time.time() or int_timestamp < 0:
        print("Invalid timestamp value")
        return False

    return True


def validate_go_reports(parameters: str) -> list:
    # try parsing the json error. If this fails, there is an error in the redis channel or in go code, not the
    # remote peers
    try:
        reports = json.loads(parameters)
    except:
        # TODO: specify json error
        print("Go send invalid json")
        return []

    if type(reports) != list:
        print("Expected list, got something else")
        return []

    return reports


#
# READ DATA FROM REDIS
#

def get_ip_info_from_slips(rdb, ip_address):
    # poll new info from redis
    ip_info = rdb.getIPData(ip_address)

    slips_score, slips_confidence = read_data_from_ip_info(ip_info)
    # check that both values were provided
    if slips_score is None:
        return None, None

    return slips_score, slips_confidence


# parse data from redis
def read_data_from_ip_info(ip_info: dict) -> (float, float):
    try:
        score = ip_info["score"]
        confidence = ip_info["confidence"]
        return float(score), float(confidence)
    except KeyError:
        return None, None


#
# SEND COMMUNICATION TO GO
#


def send_evaluation_to_go(rdb, ip, score, confidence, recipient):
    message_raw = {}
    message_raw["message_type"] = "report"
    message_raw["key_type"] = "ip"
    message_raw["key"] = ip
    message_raw["evaluation_type"] = "score_confidence"
    message_raw["evaluation"] = {}
    message_raw["evaluation"]["score"] = score
    message_raw["evaluation"]["confidence"] = confidence

    message_json = json.dumps(message_raw)
    message_b64 = base64.b64encode(bytes(message_json, "ascii")).decode()

    send_b64_to_go(rdb, message_b64, recipient)


def send_b64_to_go(rdb, message, recipient):
    data_raw = {"message": message, "recipient": recipient}
    data_json = json.dumps(data_raw)
    print("[publish trust -> go]", data_json)
    rdb.publish("p2p_pygo", data_json)
