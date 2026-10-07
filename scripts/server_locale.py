"""Server HTTP statico per docs/, usato da anteprima, screenshot e smoke test."""
from __future__ import annotations

import contextlib
import functools
import http.server
import socket
import threading
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"


class _Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # silenzioso
        pass

    def end_headers(self):
        # come GitHub Pages ma senza cache, così l'anteprima mostra sempre l'ultima versione
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def porta_libera() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def servi(cartella: Path = DOCS, porta: int | None = None, host: str = "127.0.0.1"):
    """Avvia il server in un thread; restituisce l'URL base (con / finale)."""
    porta = porta or porta_libera()
    handler = functools.partial(_Handler, directory=str(cartella))
    srv = http.server.ThreadingHTTPServer((host, porta), handler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{porta}/"
    finally:
        srv.shutdown()
        srv.server_close()
