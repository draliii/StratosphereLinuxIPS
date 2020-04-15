# data for testing message parsing. It is important to know that the json is sent by the go part of the code, so it is
# not likely to be malicious. The message base64 part, however, comes from another peer and should be handled with care

# TODO: replace message with valid data
[
  {
    "reporter": "abcsakughroiauqrghaui",
    "version": "v1",
    "report_time": 154900000,
    "message": "ewogICAgImtleV90eXBlIjogImlwIiwKICAgICJrZXkiOiAiMS4yLjMuNDAiLAogICAgImV........jYKfQ=="
  },
  {
    "reporter": "efghkughroiauqrghxyz",
    "version": "v1",
    "report_time": 1567000300,
    "message": "ewogICAgImtleV90eXBlIjogImlwIiwKICAgICJrZXkiOiAiMS4yLjMuNDAiLAogICAgImV........jYKfQ=="
  }
]

# one correct report (OK)


# multiple correct reports (OK)


# invalid json (fail on parsing)


# valid json with missing fields (fail on validating json)


# valid json with other fields (OK)


# valid json, time is string (fail on reading values from json)


# message has unknown type


# message can't be read as base 64 (fail in message interpretation)


# message can't be parsed as json


# message doesn't have v1 fields (fail in message interpretation)


# v1 fields have wrong type (fail in message interpretation)


# reported IP address is not an IP address


# reported score / confidence are out of the interval <0, 1>