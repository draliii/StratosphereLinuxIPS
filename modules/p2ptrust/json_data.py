# data for testing message parsing. It is important to know that the json is sent by the go part of the code, so it is
# not likely to be malicious. The message base64 part, however, comes from another peer and should be handled with care



# one correct report (OK)
# message: {"key_type": "ip", "key": "1.2.3.40", "evaluation_type": "score_confidence", "evaluation": { "score": 0.9, "confidence": 0.6 }}
one_correct = '[{' \
'    "reporter": "abcsakughroiauqrghaui",' \
'    "report_time": 154900000,' \
'    "message": "eyJrZXlfdHlwZSI6ICJpcCIsICJrZXkiOiAiMS4yLjMuNDAiLCAiZXZhbHVhdGlvbl90eXBlIjogInNjb3JlX2NvbmZpZGVuY2UiLCAiZXZhbHVhdGlvbiI6IHsgInNjb3JlIjogMC45LCAiY29uZmlkZW5jZSI6IDAuNiB9fQ=="' \
'  }]'

# multiple correct reports (OK)
two_correct = '[{' \
'    "reporter": "abcsakughroiauqrghaui",' \
'    "report_time": 154900000,' \
'    "message": "eyJrZXlfdHlwZSI6ICJpcCIsICJrZXkiOiAiMS4yLjMuNDAiLCAiZXZhbHVhdGlvbl90eXBlIjogInNjb3JlX2NvbmZpZGVuY2UiLCAiZXZhbHVhdGlvbiI6IHsgInNjb3JlIjogMC45LCAiY29uZmlkZW5jZSI6IDAuNiB9fQ=="' \
'  },{' \
'    "reporter": "anotherreporterspeerid",' \
'    "report_time": 154800000,' \
'    "message": "eyJrZXlfdHlwZSI6ICJpcCIsICJrZXkiOiAiMS4yLjMuNSIsICJldmFsdWF0aW9uX3R5cGUiOiAic2NvcmVfY29uZmlkZW5jZSIsICJldmFsdWF0aW9uIjogeyAic2NvcmUiOiAwLjksICJjb25maWRlbmNlIjogMC43IH19"' \
'  }]'

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