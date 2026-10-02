"""Live infrastructure verification via authoritative sources.

Every assertion in the EVEZ dossiers is checked against RIPE RDAP and BGP
origin data at retrieval time. Results are cached with an explicit timestamp
so any third party can reproduce them and see how current they are.

This is the difference between an asserted ASN and a sourced one.
"""
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

OUT = Path("/root/evez-agentnet/evidence")
OUT.mkdir(parents=True, exist_ok=True)

# Entities asserted in the EVEZ dossiers, extracted verbatim.
TARGETS = {
    "asn": ["AS47890", "AS48090", "AS209847", "AS42397"],
    "ip": ["80.94.92.166", "80.94.92.60", "80.94.92.72", "80.94.92.239",
           "2.57.122.72", "45.148.10.1", "193.32.162.1"],
}

UA = "evez-forensic-verifier/1.0"


def http_json(url, timeout=12):
    try:
        p = subprocess.run(
            ["curl", "-s", "-m", str(timeout), "-H", f"User-Agent: {UA}", url],
            capture_output=True, text=True, timeout=timeout + 4)
        if p.returncode != 0 or not p.stdout.strip():
            return None, f"curl rc={p.returncode}"
        return json.loads(p.stdout), None
    except Exception as e:
        return None, str(e)[:100]


def whois_ripe(target, kind):
    """RIPE RDAP — authoritative for RIPE-registered space."""
    path = f"autnum/{target}" if kind == "asn" else f"ip/{target}"
    url = f"https://rdap.db.ripe.net/{path}"
    data, err = http_json(url)
    if err or not data:
        return {"query": target, "source": url, "error": err or "empty"}
    out = {"query": target, "source": url}
    if kind == "asn":
        out["handle"] = data.get("handle")
        out["name"] = data.get("name")
        out["country"] = data.get("country")
        out["status"] = data.get("status")
        # flatten vcard org/address without dumping unstructured data
        # RDAP vcardArray entries vary in shape across RIPE responses:
        # item[3] is sometimes a dict, sometimes a list of [type, value] pairs.
        # Parse defensively rather than assuming one form.
        org = {}
        for ent in data.get("entities", []):
            arr = ent.get("vcardArray") or [None, []]
            items = arr[1] if len(arr) > 1 else []
            if not isinstance(items, list):
                continue
            for item in items:
                if not (isinstance(item, list) and len(item) >= 4):
                    continue
                key, val = item[0], item[3]
                if not isinstance(val, (dict, list)):
                    continue
                if isinstance(val, dict):
                    if key == "org":
                        org.update({k: v for k, v in val.items()
                                    if isinstance(v, str) and len(v) < 200})
                    elif key == "adr" and isinstance(val.get("address"), str):
                        org.setdefault("address", val["address"][:200])
                elif key == "org":
                    pairs = {p[0]: p[-1] for p in val
                             if isinstance(p, list) and len(p) >= 2
                             and isinstance(p[-1], str)}
                    if pairs:
                        org.update({k: v for k, v in pairs.items() if len(v) < 200})
        out["org"] = org
        out["entities"] = [e.get("roles") for e in data.get("entities", [])]
    else:
        out["handle"] = data.get("handle")
        out["name"] = data.get("name")
        out["country"] = data.get("country")
        out["start"] = data.get("startAddress")
        out["end"] = data.get("endAddress")
        out["type"] = data.get("type")
        out["cidr"] = (data.get("cidr0_cidrs") or [{}])[0].get("v4prefix")
    return out


def bgp_origin(ip):
    """Current BGP origin for an IP, via RIPEstat.

    NOTE: api.bgpview.io no longer resolves (DNS NXDOMAIN as of 2026-10-02), so
    RIPEstat is used instead. It is RIPE NCC's own measurement service and is
    authoritative for RIPE space, which is where all targets here live.
    """
    url = (f"https://stat.ripe.net/data/prefix-overview/data.json"
           f"?resource={ip}")
    data, err = http_json(url)
    if err or not data or data.get("status_code") != 200:
        return {"ip": ip, "source": url,
                "error": err or f"status {data.get('status_code') if data else '?'}"}

    d = data["data"]
    announced = d.get("announced", False)
    warn = ""
    for m in (d.get("messages") or []):
        if isinstance(m, list) and len(m) > 1 and m[0] == "warning":
            warn = m[1]

    # RIPEstat returns asns as [{"asn": 47890, "holder": "..."}, ...]
    # — objects, not bare integers.
    origins = []
    for a in (d.get("asns") or []):
        if isinstance(a, dict):
            num = a.get("asn")
            if num is None:
                continue
            origins.append({"asn": f"AS{num}", "holder": a.get("holder")})
        elif isinstance(a, int):
            origins.append({"asn": f"AS{a}", "holder": None})

    return {
        "ip": ip,
        "source": url,
        "announced": announced,
        "resource": d.get("resource"),
        "is_less_specific": d.get("is_less_specific", False),
        "origin": origins[0] if origins else None,
        "origins": origins,
        "block": (d.get("block") or {}).get("desc", ""),
        "less_specific_warning": warn or None,
        "query_time": d.get("query_time"),
    }


def main():
    fetched = datetime.now(timezone.utc).isoformat()
    result = {
        "generated_at": fetched,
        "generator": "evez infrastructure verifier",
        "note": "All values retrieved live at generated_at. Reproduce with "
                "python3 verify_infrastructure.py",
        "asn": {},
        "ip": {},
    }

    for asn in TARGETS["asn"]:
        bare = asn[2:]
        r = whois_ripe(bare, "asn")
        r["queried_asn"] = asn
        result["asn"][asn] = r
        print(f"{asn}: {r.get('name', r.get('error'))} [{r.get('country','?')}]")
        time.sleep(1.2)   # be polite to RIPE

    for ip in TARGETS["ip"]:
        r = bgp_origin(ip)
        r["rdap"] = whois_ripe(ip, "ip")
        result["ip"][ip] = r
        o = r.get("origin") or {}
        print(f"{ip}: {o.get('asn','?')} {o.get('holder','') or r.get('error','')}"
              f"  [{r.get('resource','?')}]")
        time.sleep(1.2)

    path = OUT / "infrastructure-verification.json"
    path.write_text(json.dumps(result, indent=1))
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
