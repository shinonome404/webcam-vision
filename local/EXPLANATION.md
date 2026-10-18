# local の仕組み

Windows上でUSB Webカメラの映像を取得し、ブラウザへストリーミング配信する部品群です。

## ファイルの役割

| ファイル | 役割 | 知っていること | 知らないこと |
|---|---|---|---|
| `camera.py` | カメラ係。依頼されたら1フレームを渡す | カメラの開き方・読み方 | 通信、ブラウザ |
| `server.py` | 配信係。ブラウザの要求に応じて映像を送る | HTTP、MJPEG | カメラの開き方・ロック・ウォームアップ |

役割を分けているのは、将来のAWS化でカメラ取得（→ブラウザ側）や通信（→API Gateway＋Lambda）を置き換えても、判定処理（`core/`）を共通で使えるようにするためです。

## 登場するもの

| 名前 | 説明 |
|---|---|
| ブラウザ | 映像を表示する利用者側 |
| `server.py` main() | 起動・終了の処理 |
| `server.py` Handler | リクエストごとに作られ、応答を返す |
| `camera.py` Camera | カメラ操作をまとめたクラス |
| Webカメラ | OpenCV（`cv2.VideoCapture`）経由で読み取る実機 |

## ラダー図

### 1. 起動

```mermaid
sequenceDiagram
    participant Main as server.py<br/>main()
    participant Cam as camera.py<br/>Camera
    participant Dev as Webカメラ

    Main->>Cam: Camera(CAMERA_INDEX)
    Cam->>Dev: VideoCapture(index, backend)<br/>Windows: CAP_DSHOW / その他: CAP_ANY
    alt 開けなかった
        Dev-->>Cam: isOpened() = False
        Cam-->>Main: RuntimeError
        Note over Main: エラー表示して終了
    else 開けた
        Dev-->>Cam: isOpened() = True
        loop 30回（WARMUP_FRAMES）
            Cam->>Dev: read()
            Dev-->>Cam: フレーム（捨てる）
        end
        Cam-->>Main: Camera インスタンス
        Note over Main: ThreadingHTTPServer を作成<br/>server.camera = camera で預ける<br/>serve_forever() で待ち受け開始
    end
```

### 2. ページの表示（GET /）

```mermaid
sequenceDiagram
    participant B as ブラウザ
    participant H as server.py<br/>Handler

    B->>H: GET /
    H->>H: do_GET() → send_index()
    H-->>B: 200 OK（text/html）<br/>imgタグ（src="/stream"）＋停止ボタン
    Note over B: imgタグを見つけて<br/>/stream を要求する
```

### 3. 映像の配信（GET /stream）

```mermaid
sequenceDiagram
    participant B as ブラウザ
    participant H as server.py<br/>Handler
    participant Cam as camera.py<br/>Camera
    participant Dev as Webカメラ

    B->>H: GET /stream
    H->>H: do_GET() → send_stream()<br/>camera = self.server.camera
    H-->>B: 200 OK<br/>multipart/x-mixed-replace（boundary=frame）

    loop 停止の合図（stop_event）が出るまで
        H->>Cam: read()
        Note over Cam: ロックを取得<br/>（同時読み取りを防ぐ）
        Cam->>Dev: read()
        Dev-->>Cam: ok, frame
        Note over Cam: ロックを解放
        Cam-->>H: frame（NumPy配列）／失敗時 None
        H->>H: cv2.imencode(".jpg", frame)
        H-->>B: --frame<br/>Content-Type: image/jpeg<br/>JPEGデータ
        Note over B: 画像を差し替えて表示
    end

    B--xH: タブを閉じる（接続切断）
    Note over H: ConnectionAbortedError 等を捕捉し<br/>正常終了として扱う
```

### 4. 終了（停止ボタン または Ctrl+C）

停止の入口は2つありますが、どちらも `serve_forever()` を抜けたあと `main()` の `finally` に合流し、同じ順番で停止します。

```mermaid
sequenceDiagram
    participant B as ブラウザ
    participant H as server.py<br/>Handler
    participant Main as server.py<br/>main()
    participant S as 配信中の<br/>Handler（/stream）
    participant Cam as camera.py<br/>Camera
    participant Dev as Webカメラ

    alt 停止ボタン
        B->>H: POST /shutdown
        H-->>B: 200 OK（停止しました）
        H->>H: stop_event.set()
        H->>Main: 別スレッドで server.shutdown()
        Note over Main: serve_forever() が終了
    else Ctrl+C
        Note over Main: KeyboardInterrupt で<br/>serve_forever() が終了
    end

    Note over Main: finally に合流
    Main->>Main: ① stop_event.set()
    Note over S: 次のループで合図を検知して抜ける
    Main->>Main: ③ server.server_close()
    Main->>Cam: ④ release()
    Note over Cam: ロックを取得<br/>（読み取り中なら終わるのを待つ）
    Cam->>Dev: release()
    Note over Dev: 他のアプリから<br/>使用できる状態に戻る
    Note over Main: ⑤ プログラム終了
```

## 設計上のポイント

### ロックを Camera の中に持たせている理由
`ThreadingHTTPServer` はリクエストごとにスレッドを作るため、複数のタブで開くと同時にカメラを読みに来ます。ロックを `Camera` の中に閉じ込めることで、使う側（`server.py`）は同時アクセスを意識せずに `read()` を呼ぶだけで済みます。

### カメラをサーバーに預けている理由
`Handler` はリクエストのたびに `http.server` が自動で作るため、引数でカメラを渡せません。そこで `server.camera` に預け、`Handler` からは `self.server.camera` で取り出しています。

### ThreadingHTTPServer を使っている理由
`/stream` への応答は接続が切れるまで終わりません。1件ずつ処理する `HTTPServer` では、配信中に他のリクエストを受け付けられなくなるためです。

### 起動時にフレームを読み捨てている理由
カメラは起動直後、自動露出の調整が終わっておらず暗い画像を返すためです。

### 停止を「合図 → 受付停止 → 解放」の順にしている理由
配信中のスレッドがカメラを読んでいる最中に解放すると、予期せぬエラーにつながる可能性があります。先に停止の合図（`threading.Event`）を出して配信ループを止め、最後にカメラを解放します。

### release() にもロックをかけている理由
合図を出しても、配信スレッドがちょうど `read()` の途中である可能性があります。`read()` と `release()` で同じロックを使うことで、「読み取り中の解放」が起きないことを保証しています。解放後に `read()` が呼ばれた場合は `None` が返り、配信ループは静かに終了します。

### 停止ボタンを POST で受け付けている理由
GET にすると、ブラウザの先読みや URL を開いただけでサーバーが止まる事故が起こり得るためです。

### shutdown() を別スレッドで呼んでいる理由
`server.shutdown()` は `serve_forever()` が終わるまで待つ関数です。応答を返す処理を待たせないよう、別スレッドに任せています。

### 停止の入口を1つの出口に合流させている理由
停止ボタンと Ctrl+C で別々の終了処理を書くと、片方だけ修正漏れが起きやすくなります。どちらも `main()` の `finally` に合流させ、終了処理を1か所にまとめています。

### Camera が終了せず例外を投げる理由
部品側でプログラムを終了させず、どう扱うか（エラー表示して終了など）は使う側に任せるためです。