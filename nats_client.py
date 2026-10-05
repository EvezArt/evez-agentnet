#!/usr/bin/env python3
"""Minimal stdlib NATS wire-protocol client.

No external deps: python3.14 has no pip, and the box has no nats CLI.
Speaks just enough of the NATS protocol for the delta substrate:
CONNECT, PING/PONG, SUB, PUB (with optional reply-to), MSG parsing.
"""

import json
import secrets
import socket


class NatsError(Exception):
    pass


class NatsClient:
    def __init__(self, host="127.0.0.1", port=4222, name="evez-delta", timeout=10.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.buf = b""
        self.name = name
        self._next_sid = 100  # request() sids start above caller-chosen ones (e.g. 1)
        info = self._read_line()
        if not info.startswith("INFO "):
            raise NatsError(f"expected INFO, got: {info[:64]}")
        self._send("CONNECT " + json.dumps({
            "verbose": False, "pedantic": False, "tls_required": False,
            "name": name, "lang": "py", "version": "1.0.0",
        }) + "\r\n")
        self._send("PING\r\n")
        pong = self._read_line()
        if pong.strip() != "PONG":
            raise NatsError(f"handshake failed, got: {pong[:64]}")

    def _send(self, s: str):
        self.sock.sendall(s.encode())

    def _fill(self):
        chunk = self.sock.recv(65536)
        if not chunk:
            raise NatsError("connection closed")
        self.buf += chunk

    def _read_line(self) -> str:
        while b"\r\n" not in self.buf:
            self._fill()
        line, self.buf = self.buf.split(b"\r\n", 1)
        return line.decode("utf-8", "replace")

    def _read_exact(self, n: int) -> bytes:
        while len(self.buf) < n:
            self._fill()
        data, self.buf = self.buf[:n], self.buf[n:]
        return data

    def sub(self, subject: str, sid: int):
        self._send(f"SUB {subject} {sid}\r\n")

    def publish(self, subject: str, payload: bytes, reply_to: str = ""):
        head = f"PUB {subject} {reply_to} {len(payload)}\r\n" if reply_to else f"PUB {subject} {len(payload)}\r\n"
        self.sock.sendall(head.encode() + payload + b"\r\n")

    def next_msg(self, timeout=10.0):
        """Return (subject, reply_to, payload) for the next MSG; None on timeout of PING keepalive."""
        self.sock.settimeout(timeout)
        while True:
            try:
                line = self._read_line()
            except socket.timeout:
                return None
            if line.startswith("MSG "):
                parts = line.split(" ")
                # MSG <subject> <sid> [reply-to] <#bytes>
                if len(parts) == 4:
                    subject, _sid, n = parts[1], parts[2], int(parts[3])
                    reply = ""
                elif len(parts) == 5:
                    subject, _sid, reply, n = parts[1], parts[2], parts[3], int(parts[4])
                else:
                    raise NatsError(f"bad MSG frame: {line[:80]}")
                payload = self._read_exact(n + 2)[:-2]
                return subject, reply, payload
            if line.strip() == "PING":
                self._send("PONG\r\n")
                continue
            if line.startswith("-ERR"):
                raise NatsError(line)

    def request(self, subject: str, payload: bytes, timeout=10.0):
        """Publish with an inbox reply subject; wait for the first reply MSG.

        Each request uses a FRESH inbox AND a fresh sid. Reusing a sid for a
        second SUB makes the server drop the mapping, so every request after
        the first on a connection would silently time out.
        """
        inbox = "_INBOX." + secrets.token_hex(8)
        sid = self._next_sid
        self._next_sid += 1
        self.sub(inbox, sid)
        self.publish(subject, payload, reply_to=inbox)
        while True:
            msg = self.next_msg(timeout=timeout)
            if msg is None:
                raise NatsError(f"request timeout on {subject}")
            _s, _r, body = msg
            if _s == inbox:
                return json.loads(body.decode("utf-8"))

    def close(self):
        try:
            self._send("PING\r\n")
        except Exception:
            pass
        self.sock.close()
