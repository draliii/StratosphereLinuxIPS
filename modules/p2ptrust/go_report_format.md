# Report format, forwarding reports

## Reports sent between nodes
Nodes send each other reports in base64, which contains a json object. The report always contains the key type 
(currently, on IP addresses are supported), and the key itself - this is the IP address the node is reporting about.
Then, the Evaluation object follows, this aims to allow for easier expansion later on. Nodes advertise the Evaluation
type with the type attribute, and they share the type when first making contact.

At the time of writing this, the only type is `score_confidence` and there are two values shared - score and confidence.

The nodes always report the key type - currently, only IP addresses are supported, nodes should drop any unknown key
types. A valid report can look like this:

```json
{
  "key_type": "ip",
  "key": "1.2.3.40",
  "evaluation": {
    "score": 0.9,
    "confidence": 0.6
  }
}
```

For easier transfer, the message is sent as base64 encoded string:
```
ewogICAgImtleV90eXBlIjogImlwIiwKICAgICJrZXkiOiAiMS........jYKfQ==
```

## Go layer
In the go layer, data is not unpacked. The received message is simply forwarded, with some additional information: the 
sender's peerid, the message type he claims to have, and the time the report was received (system time, unix)

A report processed by the go layer could look like this
```json
{
  "reporter": "abcsakughroiauqrghaui",
  "message_type": "score_confidence",
  "report_time": 154900000,
  "message": {
    "key_type": "ip",
    "key": "1.2.3.40",
    "evaluation": {
      "score": 0.9,
      "confidence": 0.6
    }
  }
}
```

Remember, that the message is really a base64 string, the go layer doesn't process the data at all (more on that later).
To simplify implementation, the message should always be an array (in this case, with only one element).

```json
[
  {
    "reporter": "abcsakughroiauqrghaui",
    "message_type": "score_confidence",
    "report_time": 154900000,
    "message": "ewogICAgImtleV90eXBlIjogImlwIiwKICAgICJrZXkiOiAiMS4yLjMuNDAiLAogICAgImV........jYKfQ=="
  }
]
```

## Multiple reports in one message
In some cases, more reports arrive to the go layer. They are sent in an array, where each element is one report as
described above. These are usually responses about a given IP (key) from the network, so the key in all of them is the
same. The go layer doesn't unpack the messages to find the key, because:

 * it makes things a lot easier in the go layer, if it doesn't have to unpack data
 * it makes the protocol a lot more versatile - the go layer doesn't need to understand data structure, it is just there
  to forward data
  
The upper layers should not rely on the key to be same in all reports. Message sent to the high level processor can look
like this:

```json
[
  {
    "reporter": "abcsakughroiauqrghaui",
    "message_type": "score_confidence",
    "report_time": 154900000,
    "message": "ewogICAgImtleV90eXBlIjogImlwIiwKICAgICJrZXkiOiAiMS4yLjMuNDAiLAogICAgImV........jYKfQ=="
  },
  {
    "reporter": "efghkughroiauqrghxyz",
    "message_type": "score_confidence",
    "report_time": 1567000300,
    "message": "ewogICAgImtleV90eXBlIjogImlwIiwKICAgICJrZXkiOiAiMS4yLjMuNDAiLAogICAgImV........jYKfQ=="
  }
]
```