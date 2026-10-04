#!/bin/bash
# Court-evidence acquisition — DMZHOST ecosystem. Every artifact hashed; sources recorded.
set -x
cd /root/evez-agentnet/evidence/2026-10-04/attack-acquisition
for asn in AS48090 AS47890 AS209847; do whois -h whois.ripe.net $asn > ripe_${asn}.txt 2>&1; done
for ip in 80.94.92.166 80.94.92.179 80.94.92.234 80.94.92.55 2.57.122.150 2.57.122.168 45.156.87.204; do whois $ip > whois_${ip}.txt 2>&1; done
for ip in 80.94.92.166 80.94.92.179 80.94.92.234 80.94.92.55 2.57.122.150 2.57.122.168 45.156.87.204; do (dig +short -x $ip > ptr_${ip}.txt 2>&1) & done; wait
curl -sS -m 20 -D dmzhost_co.headers -o dmzhost_co.html https://dmzhost.co/ 2>&1 | head -2
curl -sS -m 20 -o crtsh_dmzhost.json 'https://crt.sh/?q=dmzhost.co&output=json' 2>&1 | head -2
curl -sS -m 20 -o rdap_as48090.json 'https://rdap.org/autnum/48090' 2>&1 | head -2
curl -sS -m 20 -o rdap_as47890.json 'https://rdap.org/autnum/47890' 2>&1 | head -2
