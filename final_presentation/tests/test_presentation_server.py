"""Exercise the fixed HTTP runner, including one real public-only RSA replay."""
import http.client
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import presentation_server as app


class PresentationServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.PresentationHandler)
        cls.port = cls.server.server_port
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=100)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, response.read(), response.getheader("Content-Type")
        connection.close()
        return result

    def post(self, body="{}", extra=None):
        headers = {"Origin": f"http://127.0.0.1:{self.port}", "Content-Type": "application/json"}
        headers.update(extra or {})
        return self.request("POST", "/api/live/run", body, headers)

    def test_assets_and_status(self):
        for path in ("/presentation/final.html", "/presentation/assets/live.js", "/presentation/embed/index.html", "/artifacts/figures/scan_times_presentation.svg"):
            self.assertEqual(self.request("GET", path)[0], 200, path)
        code, body, _ = self.request("GET", "/api/live/status")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["runner"], "rsa-presentation-v1")

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
