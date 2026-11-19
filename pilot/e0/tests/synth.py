"""Generador de .slp sintéticos mínimos (conformes al SPEC en los offsets que usa slpraw)."""
import struct

SIZES = {0x36: 0x2F8, 0x37: 0x40, 0x38: 0x50, 0x39: 0x6, 0x3A: 0xC, 0x3C: 0x8}


def payloads():
    body = b"".join(bytes([c]) + struct.pack(">H", s) for c, s in SIZES.items())
    return bytes([0x35, len(body) + 1]) + body


def game_start(chars=(2, 2), types=(0, 0), stage=31, seed=12345, version=(3, 15, 0)):
    b = bytearray(1 + SIZES[0x36])
    b[0] = 0x36
    b[1:4] = bytes(version)
    gib = 5
    struct.pack_into(">H", b, gib + 0xE, stage)
    for p in range(4):
        b[gib + 0x60 + 0x24 * p] = chars[p] if p < len(chars) else 0
        b[gib + 0x61 + 0x24 * p] = types[p] if p < len(types) else 3
        b[gib + 0x62 + 0x24 * p] = 4
    struct.pack_into(">I", b, 0x13D, seed)
    b[0x1A4] = 8
    return bytes(b)


def pre(frame, port, joy_x=0.0, buttons=0, seed=0):
    b = bytearray(1 + SIZES[0x37])
    b[0] = 0x37
    struct.pack_into(">iBB", b, 1, frame, port, 0)
    struct.pack_into(">I", b, 0x7, seed)
    struct.pack_into(">f", b, 0x19, joy_x)
    struct.pack_into(">H", b, 0x31, buttons)
    return bytes(b)


def post(frame, port, action=14, x=0.0):
    b = bytearray(1 + SIZES[0x38])
    b[0] = 0x38
    struct.pack_into(">iBB", b, 1, frame, port, 0)
    b[7] = 1
    struct.pack_into(">H", b, 0x8, action)
    struct.pack_into(">f", b, 0xA, x)
    return bytes(b)


def frame_start(frame, seed):
    b = bytearray(1 + SIZES[0x3A])
    b[0] = 0x3A
    struct.pack_into(">iI", b, 1, frame, seed)
    return bytes(b)


def game_end(method=2):
    b = bytearray(1 + SIZES[0x39])
    b[0] = 0x39
    b[1] = method
    b[2] = 0xFF
    return bytes(b)


def build(frames, chars=(2, 2), end_method=2, rollback_at=(), marker=None):
    """frames: iterable de frame ids. rollback_at: frames que se emiten dos veces (la 2ª con x=+1000)."""
    ev = [payloads(), game_start(chars=chars)]
    order = []
    for f in frames:
        order.append((f, 0))
        if f in rollback_at:
            order.append((f, 1))
    for f, copy in order:
        ev.append(frame_start(f, 1000 + f + copy))
        for p in (0, 1):
            ev.append(pre(f, p, joy_x=0.5 if copy else 0.0, buttons=0x0100 * copy))
            ev.append(post(f, p, x=float(f) + 1000.0 * copy))
    if end_method is not None:
        ev.append(game_end(end_method))
    raw = b"".join(ev)
    return b"{U\x03raw[$U#l" + struct.pack(">I", len(raw)) + raw + b"U\x08metadata{}}"
