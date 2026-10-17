"""Serve the final presentation and replay its fixed public-input experiment.

Only loopback clients are accepted. The run endpoint takes no commands or paths.
Every scan/recovery invokes the existing rsa_lab CLI in a new Python process.
"""

import argparse
from datetime import datetime, timezone
import errno
import hashlib
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import unquote, urlsplit
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
RUN_LOCK = threading.Lock()


def presentation_info():
    """Identify the deck and its code pages/assets, including embedded updates."""
    class SlideCounter(HTMLParser):
        count = 0

        def handle_starttag(self, tag, attrs):
            if tag == "section" and "slide" in dict(attrs).get("class", "").split():
                self.count += 1

    content = (ROOT / "presentation" / "final.html").read_bytes()
    counter = SlideCounter()
    counter.feed(content.decode("utf-8"))
    version = hashlib.sha256()
    presentation = ROOT / "presentation"
    resources = sorted(path for path in presentation.rglob("*")
                       if path.is_file() and path.suffix.lower() in {".html", ".css", ".js"})
    for resource in resources:
        version.update(resource.relative_to(ROOT).as_posix().encode("utf-8") + b"\0")
        version.update(hashlib.sha256(resource.read_bytes()).digest())
    return {"slide_count": counter.count, "presentation_version": version.hexdigest()[:16]}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_pipeline(root, emit):
    """Fresh computation; archived expected results are read only afterwards."""
    started = time.perf_counter()
    archive = root / "artifacts" / "demo"
    public = archive / "public_keys.jsonl"
    ciphertexts = archive / "ciphertexts.json"

    def stage(index, text):
        emit({"type": "stage", "stage": index, "text": text})

    def log(text):
        emit({"type": "output", "text": text})

    def cli(arguments, display):
        # Argument arrays, fixed paths and shell=False: no browser command input.
        log("$ " + display)
        process = subprocess.run(
            [sys.executable, "-X", "utf8", "-m", "rsa_lab", *map(str, arguments)],
            cwd=root, capture_output=True, text=True, encoding="utf-8", timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if process.stdout:
            log(process.stdout.rstrip())
        if process.returncode:
            raise RuntimeError(process.stderr.strip() or f"Python exited with code {process.returncode}")

    stage(0, "[1/5] Validate the archived public inputs")
    manifest = read_json(archive / "manifest.json")
    for key, filename in (("public_sha256", public), ("ciphertexts_sha256", ciphertexts)):
        if digest(filename) != manifest[key]:
            raise ValueError(f"Input checksum mismatch: {filename.name}")
    records = [json.loads(line) for line in public.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records or any(set(row) != {"id", "n", "e"} or int(row["n"], 16).bit_length() != 2048 for row in records):
        raise ValueError("Expected public-only records with actual 2048-bit RSA moduli")
    log(f"{len(records)} public records; {len({row['n'] for row in records})} distinct 2048-bit moduli")
    log("Public input SHA-256: " + digest(public))
    log("No ground-truth file or original private key enters scan or recover.")

    # Results are isolated from the original experiment and cleaned automatically.
    with tempfile.TemporaryDirectory(prefix="rsa-presentation-") as temporary:
        out = Path(temporary)
        scan_file, recovery_file = out / "scan.json", out / "recovery.json"
        log("$OUT = " + str(out))
        stage(1, "[2/5] Execute batch GCD with the A detection engine")
        cli(["scan", "--public", public, "--algorithm", "batch", "--backend", "auto", "--out", scan_file],
            'python -m rsa_lab scan --public artifacts/demo/public_keys.jsonl --algorithm batch --backend auto --out "$OUT/scan.json"')
        stage(2, "[3/5] Reconstruct private keys and decrypt OAEP")
        cli(["recover", "--public", public, "--scan", scan_file, "--ciphertexts", ciphertexts, "--out", recovery_file],
            'python -m rsa_lab recover --public artifacts/demo/public_keys.jsonl --scan "$OUT/scan.json" --ciphertexts artifacts/demo/ciphertexts.json --out "$OUT/recovery.json"')
        stage(3, "[4/5] Compare fresh results with archived verified evidence")
        actual_scan, recovery = read_json(scan_file), read_json(recovery_file)
        expected_scan = read_json(archive / "scan_batch.json")
        if actual_scan["public_sha256"] != digest(public) or expected_scan["public_sha256"] != digest(public):
            raise ValueError("Scan/input checksum mismatch")
        actual_status = {row["id"]: row["status"] for row in actual_scan["records"]}
        expected_status = {row["id"]: row["status"] for row in expected_scan["records"]}
        if actual_status != expected_status or actual_scan["summary"]["unresolved"]:
            raise ValueError("Fresh scan disagrees with the archived verified result")
        factored = [row for row in actual_scan["records"] if row["status"] == "factor_found"]
        for row in factored:
            n, p, q = (int(row[key], 16) for key in ("n", "factor", "cofactor"))
            if not (1 < p < n and 1 < q < n and p * q == n):
                raise ValueError("Invalid recovered factorization")
        actual = {row["id"]: row["plaintext_utf8"] for row in recovery["records"] if row["status"] == "decrypted"}
        expected = {row["id"]: row["plaintext_utf8"] for row in read_json(archive / "decrypted_messages.json")}
        if not expected or actual != expected:
            raise ValueError("OAEP plaintexts do not match archived verified messages")
        log(f"All {len(actual_status)} record statuses match; every returned factorization satisfies p × q = N.")
        for key_id, plaintext in actual.items():
            log(f"MATCH  {key_id}: {plaintext}")
        log("Comparison uses archived verified outputs, after fresh scanning and recovery.")
        stage(4, "[5/5] Rescan the saved replacement-key collection")
        repaired_public = archive / "repaired" / "public_keys.jsonl"
        if digest(repaired_public) != read_json(archive / "scan_repaired.json")["public_sha256"]:
            raise ValueError("Replacement input checksum mismatch")
        repaired_file = out / "repaired.json"
        cli(["scan", "--public", repaired_public, "--algorithm", "batch", "--backend", "auto", "--out", repaired_file],
            'python -m rsa_lab scan --public artifacts/demo/repaired/public_keys.jsonl --algorithm batch --backend auto --out "$OUT/repaired.json"')
        repaired = read_json(repaired_file)
        if repaired["summary"]["factor_found"] or repaired["summary"]["unresolved"]:
            raise ValueError("Replacement collection still contains shared or unresolved factors")
        result = {"type": "result", "passed": True,
                  "records": len(records), "unique_moduli": actual_scan["summary"]["unique_moduli"],
                  "factorable": actual_scan["summary"]["factor_found"], "messages": len(actual),
                  "fallback_candidates": actual_scan["summary"]["fallback_candidates"],
                  "fallback_checks": actual_scan["summary"]["fallback_gcd_calls"],
                  "scan_seconds": actual_scan["timings_seconds"]["total"],
                  "repaired_found": repaired["summary"]["factor_found"], "backend": actual_scan["backend"],
                  "public_sha256": digest(public), "python": sys.version.split()[0],
                  "elapsed_seconds": time.perf_counter() - started,
                  "finished_at": datetime.now(timezone.utc).isoformat(),
                  "verification": "Fresh results match archived verified outputs; full ground-truth controls are not rerun."}
        log("PASS — fresh scan, OAEP recovery, archive comparison and replacement rescan completed.")
        emit(result)


class PresentationHTTPServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR can let two previews bind the same port.
    allow_reuse_address = False

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class PresentationHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def allowed_host(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def end_headers(self):
        # Every launch must use the current HTML, iframe pages and scripts.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def json_response(self, status, value):
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def browser_probe(self):
        if urlsplit(self.path).path not in {"/favicon.ico", "/.well-known/appspecific/com.chrome.devtools.json"}:
            return False
        # Optional browser requests: no legacy ICO or DevTools workspace binding.
        # The real SVG favicon is linked from the presentation HTML.
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()
        return True

    def do_GET(self):
        if not self.allowed_host():
            self.send_error(403)
            return
        if self.browser_probe():
            return
        path = urlsplit(self.path).path
        if path == "/api/live/status":
            self.json_response(200, {"runner": "rsa-presentation-v1", "python": sys.version.split()[0], "busy": RUN_LOCK.locked(), **presentation_info()})
        elif path == "/":
            self.send_response(302)
            self.send_header("Location", "/presentation/final.html?v=" + presentation_info()["presentation_version"])
            self.end_headers()
        else:
            super().do_GET()

    def do_HEAD(self):
        if not self.allowed_host():
            self.send_error(403)
        elif not self.browser_probe():
            super().do_HEAD()

    def send_head(self):
        path = (ROOT / unquote(urlsplit(self.path).path).lstrip("/")).resolve()
        allowed = any(path.is_relative_to(folder) for folder in ((ROOT / "presentation").resolve(), (ROOT / "artifacts/figures").resolve()))
        if not self.allowed_host() or not allowed or not path.is_file():
            self.send_error(404)
            return None
        # Old cached responses may still send validators even after this fix.
        for name in ("If-Modified-Since", "If-None-Match"):
            if name in self.headers:
                del self.headers[name]
        return super().send_head()

    def do_POST(self):
        origin = self.headers.get("Origin")
        if not self.allowed_host() or origin != f"http://{self.headers.get('Host')}":
            self.send_error(403)
            return
        if self.path != "/api/live/run":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 32 or self.headers.get("Content-Type") != "application/json" or json.loads(self.rfile.read(length)) != {}:
                raise ValueError("Expected empty JSON object")
        except (ValueError, json.JSONDecodeError):
            self.send_error(400)
            return
        if not RUN_LOCK.acquire(blocking=False):
            self.json_response(409, {"error": "Another pipeline is running"})
            return
        connected = True

        def emit(event):
            nonlocal connected
            if connected:
                try:
                    self.wfile.write((json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8"))
                    self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    connected = False

        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            run_pipeline(ROOT, emit)
        except Exception as error:
            emit({"type": "error", "text": str(error)})
        finally:
            RUN_LOCK.release()


def bind_server(port):
    """A previous preview may own the requested port; never reuse its content."""
    for candidate in range(port, min(port + 10, 65536)):
        try:
            return PresentationHTTPServer(("127.0.0.1", candidate), PresentationHandler)
        except OSError as error:
            if error.errno != errno.EADDRINUSE and getattr(error, "winerror", None) != 10048:
                raise
    raise OSError(f"No available local port between {port} and {min(port + 9, 65535)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open-browser", action="store_true", help="Open the current version after starting")
    parser.add_argument("--no-browser", dest="open_browser", action="store_false", help="Start without opening a browser")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    info = presentation_info()
    if info["slide_count"] != 10:
        parser.exit(1, f"Expected 10 slides in {ROOT / 'presentation/final.html'}, found {info['slide_count']}.\n")
    try:
        server = bind_server(args.port)
    except OSError as error:
        parser.exit(1, f"Could not start the presentation server: {error}\n")
    url = f"http://127.0.0.1:{server.server_port}/presentation/final.html?v={info['presentation_version']}"
    if args.port and server.server_port != args.port:
        print(f"Port {args.port} is occupied; using port {server.server_port}.", flush=True)
    print(f"Final presentation ({info['slide_count']} slides): {url}", flush=True)
    print(f"Presentation folder: {ROOT}", flush=True)
    print("Press Ctrl+C to stop. The live run uses temporary result files.", flush=True)
    try:
        if args.open_browser:
            try:
                if not webbrowser.open(url, new=2):
                    print("Open the URL above in your browser.", flush=True)
            except OSError:
                print("Open the URL above in your browser.", flush=True)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
