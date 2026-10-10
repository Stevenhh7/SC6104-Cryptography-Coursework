"""Serve the final presentation and replay its fixed public-input experiment.

Only loopback clients are accepted. The run endpoint takes no commands or paths.
Every scan/recovery invokes the existing rsa_lab CLI in a new Python process.
"""

import argparse
from datetime import datetime, timezone
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
RUN_LOCK = threading.Lock()


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


class PresentationHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def allowed_host(self):
        return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def json_response(self, status, value):
        body = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if not self.allowed_host():
            self.send_error(403)
            return
        path = urlsplit(self.path).path
        if path == "/api/live/status":
            self.json_response(200, {"runner": "rsa-presentation-v1", "python": sys.version.split()[0], "busy": RUN_LOCK.locked()})
        elif path == "/":
            self.send_response(302)
            self.send_header("Location", "/presentation/final.html")
            self.end_headers()
        else:
            super().do_GET()

    def send_head(self):
        path = (ROOT / unquote(urlsplit(self.path).path).lstrip("/")).resolve()
        allowed = any(path.is_relative_to(folder) for folder in ((ROOT / "presentation").resolve(), (ROOT / "artifacts/figures").resolve()))
        if not self.allowed_host() or not allowed or not path.is_file():
            self.send_error(404)
            return None
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
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            run_pipeline(ROOT, emit)
        except Exception as error:
            emit({"type": "error", "text": str(error)})
        finally:
            RUN_LOCK.release()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), PresentationHandler)
    print(f"Final presentation: http://127.0.0.1:{server.server_port}/presentation/final.html", flush=True)
    print("Press Ctrl+C to stop. The live run uses temporary result files.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
