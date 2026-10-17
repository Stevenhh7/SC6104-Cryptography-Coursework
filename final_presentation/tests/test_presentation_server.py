"""Exercise the fixed HTTP runner, including one real public-only RSA replay."""
import http.client
import errno
import io
import json
from pathlib import Path
import re
import sys
import threading
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, call, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import presentation_server as app


class PresentationServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = app.PresentationHTTPServer(("127.0.0.1", 0), app.PresentationHandler)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request_details(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=100)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, response.read(), response.headers
        connection.close()
        return result

    def request(self, method, path, body=None, headers=None):
        code, content, response_headers = self.request_details(method, path, body, headers)
        return code, content, response_headers.get("Content-Type")

    def post(self, body="{}", extra=None):
        headers = {"Origin": f"http://127.0.0.1:{self.port}", "Content-Type": "application/json"}
        headers.update(extra or {})
        return self.request("POST", "/api/live/run", body, headers)

    def test_assets_and_status(self):
        for path in (
            "/presentation/final.html", "/presentation/assets/live.js",
            "/presentation/embed/index.html",
            "/presentation/embed/a-key-implementation.html",
            "/presentation/embed/b-key-implementation.html",
            "/presentation/assets/implementation-embed.js",
            "/presentation/assets/implementation-embed.css",
            "/presentation/assets/favicon.svg",
            "/artifacts/figures/scan_times_presentation.svg",
        ):
            self.assertEqual(self.request("GET", path)[0], 200, path)
        code, body, _ = self.request("GET", "/api/live/status")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["runner"], "rsa-presentation-v1")

    def test_current_ten_slide_pages_ignore_old_cache_validators(self):
        for path in (
            "/presentation/final.html", "/presentation/assets/final.js",
            "/presentation/embed/a-key-implementation.html",
            "/presentation/embed/b-key-implementation.html",
        ):
            code, body, headers = self.request_details("GET", path, headers={
                "If-Modified-Since": "Fri, 31 Dec 9999 23:59:59 GMT",
                "If-None-Match": '"old-eight-slide-copy"',
            })
            self.assertEqual(code, 200, path)
            self.assertEqual(headers["Cache-Control"], "no-store", path)
            self.assertEqual(body, (app.ROOT / path.lstrip("/")).read_bytes(), path)
        _, content, _ = self.request("GET", "/presentation/final.html")
        self.assertEqual(len(re.findall(rb'<section class="slide[^\"]*"', content)), 10)
        self.assertIn(b'embed/a-key-implementation.html', content)
        self.assertIn(b'embed/b-key-implementation.html', content)
        _, status, _ = self.request("GET", "/api/live/status")
        info = json.loads(status)
        self.assertEqual(info["slide_count"], 10)
        self.assertRegex(info["presentation_version"], r"^[0-9a-f]{16}$")
        self.assertEqual(info["presentation_version"], app.presentation_info()["presentation_version"])
        code, _, headers = self.request_details("GET", "/")
        self.assertEqual(code, 302)
        self.assertEqual(headers["Location"], "/presentation/final.html?v=" + info["presentation_version"])
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_version_changes_when_embedded_code_or_assets_change(self):
        with tempfile.TemporaryDirectory(prefix="presentation-version-") as temporary:
            root = Path(temporary)
            presentation = root / "presentation"
            (presentation / "embed").mkdir(parents=True)
            (presentation / "assets").mkdir()
            (presentation / "final.html").write_text('<section class="slide"></section>' * 10, encoding="utf-8")
            code_page = presentation / "embed" / "b-key-implementation.html"
            code_page.write_text("old recovery page", encoding="utf-8")
            style = presentation / "assets" / "implementation-embed.css"
            style.write_text("body { color: navy; }", encoding="utf-8")
            with patch.object(app, "ROOT", root):
                before = app.presentation_info()
                self.assertEqual(before["slide_count"], 10)
                self.assertEqual(before, app.presentation_info())
                code_page.write_text("approved recovery and verification page", encoding="utf-8")
                after_code = app.presentation_info()
                self.assertNotEqual(before["presentation_version"], after_code["presentation_version"])
                style.write_text("body { color: teal; }", encoding="utf-8")
                self.assertNotEqual(after_code["presentation_version"], app.presentation_info()["presentation_version"])

    def test_updated_b_page_is_available_from_the_final_deck(self):
        _, final, _ = self.request("GET", "/presentation/final.html")
        self.assertIn(b'embed/b-key-implementation.html?v=20261010-final4', final)
        code, page, _ = self.request("GET", "/presentation/embed/b-key-implementation.html")
        self.assertEqual(code, 200)
        for text in (b'Private-key reconstruction', b'OAEP configuration and decryption', b'Recovery pipeline', b'Verification evidence', b'validation-data'):
            self.assertIn(text, page)

    def test_optional_browser_requests_do_not_report_404(self):
        for path in ("/favicon.ico", "/.well-known/appspecific/com.chrome.devtools.json"):
            for method in ("GET", "HEAD"):
                code, body, headers = self.request_details(method, path)
                self.assertEqual((code, body), (204, b""))
                self.assertEqual(headers["Cache-Control"], "no-store")
        code, body, content_type = self.request("GET", "/presentation/assets/favicon.svg")
        self.assertEqual(code, 200)
        self.assertIn("image/svg+xml", content_type)
        self.assertIn(b'<svg ', body)

    def test_launcher_opens_versioned_ten_slide_url_and_supports_no_browser(self):
        for flags, should_open in ((["--open-browser"], True), (["--open-browser", "--no-browser"], False), ([], False)):
            server = Mock(server_port=8765)
            server.serve_forever.side_effect = KeyboardInterrupt
            output = io.StringIO()
            with patch.object(app, "bind_server", return_value=server), \
                 patch.object(app.webbrowser, "open", return_value=True) as open_browser, \
                 patch.object(sys, "argv", ["presentation_server.py", *flags]), redirect_stdout(output):
                app.main()
            expected = "http://127.0.0.1:8765/presentation/final.html?v=" + app.presentation_info()["presentation_version"]
            self.assertIn("Final presentation (10 slides): " + expected, output.getvalue())
            self.assertIn(str(app.ROOT), output.getvalue())
            server.server_close.assert_called_once()
            if should_open:
                open_browser.assert_called_once_with(expected, new=2)
            else:
                open_browser.assert_not_called()

    def test_launcher_rejects_old_eight_slide_package(self):
        with patch.object(app, "presentation_info", return_value={"slide_count": 8, "presentation_version": "old"}), \
             patch.object(app, "bind_server") as bind, \
             patch.object(sys, "argv", ["presentation_server.py"]), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as result:
                app.main()
            self.assertEqual(result.exception.code, 1)
            bind.assert_not_called()

    def test_busy_port_uses_next_port_but_permission_errors_do_not(self):
        server = Mock()
        with patch.object(app, "PresentationHTTPServer", side_effect=[OSError(errno.EADDRINUSE, "busy"), server]) as factory:
            self.assertIs(app.bind_server(8765), server)
            self.assertEqual(factory.call_args_list, [
                call(("127.0.0.1", 8765), app.PresentationHandler),
                call(("127.0.0.1", 8766), app.PresentationHandler),
            ])
        with patch.object(app, "PresentationHTTPServer", side_effect=PermissionError(errno.EACCES, "blocked")) as factory:
            with self.assertRaises(PermissionError):
                app.bind_server(8765)
            factory.assert_called_once()

    def test_running_server_port_cannot_be_reused(self):
        if self.port == 65535:
            self.skipTest("No subsequent port in the valid range")
        second = app.bind_server(self.port)
        try:
            self.assertNotEqual(second.server_port, self.port)
            self.assertGreater(second.server_port, self.port)
        finally:
            second.server_close()

    def test_no_private_or_arbitrary_files_served(self):
        for path in ("/data/demo/ground_truth.json", "/rsa_lab/crypto.py", "/presentation/../../README.md", "/presentation/%2e%2e/requirements.txt"):
            self.assertEqual(self.request("GET", path)[0], 404, path)

    def test_only_same_origin_empty_command_is_accepted(self):
        self.assertEqual(self.post(extra={"Origin": "https://example.org"})[0], 403)
        self.assertEqual(self.post(extra={"Host": f"example.org:{self.port}"})[0], 403)
        self.assertEqual(self.request("POST", "/api/live/run", "{}")[0], 403)
        self.assertEqual(self.post('{"command":"anything"}')[0], 400)
        self.assertEqual(self.post('[]')[0], 400)

    def test_only_one_run_at_a_time(self):
        with app.RUN_LOCK:
            self.assertEqual(self.post()[0], 409)

    def test_failed_run_never_reports_success(self):
        with patch.object(app, "run_pipeline", side_effect=RuntimeError("Deliberate test failure")):
            code, body, _ = self.post()
        self.assertEqual(code, 200)
        events = [json.loads(line) for line in body.splitlines()]
        self.assertEqual(events[-1]["type"], "error")
        self.assertFalse(any(event.get("passed") for event in events))
        self.assertFalse(app.RUN_LOCK.locked())

    def test_real_2048_bit_replay_over_http(self):
        code, body, content_type = self.post()
        self.assertEqual(code, 200)
        self.assertIn("application/x-ndjson", content_type)
        events = [json.loads(line) for line in body.splitlines()]
        result = events[-1]
        self.assertEqual(result["type"], "result", result)
        self.assertTrue(result["passed"])
        self.assertEqual([event["stage"] for event in events if event["type"] == "stage"], list(range(5)))
        self.assertEqual((result["records"], result["unique_moduli"], result["factorable"], result["messages"], result["repaired_found"]), (102, 100, 5, 6, 0))
        self.assertEqual((result["fallback_candidates"], result["fallback_checks"]), (3, 9))
        self.assertGreater(result["scan_seconds"], 0)
        self.assertFalse(app.RUN_LOCK.locked())
        print("\nVerified live HTTP result: " + json.dumps(result))


if __name__ == "__main__":
    unittest.main()
