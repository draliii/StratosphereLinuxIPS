import ipaddress
import time
import json


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


def get_ip_info_from_slips(rdb, ip_address):
    # poll new info from redis
    ip_info = rdb.getIPData(ip_address)

    slips_score, slips_confidence = read_data_from_ip_info(ip_info)
    # check that both values were provided
    if slips_score is None:
        return None, None

    return slips_score, slips_confidence


def read_data_from_ip_info(ip_info: dict) -> (float, float):
    try:
        score = ip_info["score"]
        confidence = ip_info["confidence"]
        return float(score), float(confidence)
    except KeyError:
        return None, None