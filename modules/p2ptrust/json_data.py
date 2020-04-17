# data for testing message parsing. It is important to know that the json is sent by the go part of the code, so it is
# not likely to be malicious. The message base64 part, however, comes from another peer and should be handled with care


# one correct report (OK)
# message: {"key_type": "ip", "key": "1.2.3.40", "evaluation_type": "score_confidence",
#           "evaluation": { "score": 0.9, "confidence": 0.6 }}
one_correct = '[{' \
              '    "reporter": "abcsakughroiauqrghaui",' \
              '    "report_time": 154900000,' \
              '    "message": "eyJrZXlfdHlwZSI6ICJpcCIsICJrZXkiOiAiMS4yLjMuNDAiLCAiZXZhbHVhdGlvbl90eXBlIjogInNjb3JlX2' \
              'NvbmZpZGVuY2UiLCAiZXZhbHVhdGlvbiI6IHsgInNjb3JlIjogMC45LCAiY29uZmlkZW5jZSI6IDAuNiB9fQ=="' \
              '  }]'

# multiple correct reports (OK)
two_correct = '[{' \
              '    "reporter": "abcsakughroiauqrghaui",' \
              '    "report_time": 154900000,' \
              '    "message": "eyJrZXlfdHlwZSI6ICJpcCIsICJrZXkiOiAiMS4yLjMuNDAiLCAiZXZhbHVhdGlvbl90eXBlIjogInNjb3JlX2' \
              'NvbmZpZGVuY2UiLCAiZXZhbHVhdGlvbiI6IHsgInNjb3JlIjogMC45LCAiY29uZmlkZW5jZSI6IDAuNiB9fQ=="' \
              '  },{' \
              '    "reporter": "anotherreporterspeerid",' \
              '    "report_time": 154800000,' \
              '    "message": "eyJrZXlfdHlwZSI6ICJpcCIsICJrZXkiOiAiMS4yLjMuNSIsICJldmFsdWF0aW9uX3R5cGUiOiAic2NvcmVfY2' \
              '9uZmlkZW5jZSIsICJldmFsdWF0aW9uIjogeyAic2NvcmUiOiAwLjksICJjb25maWRlbmNlIjogMC43IH19"' \
              '  }]'

# invalid json (fail on parsing)
invalid_json1 = '[}'
invalid_json2 = '{"key_type": "ip", "key": "1.2.3.40", "evaluation_type": "score_confidence"'
invalid_json3 = '{"key_type": "ip", "key": "1.2.3.40", "evaluation_type": "score_confidence}'

# json isn't a list
not_a_list = '{' \
             '    "reporter": "abcsakughroiauqrghaui",' \
             '    "report_time": 154900000,' \
             '    "message": "eyJrZXlfdHlwZSI6ICJpcCIsICJrZXkiOiAiMS4yLjMuNDAiLCAiZXZhbHVhdGlvbl90eXBlIjogInNjb3JlX2N' \
             'vbmZpZGVuY2UiLCAiZXZhbHVhdGlvbiI6IHsgInNjb3JlIjogMC45LCAiY29uZmlkZW5jZSI6IDAuNiB9fQ=="' \
             '  }'

# json is an empty list
empty_list = '[]'

# valid json with missing fields (fail on validating json)
missing_fields = '[{' \
                 '    "reporter": "abcsakughroiauqrghaui",' \
                 '    "message": "eyJrZXlfdHlwZSI6ICJpcCIsICJrZXkiOiAiMS4yLjMuNDAiLCAiZXZhbHVhdGlvbl90eXBlIjogInNjb3J' \
                 'lX2NvbmZpZGVuY2UiLCAiZXZhbHVhdGlvbiI6IHsgInNjb3JlIjogMC45LCAiY29uZmlkZW5jZSI6IDAuNiB9fQ=="' \
                 '  }]'

# valid json with other fields (OK)
too_many_fields = '[{' \
                  '    "reporter": "abcsakughroiauqrghaui",' \
                  '    "some_other_key": "a useless value",' \
                  '    "report_time": 154900000,' \
                  '    "message": "eyJrZXlfdHlwZSI6ICJpcCIsICJrZXkiOiAiMS4yLjMuNDAiLCAiZXZhbHVhdGlvbl90eXBlIjogInNjb3' \
                  'JlX2NvbmZpZGVuY2UiLCAiZXZhbHVhdGlvbiI6IHsgInNjb3JlIjogMC45LCAiY29uZmlkZW5jZSI6IDAuNiB9fQ=="' \
                  '  }]'

# valid json, time wrong
wrong_time_string = '[{' \
              '    "reporter": "abcsakughroiauqrghaui",' \
              '    "report_time": "just_now",' \
              '    "message": "eyJrZXlfdHlwZSI6ICJpcCIsICJrZXkiOiAiMS4yLjMuNDAiLCAiZXZhbHVhdGlvbl90eXBlIjogInNjb3JlX2' \
              'NvbmZpZGVuY2UiLCAiZXZhbHVhdGlvbiI6IHsgInNjb3JlIjogMC45LCAiY29uZmlkZW5jZSI6IDAuNiB9fQ=="' \
              '  }]'
wrong_time_empty_string = '[{' \
              '    "reporter": "abcsakughroiauqrghaui",' \
              '    "report_time": "",' \
              '    "message": "eyJrZXlfdHlwZSI6ICJpcCIsICJrZXkiOiAiMS4yLjMuNDAiLCAiZXZhbHVhdGlvbl90eXBlIjogInNjb3JlX2' \
              'NvbmZpZGVuY2UiLCAiZXZhbHVhdGlvbiI6IHsgInNjb3JlIjogMC45LCAiY29uZmlkZW5jZSI6IDAuNiB9fQ=="' \
              '  }]'
wrong_time_negative = '[{' \
              '    "reporter": "abcsakughroiauqrghaui",' \
              '    "report_time": -3,' \
              '    "message": "eyJrZXlfdHlwZSI6ICJpcCIsICJrZXkiOiAiMS4yLjMuNDAiLCAiZXZhbHVhdGlvbl90eXBlIjogInNjb3JlX2' \
              'NvbmZpZGVuY2UiLCAiZXZhbHVhdGlvbiI6IHsgInNjb3JlIjogMC45LCAiY29uZmlkZW5jZSI6IDAuNiB9fQ=="' \
              '  }]'
wrong_time_float = '[{' \
              '    "reporter": "abcsakughroiauqrghaui",' \
              '    "report_time": 2.5,' \
              '    "message": "eyJrZXlfdHlwZSI6ICJpcCIsICJrZXkiOiAiMS4yLjMuNDAiLCAiZXZhbHVhdGlvbl90eXBlIjogInNjb3JlX2' \
              'NvbmZpZGVuY2UiLCAiZXZhbHVhdGlvbiI6IHsgInNjb3JlIjogMC45LCAiY29uZmlkZW5jZSI6IDAuNiB9fQ=="' \
              '  }]'
wrong_time_future = '[{' \
              '    "reporter": "abcsakughroiauqrghaui",' \
              '    "report_time": 2587122908,' \
              '    "message": "eyJrZXlfdHlwZSI6ICJpcCIsICJrZXkiOiAiMS4yLjMuNDAiLCAiZXZhbHVhdGlvbl90eXBlIjogInNjb3JlX2' \
              'NvbmZpZGVuY2UiLCAiZXZhbHVhdGlvbiI6IHsgInNjb3JlIjogMC45LCAiY29uZmlkZW5jZSI6IDAuNiB9fQ=="' \
              '  }]'


# message has unknown type


# message can't be read as base 64 (fail in message interpretation)


# message can't be parsed as json


# message doesn't have v1 fields (fail in message interpretation)


# v1 fields have wrong type (fail in message interpretation)


# reported IP address is not an IP address


# reported score / confidence are out of the interval <0, 1>
