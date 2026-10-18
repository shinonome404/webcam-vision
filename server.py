import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
MAX_REQUEST_SIZE = 64 * 1024
MAX_HISTORY = 20
MAX_MESSAGE_LENGTH = 2000


class WebcamVisionHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/status":
            self._send_json(200, {"ai_enabled": bool(os.environ.get("OPENAI_API_KEY"))})
            return

        filename = "index.html" if self.path == "/" else self.path.lstrip("/")
        if filename not in {"index.html", "app.js", "style.css"}:
            self.send_error(404)
            return

        path = ROOT / filename
        content_type = {
            ".html": "text/html; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".css": "text/css; charset=utf-8",
        }[path.suffix]
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            self._send_json(503, {"error": "AIチャットは未設定です。OPENAI_API_KEYを設定してください。"})
            return

        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > MAX_REQUEST_SIZE:
                self._send_json(413, {"error": "リクエストのサイズが上限を超えています。"})
                return
            payload = json.loads(self.rfile.read(size))
            messages = payload.get("messages")
            detections = payload.get("detections", [])
            if not isinstance(messages, list) or not messages:
                raise ValueError("messages must be a non-empty list")
            if not isinstance(detections, list):
                raise ValueError("detections must be a list")

            history = []
            for message in messages[-MAX_HISTORY:]:
                if not isinstance(message, dict) or message.get("role") not in {"user", "assistant"}:
                    raise ValueError("invalid message")
                content = message.get("content")
                if not isinstance(content, str) or not content.strip():
                    raise ValueError("invalid message content")
                history.append({
                    "role": message["role"],
                    "content": content.strip()[:MAX_MESSAGE_LENGTH],
                })

            objects = []
            for detection in detections[:20]:
                if not isinstance(detection, dict):
                    continue
                label = detection.get("class")
                score = detection.get("score")
                if isinstance(label, str) and isinstance(score, (int, float)):
                    objects.append(f"{label} ({score * 100:.0f}%)")
            scene = ", ".join(objects) if objects else "現在、検出された物体はありません"

            request_data = json.dumps({
                "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "あなたはWebカメラの物体検出を手伝う日本語アシスタントです。"
                            "検出結果を手がかりとして、簡潔で親切に回答してください。"
                            "画像そのものを見ているかのように、検出結果にない詳細を断定しないでください。"
                            f" 現在の検出結果: {scene}"
                        ),
                    },
                    *history,
                ],
            }).encode("utf-8")
            request = Request(
                "https://api.openai.com/v1/chat/completions",
                data=request_data,
                headers={
                    "Authorization": "Bearer " + api_key,
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(request, timeout=30) as response:
                result = json.loads(response.read())
            answer = result["choices"][0]["message"]["content"]
            if not isinstance(answer, str):
                raise ValueError("invalid AI response")
            self._send_json(200, {"answer": answer})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            self._send_json(400, {"error": "メッセージの形式が正しくありません。"})
        except HTTPError:
            self._send_json(502, {"error": "AIサービスへのリクエストに失敗しました。設定を確認してください。"})
        except (URLError, TimeoutError, OSError):
            self._send_json(502, {"error": "AIサービスに接続できませんでした。"})


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), WebcamVisionHandler)
    print(f"Webcam Vision: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
