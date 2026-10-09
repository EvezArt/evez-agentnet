"""evez-agentnet/generator/face_reader.py
===================================
On-device face detection for the generator / art reader.

Haar cascades (bundled with opencv-data at /usr/share/opencv4/haarcascades)
are the primary detector: fast, dependency-free, CPU-only, no network fetch.
The reader stays torch-free so the generator imports cleanly anywhere.

Deliverable: normalized facies JSON consumed by _generate_draft() when the
prediction carries a photo_path:
  {
    "faces":   [{index, x0, y0, w, h}],
    "corr":    {"dominant": {x0, y0, w, h, area, frame_area, ratio}},
    "weights": {"0": 1.0, "1": 0.5, ...}   # dominant face = 1.0
  }
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Optional

import cv2  # type: ignore

log = logging.getLogger("evez.generator.reader.facial")

# Cascade discovery: cv2.data first (full opencv), then /usr/share/opencv4
# (opencv-data package, the headless-wheel case), then a package-local copy.
_CANDIDATE_DIRS = []
if hasattr(cv2, "data"):
    _CANDIDATE_DIRS.append(Path(cv2.data.haarcascades))
_CANDIDATE_DIRS += [Path("/usr/share/opencv4/haarcascades"),
                    Path(__file__).parent / "haarcascades"]

_FRONTAL = _PROFILE = _EYE = None
for _d in _CANDIDATE_DIRS:
    if (_d / "haarcascade_frontalface_default.xml").exists():
        _FRONTAL = _d / "haarcascade_frontalface_default.xml"
        _PROFILE = _d / "haarcascade_frontalface_alt2.xml"
        _EYE = _d / "haarcascade_eye.xml"
        break

if _FRONTAL is None:
    log.warning("face_reader: no Haar cascade found in %s -- offline path only",
                [str(d) for d in _CANDIDATE_DIRS])


class FacialAnalyzer:
    """On-device face reader: Haar cascade -> normalized facies payload."""

    def __init__(self) -> None:
        if _FRONTAL is None:
            raise RuntimeError("no Haar cascade available; install opencv-data")
        self._frontal = cv2.CascadeClassifier(str(_FRONTAL))
        self._profile = cv2.CascadeClassifier(str(_PROFILE)) if _PROFILE else None
        self._eye = cv2.CascadeClassifier(str(_EYE)) if _EYE else None
        self._frame_h = self._frame_w = 0
        self._out: Optional[dict[str, Any]] = None

    @staticmethod
    def _detect(cascade: "cv2.CascadeClassifier", gray, scale: float,
                neighbors: int) -> list[dict[str, Any]]:
        rects = cascade.detectMultiScale(gray, scaleFactor=scale,
                                         minNeighbors=neighbors, minSize=(30, 30))
        return [{"x0": int(x), "y0": int(y), "w": int(w), "h": int(h)}
                for (x, y, w, h) in rects]

    def analyze_file(self, path: str | Path) -> dict[str, Any]:
        img = cv2.imread(str(path))
        if img is None:
            raise FileNotFoundError(path)
        self._frame_w, self._frame_h = img.shape[1], img.shape[0]

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self._detect(self._frontal, gray, scale=1.3, neighbors=5)
        if not faces and self._profile is not None:
            faces = self._detect(self._profile, gray, scale=1.2, neighbors=4)

        out: dict[str, Any] = {"faces": faces, "corr": {}, "weights": {}}
        if faces:
            sizes = [f["w"] * f["h"] for f in faces]
            ranked = sorted(range(len(sizes)), key=lambda i: sizes[i], reverse=True)
            for rank, idx in enumerate(ranked):
                out["faces"][idx]["index"] = idx
                out["weights"][str(idx)] = 1.0 / (1.0 + rank)
            dom = faces[ranked[0]]
            frame_area = self._frame_w * self._frame_h
            out["corr"]["dominant"] = {
                "x0": dom["x0"], "y0": dom["y0"], "w": dom["w"], "h": dom["h"],
                "area": dom["w"] * dom["h"], "frame_area": frame_area,
                "ratio": round(dom["w"] * dom["h"] / frame_area, 6),
            }
        self._out = out
        return out
