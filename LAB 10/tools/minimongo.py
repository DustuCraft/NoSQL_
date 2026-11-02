"""Minimal MongoDB wire-protocol client (OP_MSG) with BSON codec.

Used because mongosh / mongodump are not installed on the lab machine and the
environment has no network access to download them.  Supports the subset of
commands needed for Lab 10: hello, rs.initiate/status, insert, find, count,
aggregate, createIndexes, listDatabases, drop.
"""
import socket
import struct
import os
import datetime as _dt
import json


class ObjectId:
    __slots__ = ("oid",)

    def __init__(self, oid=None):
        self.oid = oid or os.urandom(12)

    def __str__(self):
        return self.oid.hex()

    def __repr__(self):
        return "ObjectId('%s')" % self.oid.hex()

    def __eq__(self, other):
        return isinstance(other, ObjectId) and other.oid == self.oid


class Timestamp:
    __slots__ = ("t", "i")

    def __init__(self, t, i):
        self.t, self.i = t, i

    def __repr__(self):
        return "Timestamp(%d, %d)" % (self.t, self.i)


class Int64(int):
    pass


def _cstring(s):
    return s.encode("utf-8") + b"\x00"


def _encode_value(v):
    if isinstance(v, bool):
        return 0x08, b"\x01" if v else b"\x00"
    if isinstance(v, ObjectId):
        return 0x07, v.oid
    if isinstance(v, Int64):
        return 0x12, struct.pack("<q", int(v))
    if isinstance(v, int):
        if -2**31 <= v < 2**31:
            return 0x10, struct.pack("<i", v)
        return 0x12, struct.pack("<q", v)
    if isinstance(v, float):
        return 0x01, struct.pack("<d", v)
    if isinstance(v, str):
        b = v.encode("utf-8")
        return 0x02, struct.pack("<i", len(b) + 1) + b + b"\x00"
    if isinstance(v, dict):
        return 0x03, _encode_doc(v)
    if isinstance(v, (list, tuple)):
        return 0x04, _encode_array(v)
    if isinstance(v, bytes):
        return 0x05, struct.pack("<i", len(v)) + b"\x00" + v
    if isinstance(v, _dt.datetime):
        ms = int(v.timestamp() * 1000)
        return 0x09, struct.pack("<q", ms)
    if v is None:
        return 0x0A, b""
    raise TypeError("cannot BSON-encode %r" % (v,))


def _encode_doc(d):
    body = b""
    for k, v in d.items():
        t, payload = _encode_value(v)
        body += bytes([t]) + _cstring(k) + payload
    return struct.pack("<i", len(body) + 5) + body + b"\x00"


def _encode_array(a):
    return _encode_doc({str(i): v for i, v in enumerate(a)})


class _Reader:
    def __init__(self, data):
        self.d = data
        self.p = 0

    def read(self, n):
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def cstring(self):
        e = self.d.index(b"\x00", self.p)
        s = self.d[self.p:e].decode("utf-8")
        self.p = e + 1
        return s

    def doc(self):
        start = self.p
        size = struct.unpack("<i", self.read(4))[0]
        end = start + size
        out = {}
        while self.p < end - 1:
            t = self.d[self.p]
            self.p += 1
            k = self.cstring()
            out[k] = self.value(t)
        self.p = end
        return out

    def array(self):
        start = self.p
        size = struct.unpack("<i", self.read(4))[0]
        end = start + size
        out = []
        while self.p < end - 1:
            t = self.d[self.p]
            self.p += 1
            self.cstring()
            out.append(self.value(t))
        self.p = end
        return out

    def value(self, t):
        if t == 0x01:
            return struct.unpack("<d", self.read(8))[0]
        if t == 0x02:
            n = struct.unpack("<i", self.read(4))[0]
            s = self.read(n - 1).decode("utf-8", "replace")
            self.read(1)
            return s
        if t == 0x03:
            return self.doc()
        if t == 0x04:
            return self.array()
        if t == 0x05:
            n = struct.unpack("<i", self.read(4))[0]
            sub = self.read(1)[0]
            return {"$binary": self.read(n).hex(), "subType": "%02x" % sub}
        if t == 0x07:
            return ObjectId(self.read(12))
        if t == 0x08:
            return self.read(1)[0] == 1
        if t == 0x09:
            ms = struct.unpack("<q", self.read(8))[0]
            return _dt.datetime.fromtimestamp(ms / 1000.0, _dt.timezone.utc)
        if t == 0x0A:
            return None
        if t == 0x10:
            return struct.unpack("<i", self.read(4))[0]
        if t == 0x11:
            i, tt = struct.unpack("<II", self.read(8))
            return Timestamp(tt, i)
        if t == 0x12:
            return struct.unpack("<q", self.read(8))[0]
        if t == 0x13:
            return {"$decimal": self.read(16).hex()}
        if t == 0xFF:
            return {"$minKey": 1}
        if t == 0x7F:
            return {"$maxKey": 1}
        raise ValueError("unsupported BSON type 0x%02x at %d" % (t, self.p))


def decode(data):
    return _Reader(data).doc()


def _to_jsonable(o):
    if isinstance(o, ObjectId):
        return str(o)
    if isinstance(o, Timestamp):
        return {"$timestamp": {"t": o.t, "i": o.i}}
    if isinstance(o, _dt.datetime):
        return o.astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    if isinstance(o, dict):
        return {k: _to_jsonable(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_to_jsonable(v) for v in o]
    return o


class MongoError(Exception):
    def __init__(self, doc):
        self.doc = doc
        self.code = doc.get("code")
        super().__init__("%s (code %s)" % (doc.get("errmsg"), doc.get("code")))


class Client:
    def __init__(self, host="127.0.0.1", port=27101, timeout=15):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        self.req = 0

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

    def command(self, db, cmd, check=True, timeout=None):
        if timeout:
            self.sock.settimeout(timeout)
        body = dict(cmd)
        body.setdefault("$db", db)
        payload = b"\x00\x00\x00\x00" + b"\x00" + _encode_doc(body)
        self.req += 1
        header = struct.pack("<iiii", 16 + len(payload), self.req, 0, 2013)
        self.sock.sendall(header + payload)

        hdr = self._recv_exact(16)
        length, _rid, _resp, opcode = struct.unpack("<iiii", hdr)
        data = self._recv_exact(length - 16)
        if opcode != 2013:
            raise RuntimeError("unexpected opcode %d" % opcode)
        flags = struct.unpack("<I", data[:4])[0]
        pos = 4
        doc = None
        while pos < len(data):
            kind = data[pos]
            pos += 1
            if kind == 0:
                r = _Reader(data[pos:])
                doc = r.doc()
                pos += struct.unpack("<i", data[pos:pos + 4])[0]
            elif kind == 1:
                secsize = struct.unpack("<i", data[pos:pos + 4])[0]
                pos += secsize
            else:
                break
        if doc is None:
            raise RuntimeError("empty reply")
        if check and doc.get("ok") != 1:
            raise MongoError(doc)
        return doc

    def _recv_exact(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("connection closed")
            buf += chunk
        return buf


def run_sequence(host, port, steps):
    """steps: list of (db, cmd). Returns list of results (jsonable) and errors."""
    results = []
    with Client(host, port) as c:
        for db, cmd in steps:
            try:
                r = c.command(db, cmd)
                results.append({"ok": 1, "result": _to_jsonable(r)})
            except MongoError as e:
                results.append({"ok": 0, "error": _to_jsonable(e.doc)})
            except (ConnectionError, OSError) as e:
                results.append({"ok": 0, "error": {"errmsg": str(e)}})
                break
    return results


def dumps(o, **kw):
    return json.dumps(_to_jsonable(o), ensure_ascii=False, indent=2, default=str, **kw)
