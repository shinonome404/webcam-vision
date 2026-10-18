"""
カメラ映像をブラウザにストリーミング配信するローカル用サーバー。

- 配信方式はMJPEG（multipart/x-mixed-replace）
- Webサーバーは標準ライブラリ（http.server）のみで構成する
- カメラの操作は local/camera.py の Camera クラスに任せる

使い方（プロジェクトの一番上のフォルダで実行）:
    python -m local.server
    ブラウザで http://127.0.0.1:8000/ を開く（Ctrl+C で終了）
"""

# 標準ライブラリのインポート
import cv2  # OpenCVを使ってカメラ映像をJPEGに変換するために使用
import threading # スレッド間でカメラアクセスを同期するためのロック用
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer # HTTPサーバー用クラスをインポート

# ローカルモジュールのインポート
from local.draw import draw_detections # 物体検出結果を画像に描画する関数
from local.camera import Camera # カメラ操作用クラスをインポート
from core.detector import Detector # 物体検出用クラス



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

    # POSTリクエストを処理するメソッド
    def do_POST(self):
        # URLのパスに応じて処理を振り分ける
        if self.path == "/shutdown":
            self.send_shutdown()
        else:
            self.send_error(404)

    # 停止ボタンを押したときの処理
    def send_shutdown(self):
        """停止ボタン：完了ページを返してから、サーバーに停止を依頼する。"""
        body = "<p>停止しました。このタブは閉じて大丈夫です。</p>".encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

        # ① 停止の合図を出す（配信ループを先に止める）
        self.server.stop_event.set()
        # serve_forever() を終わらせる。
        # shutdown() は待ち受けが終わるまで待つため、別スレッドで呼ぶ
        threading.Thread(target=self.server.shutdown).start()

    # トップページを返すメソッド
    def send_index(self):
        """トップページ：映像を表示する<img>タグだけを返す。"""
        body = (
            "<h1>Stream</h1>"
            '<img src="/stream"><br>'
            '<form method="post" action="/shutdown">'
            '<button type="submit">停止</button>'
            "</form>"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ストリーム配信を行うメソッド（ブラウザにMJPEG形式で映像を送り続ける）
    def send_stream(self):
        # カメラクラスのインスタンスをサーバーから取得する
        camera = self.server.camera
        detector = self.server.detector

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
            # 停止の合図が出るまで送り続ける
            while not self.server.stop_event.is_set():
                frame = camera.read()   # カメラから1フレーム取得
                if frame is None:       # フレームが取得できなかったらループを抜ける
                    break

                # 判定して、結果の枠と名前を画像に描き込む
                detections = detector.detect(frame)
                draw_detections(frame, detections)

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
    # モデルの読み込みはカメラより先に行う
    # （モデルがなかったとき、開いたカメラを解放し忘れないようにするため）
    try:
        detector = Detector()
    except FileNotFoundError as e:
        print(e)
        return

    # 停止の合図用イベントを作成してサーバーに預けておく
    try:
        camera = Camera(CAMERA_INDEX)
    except RuntimeError as e:
        print(e)
        return

    # リクエストごとにスレッドを分けるサーバー
    # （ストリーム配信中でも他のリクエストを受け付けられるようにするため）
    server = ThreadingHTTPServer((HOST, PORT), Handler)

    # Handler から使えるよう、サーバーに預けておく
    server.camera = camera # Handler から使えるよう、サーバーに預けておく
    server.detector = detector # Handler から使えるよう、サーバーに預けておく
    server.stop_event = threading.Event() # 停止の合図

    # サーバーを起動したことを通知するメッセージを表示
    print(f"http://{HOST}:{PORT}/ で起動しました（停止ボタン または Ctrl+C で終了）")
    
    # サーバーを起動してリクエストを処理し続ける
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

    # サーバーを停止する処理
    finally:
        print("停止しています…")
        # ① 停止の合図を出す（配信ループは次のフレームで抜ける）
        server.stop_event.set()
        # ③ サーバーの受付を止める
        server.server_close()
        # ④ カメラを解放する（読み取り中ならロックで終わるのを待つ）
        camera.release()
        print("停止しました")

""" エントリーポイント """
if __name__ == "__main__":
    main()
