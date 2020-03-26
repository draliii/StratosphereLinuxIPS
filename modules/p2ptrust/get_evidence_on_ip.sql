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