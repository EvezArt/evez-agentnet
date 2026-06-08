#!/usr/bin/env python3
"""
honeypot/npc_classifier.py  —  EVEZ NPC Witness Classification Engine

Takes a raw signal (network probe or YT chat message) and returns
an NPC record with:
  - npc_class: the human-readable classification label
  - tier: clean | suspect | hostile | confirmed
  - evidence: list of indicators that triggered the classification
  - fingerprint: SHA-256 of the classifying attributes
  - last_seen: ISO timestamp

Classification taxonomy (OSINT/witness framework):
  SCANNER        — automated port/path scanner
  SCRAPER        — content harvesting bot  
  DISINFO_SHILL  — coordinated narrative pusher
  SPAM_BOT       — repetitive message spammer
  PROBE_AGENT    — targeted infrastructure probe
  LURK_WATCHER   — high-dwell silent observer
  DISCLOSURE_DENIER — pattern-matched counter-narrative actor
  UNCLASSIFIED   — signals present but below threshold
"""

import re
import json
import hashlib
import datetime
from typing import Optional


# ──────────────────────────────────────────
# CLASSIFICATION RULES
# ──────────────────────────────────────────

SCANNER_UA_PATTERNS = [
    r"nmap", r"masscan", r"zgrab", r"nuclei", r"sqlmap",
    r"nikto", r"dirsearch", r"gobuster", r"ffuf", r"wfuzz",
    r"python-requests", r"go-http-client", r"libwww-perl",
]

SCRAPER_PATH_PATTERNS = [
    r"/wp-admin", r"/phpmyadmin", r"/.env", r"/config", r"/admin",
    r"/api/v1", r"/graphql", r"/.git", r"/backup", r"/dump",
]

DISINFO_SHILL_PHRASES = [
    r"uap (is|are) fake", r"weather balloon", r"swamp gas",
    r"no evidence", r"conspiracy theory", r"debunked",
    r"just reflections", r"mass hysteria",
]

SPAM_BOT_INDICATORS = [
    r"click here", r"free .*(crypto|nft|eth|bitcoin)",
    r"dm me", r"check my profile", r"@everyone",
    r"follow (me|back)", r"giveaway",
]

PROBE_PATHS = [
    r"/fire/", r"/evez", r"/openclaw", r"/spine",
    r"/agentvault", r"/clawhub", r"/.well-known/evez",
]

DISCLOSURE_DENIER_PHRASES = [
    r"aaro (is|was) right", r"no (legitimate|credible) (uap|ufo)",
    r"pentagon confirmed (nothing|hoax)", r"misidentified",
    r"classified for (national security|safety)",
]


def _match_any(text: str, patterns: list[str]) -> list[str]:
    text_lower = text.lower()
    return [p for p in patterns if re.search(p, text_lower)]


# ──────────────────────────────────────────
# CLASSIFIER
# ──────────────────────────────────────────

class NPCClassifier:
    def classify(self, signal: dict) -> dict:
        evidence = []
        classes = []
        tier = "clean"

        if signal.get("source") == "network_probe":
            ua = signal.get("user_agent", "")
            path = signal.get("path", "")
            ip = signal.get("remote_addr", "")

            scanner_hits = _match_any(ua, SCANNER_UA_PATTERNS)
            if scanner_hits:
                evidence += [f"scanner_ua:{h}" for h in scanner_hits]
                classes.append("SCANNER")
                tier = "hostile"

            scraper_hits = _match_any(path, SCRAPER_PATH_PATTERNS)
            if scraper_hits:
                evidence += [f"scraper_path:{h}" for h in scraper_hits]
                classes.append("SCRAPER")
                tier = "hostile" if tier != "hostile" else tier

            probe_hits = _match_any(path, PROBE_PATHS)
            if probe_hits:
                evidence += [f"targeted_probe:{h}" for h in probe_hits]
                classes.append("PROBE_AGENT")
                tier = "hostile"

            # Blank UA on port 18666 = automated probe
            if not ua and path != "/":
                evidence.append("blank_ua_off_root")
                classes.append("PROBE_AGENT")
                tier = "suspect" if tier == "clean" else tier

            fingerprint_basis = f"{ip}:{ua}:{path}"

        elif signal.get("source") == "yt_chat":
            text = signal.get("text", "")
            author = signal.get("author", "")
            author_id = signal.get("author_id", "")

            disinfo_hits = _match_any(text, DISINFO_SHILL_PHRASES)
            if disinfo_hits:
                evidence += [f"disinfo:{h}" for h in disinfo_hits]
                classes.append("DISINFO_SHILL")
                tier = "suspect"

            spam_hits = _match_any(text, SPAM_BOT_INDICATORS)
            if spam_hits:
                evidence += [f"spam:{h}" for h in spam_hits]
                classes.append("SPAM_BOT")
                tier = "hostile" if len(spam_hits) >= 2 else "suspect"

            denier_hits = _match_any(text, DISCLOSURE_DENIER_PHRASES)
            if denier_hits:
                evidence += [f"denier:{h}" for h in denier_hits]
                classes.append("DISCLOSURE_DENIER")
                tier = "suspect"

            # High dwell with no messages = lurk watcher (tracked externally)
            fingerprint_basis = f"{author_id}:{author}"

        else:
            fingerprint_basis = json.dumps(signal, sort_keys=True)

        if not classes:
            if evidence:
                classes = ["UNCLASSIFIED"]
                tier = "suspect"
            # else tier stays "clean"

        fingerprint = hashlib.sha256(fingerprint_basis.encode()).hexdigest()[:16]

        return {
            "fingerprint": fingerprint,
            "npc_class": classes[0] if classes else "CLEAN",
            "all_classes": classes,
            "tier": tier,
            "evidence": evidence,
            "source": signal.get("source"),
            "identity": (
                signal.get("remote_addr") or
                signal.get("author_id") or
                signal.get("author") or
                "unknown"
            ),
            "display_name": (
                signal.get("author") or
                signal.get("remote_addr") or
                "unknown"
            ),
            "raw_signal_preview": str(signal)[:200],
            "last_seen": datetime.datetime.utcnow().isoformat() + "Z",
        }


if __name__ == "__main__":
    c = NPCClassifier()
    # Test probes
    tests = [
        {"source": "network_probe", "remote_addr": "1.2.3.4", "method": "GET",
         "path": "/.env", "user_agent": "python-requests/2.31.0", "host_header": "evez.art"},
        {"source": "yt_chat", "author": "TestUser", "author_id": "UC12345",
         "text": "UAP are fake, just weather balloons lol", "is_verified": False,
         "is_chat_moderator": False, "is_chat_sponsor": False, "published_at": "now"},
        {"source": "network_probe", "remote_addr": "5.6.7.8", "method": "GET",
         "path": "/fire/125", "user_agent": "", "host_header": ""},
    ]
    for t in tests:
        result = c.classify(t)
        print(json.dumps(result, indent=2))
