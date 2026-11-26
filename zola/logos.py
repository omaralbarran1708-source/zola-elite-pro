"""Logos de equipos, ligas, banderas y jugadores.

Las imágenes de API-Football no gastan cuota, pero la documentación pide
guardarlas de nuestro lado: se descargan una sola vez y quedan en la base de
datos (sobreviven a reinicios) y en disco. Si una imagen no se puede bajar se
genera un escudo con las iniciales, así nunca aparece una imagen rota.
"""
from __future__ import annotations

import base64
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from .store import get_store

CACHE_DIR = Path(__file__).resolve().parent.parent / "assets" / "logos"
_mem: dict[str, tuple[str, bytes]] = {}
_failed: set[str] = set()


def _initials(name: str) -> str:
    words = [w for w in re.split(r"[\s\-\.]+", name or "") if w and w.lower() not in {"fc", "cf", "sc", "de", "la", "el", "club", "ac"}]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:3]).upper()


def crest_bytes(name: str) -> bytes:
    h = int(hashlib.md5((name or "?").encode()).hexdigest(), 16)
    hue = h % 360
    c1, c2 = f"hsl({hue},65%,42%)", f"hsl({(hue + 35) % 360},70%,28%)"
    ini = _initials(name)
    size = 34 if len(ini) <= 2 else 27
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>
<defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='{c1}'/><stop offset='1' stop-color='{c2}'/></linearGradient></defs>
<path d='M50 4 L90 16 V48 C90 72 72 88 50 96 C28 88 10 72 10 48 V16 Z' fill='url(#g)' stroke='white' stroke-width='4'/>
<text x='50' y='60' text-anchor='middle' font-family='Arial,sans-serif' font-weight='900' font-size='{size}' fill='white'>{ini}</text></svg>"""
    return svg.encode()


def crest_svg(name: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(crest_bytes(name)).decode()


def _mime(data: bytes) -> str:
    if data[:4] == b"RIFF":
        return "image/webp"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    head = data.lstrip()[:5]
    if head.startswith(b"<svg") or head.startswith(b"<?xml"):
        return "image/svg+xml"
    return "image/png"


def _path_for(url: str) -> Path:
    ext = Path(url.split("?")[0]).suffix or ".png"
    return CACHE_DIR / (hashlib.sha1(url.encode()).hexdigest()[:16] + ext)


def logo_bytes(url: str | None, timeout: float = 5.0) -> tuple[str, bytes] | None:
    """(mime, bytes) del logo: memoria → base de datos → disco → descarga (y se guarda)."""
    if not url:
        return None
    if url in _mem:
        return _mem[url]
    st = get_store()
    hit = st.logo_get(url)
    if hit:
        _mem[url] = hit
        return hit
    path = _path_for(url)
    data = path.read_bytes() if path.exists() else None
    if data is None and url not in _failed:
        try:
            r = requests.get(url, timeout=timeout, headers={"User-Agent": "ZOLA/1.0"})
            if r.status_code == 200 and r.content and len(r.content) < 800_000:
                data = r.content
                try:
                    CACHE_DIR.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                except OSError:
                    pass
        except Exception:
            pass
        if data is None:
            _failed.add(url)
    if not data:
        return None
    out = (_mime(data), data)
    _mem[url] = out
    st.logo_put(url, out[0], data)
    return out


def logo(url: str | None, name: str = "", timeout: float = 5.0) -> str:
    """Data URI del logo o escudo generado (compatibilidad)."""
    hit = logo_bytes(url, timeout)
    if not hit:
        return crest_svg(name)
    return f"data:{hit[0]};base64," + base64.b64encode(hit[1]).decode()


def prefetch(urls, workers: int = 8) -> int:
    """Descarga y guarda en paralelo los logos que aún no están guardados."""
    todo = [u for u in dict.fromkeys(urls) if u and u not in _mem and u not in _failed]
    if not todo:
        return 0
    with ThreadPoolExecutor(workers) as ex:
        return sum(1 for r in ex.map(logo_bytes, todo) if r)
