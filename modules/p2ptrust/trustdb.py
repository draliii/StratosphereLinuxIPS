import sqlite3
import datetime


class TrustDB:
    def __init__(self, db_file):
        """ create a database connection to a SQLite database """
        self.conn = sqlite3.connect(db_file)
        # self.delete_tables()
        self.create_tables()
        # self.insert_slips_score("8.8.8.8", 0.0, 0.9)
        self.get_opinion_on_ip2("xxx")
        foo = self.conn.execute("SELECT * FROM slips_reputation")
        print(sqlite3.version)

    def __del__(self):
        self.conn.close()

    def create_tables(self):
        self.conn.execute("CREATE TABLE IF NOT EXISTS slips_reputation ("
                          "id INTEGER PRIMARY KEY NOT NULL, "
                          "ipaddress TEXT NOT NULL, "
                          "score REAL NOT NULL, "
                          "confidence REAL NOT NULL, "
                          "update_time REAL NOT NULL);")

        self.conn.execute("CREATE TABLE IF NOT EXISTS go_trust ("
                          "id INTEGER PRIMARY KEY NOT NULL, "
                          "peerid TEXT NOT NULL, "
                          "trust REAL NOT NULL, "
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

    def delete_tables(self):
        self.conn.execute("DROP TABLE IF EXISTS slips_reputation;")
        self.conn.execute("DROP TABLE IF EXISTS go_reputation;")
        self.conn.execute("DROP TABLE IF EXISTS peer_ips;")
        self.conn.execute("DROP TABLE IF EXISTS reports;")

    def insert_slips_score(self, ip: str, score: float, confidence: float):
        timestamp = datetime.datetime.now()
        parameters = (ip, score, confidence, timestamp)
        self.conn.execute("INSERT INTO slips_reputation (ipaddress, score, confidence, update_time) "
                          "VALUES (?, ?, ?, ?);", parameters)

    def insert_go_score(self, ip: str, trust: float):
        timestamp = datetime.datetime.now()
        parameters = (ip, trust, timestamp)
        self.conn.execute("INSERT INTO go_trust (peerid, trust, update_time) "
                          "VALUES (?, ?, ?);", parameters)

    def insert_new_go_data(self, reports):
        # TODO: validate reports, add timestamps
        self.conn.executemany("INSERT INTO reports "
                              "(reporter_peerid, key_type, reported_key, score, confidence, update_time) "
                              "VALUES (?, ?, ?, ?, ?, ?)", reports)
        pass

    def get_opinion_on_ip(self, ip_address):
        # select most recent reports from peers, and join those with most recent values on that peer from the go and
        # slips reputation storage

        # TODO: maybe use the closest values instead of the most recent ones? What about multiple ips for one peerid?

        # this query is saved separately in the get_evidence_on_ip.sql file
        cur = self.conn.execute("SELECT reports.reporter_peerid AS peerid, "
                                "       MAX(reports.update_time) AS report_updated, "
                                "       reports.score AS report_score, "
                                "       reports.confidence AS report_confidence, "
                                "       reports.reported_key AS reported_ip, "
                                "       pi.reporter_ip AS reporter_ip, "
                                "       pi.go_updated AS go_updated, "
                                "       pi.slips_score AS reporter_slips_score, "
                                "       pi.slips_confidence AS reporter_slips_confidence, "
                                "       pi.slips_updated AS reporter_slips_updated "
                                "FROM reports "
                                "    LEFT JOIN ( "
                                "        SELECT peer_ips.peerid, "
                                "               MAX(peer_ips.update_time) AS go_updated, "
                                "               peer_ips.ipaddress AS reporter_ip, "
                                "               sr.slips_updated AS slips_updated, "
                                "               sr.slips_score AS slips_score, "
                                "               sr.slips_confidence AS slips_confidence "
                                "        FROM peer_ips "
                                "            LEFT JOIN ( "
                                "                SELECT slips_reputation.ipaddress, "
                                "                       MAX(slips_reputation.update_time) AS slips_updated, "
                                "                       slips_reputation.score AS slips_score, "
                                "                       slips_reputation.confidence AS slips_confidence "
                                "                FROM slips_reputation "
                                "                GROUP BY slips_reputation.ipaddress "
                                "            ) sr "
                                "            ON peer_ips.ipaddress=sr.ipaddress "
                                "        GROUP BY peer_ips.peerid "
                                "    ) pi "
                                "    ON reports.reporter_peerid=pi.peerid "
                                "WHERE reports.reported_key = ? AND reports.key_type = 'ip' "
                                "GROUP BY reports.reporter_peerid; ",
                                (ip_address,))

        column_names = [desc_part[0] for desc_part in cur.description]
        print(column_names)
        print(cur.fetchall())
        pass

    def get_opinion_on_ip2(self, ipaddress):
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
                                                     "WHERE sr.update_time < x.upper_bound AND "
                                                     "      sr.update_time >= x.lower_bound  "
                                                     "ORDER BY sr.update_time DESC  "
                                                     "LIMIT 1  "
                                                     ";", parameters_dict)
            data = slips_reputation_cur.fetchone()
            if data is None:
                print("No slips reputation data for ", parameters_dict)
                continue
            _, _, _, _, _, reporter_score, reporter_confidence, reputation_update_time = data
            reporters_scores.append((report_score, report_confidence, reporter_score, reporter_confidence))
        print(reporters_scores)

    def get_opinion_on_peer(self, peerid):
        pass


if __name__ == '__main__':
    trustDB = TrustDB(r"trustdb.db")
