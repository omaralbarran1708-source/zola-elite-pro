"""Logos de equipos y ligas: se descargan una vez, se guardan en disco y se
sirven embebidos (data URI). Si no se pueden descargar, se genera un escudo
SVG con las iniciales para que nunca aparezca una imagen rota."""
from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path

import requests

CACHE_DIR = Path(__file__).resolve().parent.parent / "assets" / "logos"
_mem: dict[str, str] = {}
_failed: set[str] = set()


def _initials(name: str) -> str:
    words = [w for w in re.split(r"[\s\-\.]+", name or "") if w and w.lower() not in {"fc", "cf", "sc", "de", "la", "el", "club", "ac"}]
    if not words:
        return "?"
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:3]).upper()


def crest_svg(name: str) -> str:
    """Escudo genérico con color estable según el nombre."""
    h = int(hashlib.md5((name or "?").encode()).hexdigest(), 16)
    hue = h % 360
    c1, c2 = f"hsl({hue},65%,42%)", f"hsl({(hue + 35) % 360},70%,28%)"
    ini = _initials(name)
    size = 34 if len(ini) <= 2 else 27
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>
<defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='{c1}'/><stop offset='1' stop-color='{c2}'/></linearGradient></defs>
<path d='M50 4 L90 16 V48 C90 72 72 88 50 96 C28 88 10 72 10 48 V16 Z' fill='url(#g)' stroke='white' stroke-width='4'/>
<text x='50' y='60' text-anchor='middle' font-family='Arial,sans-serif' font-weight='900' font-size='{size}' fill='white'>{ini}</text></svg>"""
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def _mime(data: bytes) -> str:
    if data[:4] == b"RIFF":
        return "image/webp"
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data.lstrip()[:4] in (b"<svg", b"<?xm"):
        return "image/svg+xml"
    return "image/png"


def _path_for(url: str) -> Path:
    ext = Path(url.split("?")[0]).suffix or ".png"
    return CACHE_DIR / (hashlib.sha1(url.encode()).hexdigest()[:16] + ext)


def logo(url: str | None, name: str = "", timeout: float = 4.0) -> str:
    """Data URI del logo (descargado y cacheado) o escudo generado."""
    if not url:
        return crest_svg(name)
    if url in _mem:
        return _mem[url]
    path = _path_for(url)
    data = None
    if path.exists():
        data = path.read_bytes()
    elif url not in _failed:
        try:
            r = requests.get(url, timeout=timeout)
            if r.status_code == 200 and r.content and len(r.content) < 600_000:
                data = r.content
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        except Exception:
            pass
        if data is None:
            _failed.add(url)
    if not data:
        return crest_svg(name)
    uri = f"data:{_mime(data)};base64," + base64.b64encode(data).decode()
    _mem[url] = uri
    return uri


def prefetch(pairs: list[tuple[str | None, str]], workers: int = 8) -> None:
    """Descarga en paralelo los logos que aún no están en caché."""
    from concurrent.futures import ThreadPoolExecutor
    todo = [(u, n) for u, n in pairs if u and u not in _mem and u not in _failed and not _path_for(u).exists()]
    if todo:
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(lambda p: logo(*p), todo))
