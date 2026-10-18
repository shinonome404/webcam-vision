from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
PORT = 8000


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = "<h1>Hello</h1>".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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