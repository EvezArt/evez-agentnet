#!/usr/bin/env python3
"""Presentation watermarking for EVEZ Pocket.

The canonical artifact is hashed before any presentation watermark is added.
Watermarks are presentation metadata, not part of the canonical evidence bytes.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass


DOMAIN = b"EVEZ/OFFLINE/PRESENTATION/v1\0"
DEVICE = os.environ.get("EVEZ_DEVICE_LABEL", "EVEZ-POCKET")


@dataclass(frozen=True)
class Watermark:
    watermark_id: str
    artifact_hash: str
    created_unix: int
    source: str = "LOCAL"
    device: str = DEVICE

    def text(self) -> str:
        return (
            f"EVEZ POCKET | {self.device} | {self.source}\n"
            f"artifact:{self.artifact_hash[:16]} | wm:{self.watermark_id}"
        )


def canonical_bytes(content: str) -> bytes:
    payload = {"content": content}
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def artifact_hash(content: str) -> str:
    return hashlib.sha256(DOMAIN + canonical_bytes(content)).hexdigest()


def make_watermark(content: str) -> Watermark:
    return Watermark(
        watermark_id=uuid.uuid4().hex[:12],
        artifact_hash=artifact_hash(content),
        created_unix=int(time.time()),
    )


def present(content: str) -> tuple[str, dict[str, object]]:
    wm = make_watermark(content)
    metadata = {
        "watermark_id": wm.watermark_id,
        "artifact_hash": wm.artifact_hash,
        "created_unix": wm.created_unix,
        "source": wm.source,
        "device": wm.device,
        "association": "PRESENTATION_ONLY",
    }
    return content + "\n\n" + wm.text(), metadata
