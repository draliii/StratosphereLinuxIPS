import sqlite3
import datetime


class TrustDB:
    def __init__(self, db_file):
        """ create a database connection to a SQLite database """
        self.conn = sqlite3.connect(db_file)
        self.delete_tables()
        self.create_tables()
        self.insert_slips_score("8.8.8.8", 0.0, 0.9)
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
                          "update_time DATE NOT NULL);")

        self.conn.execute("CREATE TABLE IF NOT EXISTS go_reputation ("
                          "id INTEGER PRIMARY KEY NOT NULL, "
                          "peerid TEXT NOT NULL, "
                          "uptime REAL NOT NULL, "
                          "ping REAL NOT NULL, "
                          "update_time DATE NOT NULL);")

        self.conn.execute("CREATE TABLE IF NOT EXISTS peer_ips ("
                          "id INTEGER PRIMARY KEY NOT NULL, "
                          "ipaddress TEXT NOT NULL, "
                          "peerid TEXT NOT NULL, "
                          "update_time DATE NOT NULL);")

        self.conn.execute("CREATE TABLE IF NOT EXISTS reports ("
                          "id INTEGER PRIMARY KEY NOT NULL, "
                          "ipaddress TEXT NOT NULL, "
                          "peerid TEXT NOT NULL, "
                          "score REAL NOT NULL, "
                          "confidence REAL NOT NULL, "
                          "update_time DATE NOT NULL);")

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


if __name__ == '__main__':
    trustDB = TrustDB(r"trustdb.db")

