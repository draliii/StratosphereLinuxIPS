INSERT INTO slips_reputation (id, ipaddress, score, confidence, update_time) VALUES (0, 'aaa''s new ip', 0, 0.5, '1583280000000');
INSERT INTO slips_reputation (id, ipaddress, score, confidence, update_time) VALUES (1, 'aaa''s new ip', 0.1, 0.4, '1585267200000');
INSERT INTO slips_reputation (id, ipaddress, score, confidence, update_time) VALUES (2, 'C', 2, 44, '3');
INSERT INTO slips_reputation (id, ipaddress, score, confidence, update_time) VALUES (3, 'C', 3, 4, '7');
INSERT INTO slips_reputation (id, ipaddress, score, confidence, update_time) VALUES (4, 'C', 1, 1, '9');

INSERT INTO reports (id, reporter_peerid, key_type, reported_key, score, confidence, update_time) VALUES (0, 'aaa', 'ip', 'xxx', 2, 1, '1583971200000');
INSERT INTO reports (id, reporter_peerid, key_type, reported_key, score, confidence, update_time) VALUES (1, 'aaa', 'ip', 'yyy', 3, 5, '1584057600000');
INSERT INTO reports (id, reporter_peerid, key_type, reported_key, score, confidence, update_time) VALUES (2, 'bbb', 'ip', 'xxx', 5, 3, '1583539200000');
INSERT INTO reports (id, reporter_peerid, key_type, reported_key, score, confidence, update_time) VALUES (3, 'aaa', 'url', 'xxx', 6, 7, '1491955200000');
INSERT INTO reports (id, reporter_peerid, key_type, reported_key, score, confidence, update_time) VALUES (4, 'aaa', 'ip', 'xxx', 2, 2, '15712000000');
INSERT INTO reports (id, reporter_peerid, key_type, reported_key, score, confidence, update_time) VALUES (5, 'ccc', 'ip', 'xxx', 3, 54, '6');

INSERT INTO peer_ips (id, ipaddress, peerid, update_time) VALUES (0, 'aaa''s new ip', 'aaa', 1584403200000);
INSERT INTO peer_ips (id, ipaddress, peerid, update_time) VALUES (1, 'bbb''s ip', 'bbb', 1583712000000);
INSERT INTO peer_ips (id, ipaddress, peerid, update_time) VALUES (2, 'aaa''s new ip', 'aaa', 1425513600000);
INSERT INTO peer_ips (id, ipaddress, peerid, update_time) VALUES (3, 'C', 'ccc', 2);
INSERT INTO peer_ips (id, ipaddress, peerid, update_time) VALUES (4, 'CC', 'ccc', 4);
INSERT INTO peer_ips (id, ipaddress, peerid, update_time) VALUES (5, 'C', 'ccc', 6);
INSERT INTO peer_ips (id, ipaddress, peerid, update_time) VALUES (6, 'C', 'bbb', 8);
INSERT INTO peer_ips (id, ipaddress, peerid, update_time) VALUES (7, 'C', 'ccc', 10);
INSERT INTO peer_ips (id, ipaddress, peerid, update_time) VALUES (8, 'C', 'ccc', 12);

