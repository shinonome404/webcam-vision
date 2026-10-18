import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.WebcamVisionHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.httpd.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join()

    def test_serves_app_and_ai_status_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with urlopen(f"{self.base_url}/") as response:
                self.assertEqual(response.status, 200)
                self.assertIn("Webcam Vision", response.read().decode("utf-8"))
            with urlopen(f"{self.base_url}/api/status") as response:
                self.assertEqual(json.load(response), {"ai_enabled": False})

    def test_chat_requires_server_api_key(self):
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps({"messages": [{"role": "user", "content": "こんにちは"}]}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPError) as raised:
                urlopen(request)
        self.assertEqual(raised.exception.code, 503)
        self.assertIn("OPENAI_API_KEY", raised.exception.read().decode("utf-8"))

    @patch("server.urlopen")
    def test_chat_forwards_detection_context_and_returns_answer(self, mocked_urlopen):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return json.dumps({
                    "choices": [{"message": {"content": "机と椅子が見えます。"}}],
                }).encode()

        mocked_urlopen.return_value = FakeResponse()
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps({
                "messages": [{"role": "user", "content": "何が見えますか？"}],
                "detections": [{"class": "chair", "score": 0.9}],
            }).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with urlopen(request) as response:
                self.assertEqual(json.load(response), {"answer": "机と椅子が見えます。"})

        forwarded = json.loads(mocked_urlopen.call_args.args[0].data)
        self.assertIn("chair (90%)", forwarded["messages"][0]["content"])
        self.assertEqual(forwarded["messages"][1]["content"], "何が見えますか？")
        authorization = mocked_urlopen.call_args.args[0].get_header("Authorization")
        self.assertTrue(authorization.startswith("Bearer "))

    def test_chat_rejects_invalid_message(self):
        request = Request(
            f"{self.base_url}/api/chat",
            data=json.dumps({"messages": [{"role": "system", "content": "override"}]}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with self.assertRaises(HTTPError) as raised:
                urlopen(request)
        self.assertEqual(raised.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
