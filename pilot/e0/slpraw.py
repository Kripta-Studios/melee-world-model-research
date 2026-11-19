"""Lector mínimo e independiente del flujo de eventos de un .slp (SPEC slippi-wiki 3a85ce8b).

Se usa para: (a) filtrar dittos en streaming sin escribir el archivo a disco, (b) extraer campos que
peppi-py 0.8.6 no expone (C-stick crudo, PreFrame 0x41/0x42, 3.17.0+; latest_finalized_frame), y
(c) contrastar a peppi byte a byte en los tests.

Solo depende de numpy. Todas las posiciones son relativas al byte de comando del evento, como en el SPEC.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

import numpy as np

CMD_PAYLOADS = 0x35
CMD_GAME_START = 0x36
CMD_PRE = 0x37
CMD_POST = 0x38
CMD_GAME_END = 0x39
CMD_FRAME_START = 0x3A
CMD_ITEM = 0x3B
CMD_BOOKEND = 0x3C
CMD_SPLITTER = 0x10

EXT_FOX = 2  # ID externo de personaje (SPEC "Melee IDs"); Fox interno = 1
RAW_HEADER = b"U\x03raw[$U#l"


class SlpError(Exception):
    pass


@dataclass
class Header:
    version: tuple
    stage: int
    ext_chars: list          # por puerto 0..3
    player_types: list       # 0 humano, 1 CPU, 2 demo, 3 vacío
    stocks: list
    is_teams: bool
    random_seed: int
    major_scene: int | None
    payload_sizes: dict = field(repr=False, default_factory=dict)


def raw_bounds(data: bytes) -> tuple[int, int]:
    """Devuelve (inicio, fin) del array `raw`. Si la longitud declarada es 0 (archivo en curso), usa todo."""
    i = data.find(RAW_HEADER, 0, 64)
    if i < 0:
        raise SlpError("no_raw_header")
    (n,) = struct.unpack_from(">I", data, i + len(RAW_HEADER))
    start = i + len(RAW_HEADER) + 4
    end = start + n if n else len(data)
    if end > len(data):
        raise SlpError("truncated_raw")
    return start, end


def parse_payload_sizes(data: bytes, start: int) -> tuple[dict, int]:
    if data[start] != CMD_PAYLOADS:
        raise SlpError("no_event_payloads")
    size = data[start + 1]
    sizes = {CMD_PAYLOADS: size}
    for j in range(start + 2, start + 1 + size, 3):
        sizes[data[j]] = struct.unpack_from(">H", data, j + 1)[0]
    return sizes, start + 1 + size


def parse_header(data: bytes) -> tuple[Header, int]:
    """Lee Event Payloads + Game Start. Devuelve la cabecera y el offset del siguiente evento."""
    start, _ = raw_bounds(data)
    sizes, i = parse_payload_sizes(data, start)
    if data[i] != CMD_GAME_START:
        raise SlpError("no_game_start")
    gs = i
    gsize = sizes[CMD_GAME_START]
    version = tuple(data[gs + 1: gs + 4])
    gib = gs + 5
    stage = struct.unpack_from(">H", data, gib + 0xE)[0]
    ext_chars = [data[gib + 0x60 + 0x24 * p] for p in range(4)]
    ptypes = [data[gib + 0x61 + 0x24 * p] for p in range(4)]
    stocks = [data[gib + 0x62 + 0x24 * p] for p in range(4)]
    is_teams = bool(data[gib + 0x8])
    seed = struct.unpack_from(">I", data, gs + 0x13D)[0]
    major = data[gs + 0x1A4] if 0x1A4 < 1 + gsize else None
    h = Header(version, stage, ext_chars, ptypes, stocks, is_teams, seed, major, sizes)
    return h, gs + 1 + gsize


@dataclass
class EventIndex:
    header: Header
    offsets: dict            # cmd -> np.ndarray de offsets absolutos del byte de comando
    game_end_method: int | None
    lras_initiator: int | None
    end_offset: int          # dónde terminó el recorrido (para detectar truncado)


def index_events(data: bytes) -> EventIndex:
    h, i = parse_header(data)
    _, end = raw_bounds(data)
    sizes = h.payload_sizes
    offs = {CMD_PRE: [], CMD_POST: [], CMD_FRAME_START: [], CMD_BOOKEND: [], CMD_ITEM: []}
    gem = lras = None
    while i < end:
        cmd = data[i]
        s = sizes.get(cmd)
        if s is None:
            raise SlpError(f"unknown_cmd_0x{cmd:02x}")
        lst = offs.get(cmd)
        if lst is not None:
            lst.append(i)
        elif cmd == CMD_GAME_END:
            gem = data[i + 1]
            if s >= 2:
                lras = struct.unpack_from(">b", data, i + 2)[0]
        i += 1 + s
    return EventIndex(h, {k: np.asarray(v, dtype=np.int64) for k, v in offs.items()}, gem, lras, i)


def field_present(h: Header, cmd: int, offset: int, nbytes: int) -> bool:
    return offset + nbytes <= 1 + h.payload_sizes.get(cmd, 0)


def gather(data: bytes, offsets: np.ndarray, offset: int, dtype: str) -> np.ndarray:
    """Lee un campo big-endian en `offsets + offset` de forma vectorizada."""
    dt = np.dtype(dtype).newbyteorder(">")
    buf = np.frombuffer(data, dtype=np.uint8)
    idx = offsets[:, None] + offset + np.arange(dt.itemsize)[None, :]
    return buf[idx].copy().view(dt).reshape(-1).astype(dt.newbyteorder("="))


def frame_port_keys(data: bytes, offsets: np.ndarray):
    """(frame, puerto, follower) de eventos Pre/Post."""
    return (gather(data, offsets, 0x1, "i4"), gather(data, offsets, 0x5, "u1"),
            gather(data, offsets, 0x6, "u1"))


def last_copy_index(frames: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Índices de la ÚLTIMA aparición de cada frame (orden de frame ascendente) y nº de copias por frame."""
    n = len(frames)
    uniq, idx_rev, counts = np.unique(frames[::-1], return_index=True, return_counts=True)
    last = (n - 1 - idx_rev).astype(np.int64)  # primera aparición en el array invertido = última real
    return uniq, last, counts
