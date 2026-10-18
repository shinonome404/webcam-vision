from http.server import BaseHTTPRequestHandler, HTTPServer

import cv2

HOST = "127.0.0.1"
PORT = 8000
CAMERA_INDEX = 0

cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
if not cap.isOpened():
    print(f"カメラ {CAMERA_INDEX} を開けませんでした")
    raise SystemExit(1)

# 起動直後の暗いフレームを読み捨てる
for _ in range(30):
    cap.read()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            body = '<h1>Snapshot</h1><img src="/snapshot.jpg">'.encode("utf-8")
            self.send_bytes(body, "text/html; charset=utf-8")
        elif self.path == "/snapshot.jpg":
            ok, frame = cap.read()
            if not ok:
                self.send_error(500, "frame read failed")
                return
            ok, jpg = cv2.imencode(".jpg", frame)
            if not ok:
                self.send_error(500, "jpeg encode failed")
                return
            self.send_bytes(jpg.tobytes(), "image/jpeg")
        else:
            self.send_error(404)

    def send_bytes(self, body, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


server = HTTPServer((HOST, PORT), Handler)
print(f"http://{HOST}:{PORT}/ で起動しました（Ctrl+C で終了）")
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
    cap.release()