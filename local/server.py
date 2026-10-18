"""
カメラ映像をブラウザにストリーミング配信するローカル用サーバー。

- 配信方式はMJPEG（multipart/x-mixed-replace）
- Webサーバーは標準ライブラリ（http.server）のみで構成する
- カメラの操作は local/camera.py の Camera クラスに任せる

使い方（プロジェクトの一番上のフォルダで実行）:
    python -m local.server
    ブラウザで http://127.0.0.1:8000/ を開く（Ctrl+C で終了）
"""

import cv2  # OpenCVを使ってカメラ映像をJPEGに変換するために使用
from local.camera import Camera # カメラ操作用クラスをインポート
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer # HTTPサーバー用クラスをインポート

""" サーバーの設定 """
HOST = "127.0.0.1"  # 自分のPCからのみアクセス可能にする
PORT = 8000         # 使用するポート番号
CAMERA_INDEX = 0    # 映らない場合は 1, 2 ... と変更する
BOUNDARY = "frame"  # MJPEGで各フレームを区切る文字列


""" HTTPリクエストを処理するハンドラクラス """
class Handler(BaseHTTPRequestHandler):

    # GETリクエストを処理するメソッドを提供する
    def do_GET(self):
        # URLのパスに応じて処理を振り分ける
        # トップページは "/"、ストリーム配信は "/stream" に対応させる
        # それ以外のURLは404を返す
        if self.path == "/":
            self.send_index()
        elif self.path == "/stream":
            self.send_stream()
        else:
            self.send_error(404)

    # トップページを返すメソッド
    def send_index(self):
        """トップページ：映像を表示する<img>タグだけを返す。"""
        body = '<h1>Stream</h1><img src="/stream">'.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ストリーム配信を行うメソッド（ブラウザにMJPEG形式で映像を送り続ける）
    def send_stream(self):
        # カメラクラスのインスタンスをサーバーから取得する
        camera = self.server.camera

        # HTTPヘッダーを送信して、ブラウザにMJPEG形式であることを伝える
        # HTTPステータスコード200 OKを送信
        self.send_response(200)
        # HTTPヘッダーの送信開始
        self.send_header(
            "Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}"
        )
        # キャッシュを無効化するヘッダーを送信
        self.send_header("Cache-Control", "no-cache")
        # ヘッダーの送信終了
        self.end_headers()

        # ここからループでフレームを送り続ける
        try:
            while True:
                frame = camera.read()   # カメラから1フレーム取得
                if frame is None:       # フレームが取得できなかったらループを抜ける
                    break

                # 画像をメモリ上でJPEGに変換する
                ok, jpg = cv2.imencode(".jpg", frame)  # フレームをJPEGに変換
                if not ok:                             # 変換に失敗したら次のフレームへ
                    continue
                data = jpg.tobytes()

                # 区切り線 → ヘッダー → JPEG本体 の順で1フレーム分を送る
                self.wfile.write(f"--{BOUNDARY}\r\n".encode())
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(data)}\r\n\r\n".encode())
                self.wfile.write(data)
                self.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # ブラウザのタブを閉じると接続が切れる。正常な終了として扱う
            pass

"""
メイン関数
"""
def main():
    # カメラを初期化する
    try:
        camera = Camera(CAMERA_INDEX)
    except RuntimeError as e:
        print(e)
        return

    # リクエストごとにスレッドを分けるサーバー
    # （ストリーム配信中でも他のリクエストを受け付けられるようにするため）
    server = ThreadingHTTPServer((HOST, PORT), Handler)

    # Handler からカメラ係を使えるよう、サーバーに預けておく
    server.camera = camera

    # サーバーを起動したことを通知するメッセージを表示
    print(f"http://{HOST}:{PORT}/ で起動しました（Ctrl+C で終了）")
    
    # サーバーを起動してリクエストを処理し続ける
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # 終了時は必ずカメラを解放する（解放しないと他のアプリから使えなくなる）
        server.server_close()
        camera.release()  # カメラを解放して終了

""" エントリーポイント """
if __name__ == "__main__":
    main()
