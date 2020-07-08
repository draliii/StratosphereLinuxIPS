import sqlite3
import datetime
import time

from p2ptrust.utils.printer import Printer


class TrustDB:
    def __init__(self, db_file: str, printer: Printer, drop_tables_on_startup: bool = False):
        """ create a database connection to a SQLite database """

        self.printer = printer

        print(db_file)
        self.conn = sqlite3.connect(db_file)
        if drop_tables_on_startup:
            self.print("Dropping tables")
            self.delete_tables()

        self.create_tables()
        # self.insert_slips_score("8.8.8.8", 0.0, 0.9)
        # self.get_opinion_on_ip("zzz")

    def __del__(self):
        self.conn.close()

    def print(self, text: str, verbose: int = 1, debug: int = 0) -> None:
        self.printer.print("[TrustDB] " + text, verbose, debug)

    def create_tables(self):
        self.conn.execute("CREATE TABLE IF NOT EXISTS slips_reputation ("
                          "id INTEGER PRIMARY KEY NOT NULL, "
                          "ipaddress TEXT NOT NULL, "
                          "score REAL NOT NULL, "
                          "confidence REAL NOT NULL, "
                          "update_time REAL NOT NULL);")

        self.conn.execute("CREATE TABLE IF NOT EXISTS go_reliability ("
                          "id INTEGER PRIMARY KEY NOT NULL, "
                          "peerid TEXT NOT NULL, "
                          "reliability REAL NOT NULL, "
                          "update_time REAL NOT NULL);")

        self.conn.execute("CREATE TABLE IF NOT EXISTS peer_ips ("
                          "id INTEGER PRIMARY KEY NOT NULL, "
                          "ipaddress TEXT NOT NULL, "
                          "peerid TEXT NOT NULL, "
                          "update_time REAL NOT NULL);")

        self.conn.execute("CREATE TABLE IF NOT EXISTS reports ("
                          "id INTEGER PRIMARY KEY NOT NULL, "
                          "reporter_peerid TEXT NOT NULL, "
                          "key_type TEXT NOT NULL, "
                          "reported_key TEXT NOT NULL, "
                          "score REAL NOT NULL, "
                          "confidence REAL NOT NULL, "
                          "update_time REAL NOT NULL);")

        self.conn.execute("CREATE TABLE IF NOT EXISTS opinion_cache ("
                          "key_type TEXT NOT NULL, "
                          "reported_key TEXT NOT NULL PRIMARY KEY, "
                          "score REAL NOT NULL, "
                          "confidence REAL NOT NULL, "
                          "network_score REAL NOT NULL, "
                          "update_time DATE NOT NULL);")

    def delete_tables(self):
        self.conn.execute("DROP TABLE IF EXISTS opinion_cache;")
        self.conn.execute("DROP TABLE IF EXISTS slips_reputation;")
        self.conn.execute("DROP TABLE IF EXISTS go_reliability;")
        self.conn.execute("DROP TABLE IF EXISTS peer_ips;")
        self.conn.execute("DROP TABLE IF EXISTS reports;")

    def insert_slips_score(self, ip: str, score: float, confidence: float, timestamp: int = None):
        if timestamp is None:
            timestamp = time.time()
        else:
            k = 3
        timestamp = time.time()
        print("###################3Slips score timeout: ", timestamp)
        parameters = (ip, score, confidence, timestamp)
        self.conn.execute("INSERT INTO slips_reputation (ipaddress, score, confidence, update_time) "
                          "VALUES (?, ?, ?, ?);", parameters)
        self.conn.commit()

    def insert_go_score(self, peerid: str, reliability: float, timestamp: int = None):
        if timestamp is None:
            timestamp = datetime.datetime.now()
        else:
            k = 3
        timestamp = time.time()
        print("#####################Go score timeout: ", timestamp)
        parameters = (peerid, reliability, timestamp)
        self.conn.execute("INSERT INTO go_reliability (peerid, reliability, update_time) "
                          "VALUES (?, ?, ?);", parameters)
        self.conn.commit()

    def insert_go_ip_pairing(self, peerid: str, ip: str, timestamp: int = None):
        if timestamp is None:
            timestamp = datetime.datetime.now()
        timestamp = time.time()

        parameters = (ip, peerid, timestamp)
        self.conn.execute("INSERT INTO peer_ips (ipaddress, peerid, update_time) "
                          "VALUES (?, ?, ?);", parameters)
        self.conn.commit()

    def insert_new_go_data(self, reports: list):
        self.conn.executemany("INSERT INTO reports "
                              "(reporter_peerid, key_type, reported_key, score, confidence, update_time) "
                              "VALUES (?, ?, ?, ?, ?, ?)", reports)
        self.conn.commit()
        pass

    def insert_new_go_report(self, reporter_peerid: str, key_type: str, reported_key: str, score: float,
                             confidence: float, timestamp: int = None):
        if timestamp is None:
            timestamp = datetime.datetime.now()
        timestamp = time.time()

        parameters = (reporter_peerid, key_type, reported_key, score, confidence, timestamp)
        self.conn.execute("INSERT INTO reports "
                          "(reporter_peerid, key_type, reported_key, score, confidence, update_time) "
                          "VALUES (?, ?, ?, ?, ?, ?)", parameters)
        self.conn.commit()
        pass

    def update_cached_network_opinion(self, key_type: str, reported_key: str, score: float, confidence: float,
                                      network_score: float):
        self.conn.execute("REPLACE INTO"
                          " opinion_cache (key_type, reported_key, score, confidence, network_score, update_time)"
                          "VALUES (?, ?, ?, ?, ?, strftime('%s','now'));",
                          (key_type, reported_key, score, confidence, network_score))
        self.conn.commit()

    def get_cached_network_opinion(self, key_type: str, reported_key: str):
        cache_cur = self.conn.execute("SELECT score, confidence, network_score, update_time "
                                      "FROM opinion_cache "
                                      "WHERE key_type = ? "
                                      "  AND reported_key = ? "
                                      "ORDER BY update_time LIMIT 1;", (key_type, reported_key))

        result = cache_cur.fetchone()
        if result is None:
            result = None, None, None, None
        return result

    def get_opinion_on_ip(self, ipaddress: str):
        reports_cur = self.conn.execute("SELECT reports.reporter_peerid AS reporter_peerid,"
                                        "       MAX(reports.update_time) AS report_timestamp,"
                                        "       reports.score AS report_score,"
                                        "       reports.confidence AS report_confidence,"
                                        "       reports.reported_key AS reported_ip "
                                        "FROM reports "
                                        "WHERE reports.reported_key = ?"
                                        "       AND reports.key_type = 'ip' "
                                        "GROUP BY reports.reporter_peerid;", (ipaddress,))

        reporters_scores = []

        # iterate over all peers that reported the ip
        for reporter_peerid, report_timestamp, report_score, report_confidence, reported_ip in reports_cur.fetchall():

            # get the ip address the reporting peer had when doing the report
            ip_cur = self.conn.execute("SELECT MAX(update_time) AS ip_update_time, ipaddress "
                                       "FROM peer_ips "
                                       "WHERE update_time <= ? AND peerid = ?;", (report_timestamp, reporter_peerid))
            _, reporter_ipaddress = ip_cur.fetchone()
            # TODO: handle empty response

            # prevent peers from reporting about themselves
            if reporter_ipaddress == ipaddress:
                continue

            # get the most recent score and confidence for the given IP-peerID pair
            parameters_dict = {"peerid": reporter_peerid, "ipaddress": reporter_ipaddress}
            slips_reputation_cur = self.conn.execute("SELECT * FROM (  "
                                                     "    SELECT b.update_time AS lower_bound,  "
                                                     "           COALESCE( "
                                                     "              MIN(lj.min_update_time), strftime('%s','now')"
                                                     "           ) AS upper_bound,  "
                                                     "           b.ipaddress AS ipaddress,  "
                                                     "           b.peerid AS peerid  "
                                                     "    FROM peer_ips b  "
                                                     "        LEFT JOIN(  "
                                                     "            SELECT a.update_time AS min_update_time  "
                                                     "            FROM peer_ips a  "
                                                     "            WHERE a.peerid = :peerid OR a.ipaddress = :ipaddress "
                                                     "            ORDER BY min_update_time  "
                                                     "            ) lj  "
                                                     "            ON lj.min_update_time > b.update_time  "
                                                     "    WHERE b.peerid = :peerid AND b.ipaddress = :ipaddress  "
                                                     "    GROUP BY lower_bound  "
                                                     "    ORDER BY lower_bound DESC  "
                                                     "    ) x  "
                                                     "LEFT JOIN slips_reputation sr USING (ipaddress)  "
                                                     "WHERE sr.update_time <= x.upper_bound AND "
                                                     "      sr.update_time >= x.lower_bound  "
                                                     "ORDER BY sr.update_time DESC  "
                                                     "LIMIT 1  "
                                                     ";", parameters_dict)
            data = slips_reputation_cur.fetchone()
            if data is None:
                self.print("No slips reputation data for " + str(parameters_dict))
                continue

            go_reliability_cur = self.conn.execute("SELECT reliability FROM main.go_reliability WHERE peerid = ? ORDER BY update_time DESC LIMIT 1;", (reporter_peerid, ))
            reliability = go_reliability_cur.fetchone()
            if reliability is None:
                self.print("No reliability for ", reporter_peerid)
                continue
            reliability = reliability[0]

            _, _, _, _, _, reporter_score, reporter_confidence, reputation_update_time = data
            reporters_scores.append((report_score, report_confidence, reliability, reporter_score, reporter_confidence))

        return reporters_scores


if __name__ == '__main__':
    trustDB = TrustDB(r"trustdb.db")