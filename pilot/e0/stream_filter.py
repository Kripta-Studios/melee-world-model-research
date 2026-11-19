"""Descarga en streaming tarballs de erickfm/melee-ranked-replays y guarda SOLO los dittos Fox-Fox válidos.

El tarball nunca toca el disco: se lee el flujo HTTP con tarfile en modo 'r|gz' y cada miembro .slp se
clasifica en memoria con slpraw (sin peppi). Solo los aceptados se escriben en --out-dir.

Uso:
  python -I stream_filter.py --tarball FOX/FOX_diamond-diamond_a1.tar.gz [--tarball ...] \
      --out-dir /srv/mail/melee-research-data/slp --manifest evidence/E0/stream_manifest.jsonl \
      --summary evidence/E0/stream_summary.json [--max-stream-bytes 50000000]
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
import sys
import tarfile
import time
import urllib.request
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np  # noqa: E402
import slpraw  # noqa: E402

REPO = "erickfm/melee-ranked-replays"
REV = "ef54ddc230e01373ff2a179b49a7e559af788081"
MIN_LAST_FRAME = 1500  # frames de juego (post cuenta atrás); umbral de HAL selection.json


def mem_available_mb() -> int:
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) // 1024
    return 10**6


class ResumingReader:
    """Lector HTTP que cuenta bytes y, si la conexión se corta, reabre con `Range: bytes=n-` y sigue.
    Para tarfile/gzip el flujo es continuo: nada del tarball se escribe a disco."""

    def __init__(self, url, limit=None, max_retries=20, timeout=60):
        self.url, self.limit, self.max_retries, self.timeout = url, limit, max_retries, timeout
        self.n, self.retries, self.errors = 0, 0, []
        self.resp = self._open()
        cl = self.resp.headers.get("Content-Length")
        self.total = int(cl) if cl else None

    def _open(self):
        h = {"User-Agent": "research-data-client/0.1"}
        if self.n:
            h["Range"] = f"bytes={self.n}-"
        resp = urllib.request.urlopen(urllib.request.Request(self.url, headers=h), timeout=self.timeout)
        if self.n and resp.status != 206:
            raise OSError(f"range not honoured (status {resp.status})")
        return resp

    def read(self, size=-1):
        if self.limit is not None and self.n >= self.limit:
            return b""
        while True:
            try:
                b = self.resp.read(size)
                if not b and size != 0 and self.total is not None and self.n < self.total:
                    raise OSError("premature EOF")
                break
            except (OSError, http.client.HTTPException) as e:
                self.errors.append(f"{self.n}:{type(e).__name__}:{e}"[:160])
                self.retries += 1
                if self.retries > self.max_retries:
                    raise
                try:
                    self.resp.close()
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(min(60, 5 * self.retries))
                try:
                    self.resp = self._open()
                except (OSError, http.client.HTTPException) as e2:
                    self.errors.append(f"{self.n}:reopen:{type(e2).__name__}:{e2}"[:160])
        self.n += len(b)
        return b

    def close(self):
        self.resp.close()


def classify(data: bytes) -> dict:
    """Devuelve info de la partida y `reason` (None si se acepta)."""
    info = {"reason": None}
    try:
        h, _ = slpraw.parse_header(data)
    except Exception as e:  # noqa: BLE001
        info["reason"] = f"parse_error:{type(e).__name__}:{e}"[:120]
        return info
    present = [p for p in range(4) if h.player_types[p] != 3]
    info.update(version=".".join(map(str, h.version)), stage=h.stage, ports=present,
                ext_chars=[h.ext_chars[p] for p in present], start_seed=h.random_seed,
                major_scene=h.major_scene)
    if len(present) != 2:
        info["reason"] = "not_2_players"
    elif any(h.player_types[p] != 0 for p in present):
        info["reason"] = "non_human_player"
    elif h.is_teams:
        info["reason"] = "teams"
    elif not all(h.ext_chars[p] == slpraw.EXT_FOX for p in present):
        info["reason"] = "not_fox_ditto"
    if info["reason"]:
        return info
    # Solo para dittos: recorrer el flujo de eventos completo.
    try:
        ev = slpraw.index_events(data)
    except Exception as e:  # noqa: BLE001
        info["reason"] = f"event_error:{type(e).__name__}:{e}"[:120]
        return info
    pre = ev.offsets[slpraw.CMD_PRE]
    if len(pre) == 0:
        info["reason"] = "no_frames"
        return info
    fr, port, fol = slpraw.frame_port_keys(data, pre)
    uniq = np.unique(fr)
    info.update(first_frame=int(uniq[0]), last_frame=int(uniq[-1]), n_unique_frames=int(len(uniq)),
                n_pre_events=int(len(pre)), end_method=ev.game_end_method, lras=ev.lras_initiator)
    if set(np.unique(port).tolist()) != set(present):
        info["reason"] = "port_mismatch"
    elif fol.any():
        info["reason"] = "has_follower"
    elif ev.game_end_method is None:
        info["reason"] = "no_game_end"
    elif ev.game_end_method == 7:
        info["reason"] = "no_contest"
    elif ev.game_end_method not in (1, 2):
        info["reason"] = f"end_method_{ev.game_end_method}"
    elif uniq[-1] < MIN_LAST_FRAME:
        info["reason"] = "too_short"
    elif len(uniq) != uniq[-1] - uniq[0] + 1 or uniq[0] != -123:
        info["reason"] = "non_contiguous_frames"
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tarball", action="append", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--max-accepted", type=int, default=300)
    ap.add_argument("--max-saved-bytes", type=int, default=1_000_000_000)
    ap.add_argument("--max-stream-bytes", type=int, default=6_000_000_000, help="total entre tarballs")
    ap.add_argument("--dry-run", action="store_true", help="no escribe .slp (prueba del parser)")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    reasons, n_acc, saved, streamed = Counter(), 0, 0, 0
    seen_sha = set()
    t0 = time.time()
    per_tar = []
    stop = None
    with open(a.manifest, "a") as mf:
        for tb in a.tarball:
            url = f"https://huggingface.co/datasets/{REPO}/resolve/{REV}/{tb}"
            cr = ResumingReader(url, limit=a.max_stream_bytes - streamed)
            n_members = 0
            complete = False
            try:
                with tarfile.open(fileobj=cr, mode="r|gz") as tf:
                    for m in tf:
                        if not m.isfile():
                            continue
                        n_members += 1
                        name = m.name
                        if not name.endswith(".slp"):
                            reasons["not_slp"] += 1
                            continue
                        data = tf.extractfile(m).read()
                        sha1 = hashlib.sha1(data).hexdigest()
                        info = classify(data)
                        if info["reason"] is None and sha1 in seen_sha:
                            info["reason"] = "duplicate_sha1"
                        rec = {"tarball": tb, "member": name, "sha1": sha1, "bytes": len(data), **info}
                        if info["reason"] is None:
                            seen_sha.add(sha1)
                            n_acc += 1
                            saved += len(data)
                            if not a.dry_run:
                                dst = os.path.join(a.out_dir, sha1 + ".slp")
                                with open(dst + ".part", "wb") as f:
                                    f.write(data)
                                os.replace(dst + ".part", dst)
                            rec["saved_as"] = sha1 + ".slp"
                            reasons["accepted"] += 1
                        else:
                            reasons[info["reason"].split(":")[0]] += 1
                        mf.write(json.dumps(rec) + "\n")
                        if n_members % 200 == 0:
                            mf.flush()
                            for _ in range(10):  # pausa breve si el servidor va justo de RAM
                                if mem_available_mb() >= 300:
                                    break
                                reasons["mem_pause_30s"] += 1
                                time.sleep(30)
                            print(f"[{time.time()-t0:7.0f}s] {tb} members={n_members} "
                                  f"streamed={(streamed+cr.n)/1e6:.0f}MB accepted={n_acc} "
                                  f"saved={saved/1e6:.0f}MB", flush=True)
                        if n_acc >= a.max_accepted:
                            stop = "max_accepted"
                            break
                        if saved >= a.max_saved_bytes:
                            stop = "max_saved_bytes"
                            break
                    else:
                        complete = cr.limit is None or cr.n < cr.limit
            except (tarfile.ReadError, EOFError, OSError) as e:
                # corte por límite de bytes (gzip truncado) o red tras agotar reintentos
                reasons[f"stream_cut:{type(e).__name__}"] += 1
                cr.errors.append(f"final:{type(e).__name__}:{e}"[:160])
            finally:
                cr.close()
            streamed += cr.n
            per_tar.append({"tarball": tb, "url": url, "members_seen": n_members,
                            "bytes_streamed": cr.n, "read_to_end": complete,
                            "http_retries": cr.retries, "http_errors": cr.errors[-30:]})
            if stop:
                break
            if streamed >= a.max_stream_bytes:
                stop = "max_stream_bytes"
                break
    summary = {"repo": REPO, "revision": REV, "tarballs": per_tar, "stop_reason": stop or "tarballs_exhausted",
               "accepted": n_acc, "saved_bytes": saved, "bytes_streamed_total": streamed,
               "reason_counts": dict(reasons), "elapsed_s": round(time.time() - t0, 1),
               "min_last_frame": MIN_LAST_FRAME, "dry_run": a.dry_run}
    with open(a.summary, "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
