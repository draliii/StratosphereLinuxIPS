SELECT reports.reporter_peerid AS peerid,
       MAX(reports.update_time) AS report_updated,
       reports.score AS report_score,
       reports.confidence AS report_confidence,
       reports.reported_key AS reported_ip,
       pi.reporter_ip AS reporter_ip,
       pi.go_updated AS go_updated,
       pi.slips_score AS reporter_slips_score,
       pi.slips_confidence AS reporter_slips_confidence,
       pi.slips_updated AS reporter_slips_updated
FROM reports
    LEFT JOIN (
        SELECT peer_ips.peerid,
               MAX(peer_ips.update_time) AS go_updated,
               peer_ips.ipaddress AS reporter_ip,
               sr.slips_updated AS slips_updated,
               sr.slips_score AS slips_score,
               sr.slips_confidence AS slips_confidence
        FROM peer_ips
            LEFT JOIN (
                SELECT slips_reputation.ipaddress,
                       MAX(slips_reputation.update_time) AS slips_updated,
                       slips_reputation.score AS slips_score,
                       slips_reputation.confidence AS slips_confidence
                FROM slips_reputation
                GROUP BY slips_reputation.ipaddress
            ) sr
            ON peer_ips.ipaddress=sr.ipaddress
        GROUP BY peer_ips.peerid
    ) pi
    ON reports.reporter_peerid=pi.peerid
WHERE reports.reported_key = 'xxx' AND reports.key_type = 'ip' GROUP BY reports.reporter_peerid;

-- I have the timestamp, IP and peerID. I want to find all intervals, where this IP belongs to the peerID
SELECT b.update_time AS lower_bound,
       COALESCE(MIN(lj.min_update_time), strftime('%s','now')) AS upper_bound,
       b.ipaddress AS ipaddress,
       b.peerid AS peerid
FROM peer_ips b
    LEFT JOIN(
        SELECT a.update_time AS min_update_time
        FROM peer_ips a
        WHERE a.peerid = ? OR a.ipaddress = ?
        ORDER BY min_update_time
        ) lj
        ON lj.min_update_time > b.update_time
WHERE b.peerid = ? AND b.ipaddress = ?
GROUP BY lower_bound
ORDER BY lower_bound DESC
;

-- an attempt to modify the previous query to also check slips reputation and get the newest one
SELECT b.update_time AS lower_bound,
       COALESCE(MIN(lj.min_update_time), strftime('%s','now')) AS upper_bound,
       b.ipaddress AS ipaddress,
       b.peerid AS peerid,
       sr.score,
       sr.confidence,
       sr.slips_update_time AS slips_update_time
FROM peer_ips b
    LEFT JOIN(
        SELECT a.update_time AS min_update_time
        FROM peer_ips a
        WHERE a.peerid = ? OR a.ipaddress = ?
        ORDER BY min_update_time
        ) lj
        ON lj.min_update_time > b.update_time
    LEFT JOIN (
        SELECT s.confidence AS confidence,
               s.score AS score,
               s.update_time AS slips_update_time,
               s.ipaddress AS slips_ip_address
        FROM slips_reputation s
    ) sr on b.ipaddress = sr.slips_ip_address
WHERE b.peerid = ? AND b.ipaddress = ? AND sr.slips_update_time >= lower_bound
GROUP BY lower_bound
-- HAVING slips_update_time < upper_bound
-- ORDER BY slips_update_time
;

-- this works:
SELECT * FROM (
    SELECT b.update_time AS lower_bound,
           COALESCE(MIN(lj.min_update_time), strftime('%s','now')) AS upper_bound,
           b.ipaddress AS ipaddress,
           b.peerid AS peerid
    FROM peer_ips b
        LEFT JOIN(
            SELECT a.update_time AS min_update_time
            FROM peer_ips a
            WHERE a.peerid = :peerid OR a.ipaddress = :ipaddress
            ORDER BY min_update_time
            ) lj
            ON lj.min_update_time > b.update_time
    WHERE b.peerid = :peerid AND b.ipaddress = :ipaddress
    GROUP BY lower_bound
    ORDER BY lower_bound DESC
    ) x
LEFT JOIN slips_reputation sr USING (ipaddress)
WHERE sr.update_time < x.upper_bound AND sr.update_time >= x.lower_bound
ORDER BY sr.update_time DESC
LIMIT 1
;


-- insert opinion if there is none. If it exists, then update it
REPLACE INTO opinion_cache
    (key_type, reported_key, score, confidence, network_score, update_time)
     VALUES
            (?, ?, ?, ?, ?, strftime('%s','now'));