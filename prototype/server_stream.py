import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

HOST = "127.0.0.1"
PORT = 8000
CAMERA_INDEX = 0
BOUNDARY = "frame"

cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
if not cap.isOpened():
    print(f"カメラ {CAMERA_INDEX} を開けませんでした")
    raise SystemExit(1)

for _ in range(30):
    cap.read()

# 複数スレッドから同時にカメラを読まないための鍵
cap_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            body = '<h1>Stream</h1><img src="/stream">'.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/stream":
            self.stream()
        else:
            self.send_error(404)

    def stream(self):
        self.send_response(200)
        self.send_header(
            "Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}"
        )
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            while True:
                with cap_lock:
                    ok, frame = cap.read()
                if not ok:
                    break
                ok, jpg = cv2.imencode(".jpg", frame)
                if not ok:
                    continue
                data = jpg.tobytes()
                self.wfile.write(f"--{BOUNDARY}\r\n".encode())
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(data)}\r\n\r\n".encode())
                self.wfile.write(data)
                self.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # ブラウザのタブを閉じると接続が切れる。正常な終了として扱う
            pass


server = ThreadingHTTPServer((HOST, PORT), Handler)
print(f"http://{HOST}:{PORT}/ で起動しました（Ctrl+C で終了）")
try:
    server.serve_forever()
except KeyboardInterrupt:
    pass
finally:
    server.server_close()
    cap.release()