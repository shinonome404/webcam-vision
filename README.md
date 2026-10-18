# webcam-vision

USB Webカメラの映像から物体を判定し、ブラウザ上で表示・対話型AIで解説することを目指すプロジェクトです。
転職用ポートフォリオとして、段階的に設計・実装しています。

## 目標とする構成

| フェーズ | 内容 | 状況 |
|---|---|---|
| 1. ローカル配信 | カメラ映像をブラウザにストリーミング表示（Windows） | 完了 |
| 2. 物体判定 | OpenCV＋学習済みモデル（SSD MobileNet v2）で物体をリアルタイム判定 | 完了（学習済みモデルによる一般物体の判定まで） |
| 3. 対話AI | 判定結果を対話型AIで解説 | 未着手 |
| 4. AWS化 | サーバーレス構成（認証付きURLでアクセス） | 未着手 |

### 設計方針

- 判定処理は「画像を受け取り結果を返すだけ」の独立した部品（`core/`）にする
- カメラ取得や通信は差し替え可能な外側の部品とし、ローカル版（`local/`）とAWS版から同じ判定処理を使う
- 外部への依存は最小限にする（Webサーバーは標準ライブラリ `http.server` のみで構成）

## フォルダ構成

```
webcam-vision/
├─ core/                判定処理（カメラも通信も知らない共通部品）
│   ├─ detector.py      画像を受け取り、判定結果のリストを返す
│   └─ coco_labels.py   クラスIDと物体名の対応表
├─ local/               ローカル（Windows）用：カメラ取得・描画・配信
│   ├─ camera.py        カメラからフレームを取得する部品
│   ├─ draw.py          判定結果の枠と名前を画像に描き込む部品
│   ├─ server.py        判定付きの映像をブラウザへMJPEGで配信するサーバー
│   ├─ detect_image.py  静止画1枚を判定するテスト用スクリプト
│   └─ EXPLANATION.md   local の仕組みの解説
├─ models/              学習済みモデル（Git管理外。入手手順は下記）
├─ prototype/           開発初期に段階的に動作確認したファイル
├─ requirements.txt     必要なPythonライブラリ
└─ README.md
```

※ `frontend/`・`backend/`・`infra/`（AWS版）は今後追加予定です。

## 動作環境

- Windows
- Python 3.15
- USB Webカメラ

## 初期構築

ターミナルで、プロジェクトの一番上のフォルダにて実行します。

### 1. 仮想環境の作成と有効化

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

コマンドプロンプトの場合は `.venv\Scripts\activate.bat` で有効化します。
有効化に成功すると、行頭に `(.venv)` が表示されます。

### 2. ライブラリのインストール

```powershell
pip install -r requirements.txt
```

### 3. 学習済みモデルの入手

モデルはサイズが大きいため、リポジトリには含めていません。以下の手順で `models/` に配置します。

```powershell
mkdir models
cd models
curl.exe -L -o ssd_mobilenet_v2_coco_2018_03_29.tar.gz https://storage.googleapis.com/download.tensorflow.org/models/object_detection/ssd_mobilenet_v2_coco_2018_03_29.tar.gz
tar -xzf ssd_mobilenet_v2_coco_2018_03_29.tar.gz
del ssd_mobilenet_v2_coco_2018_03_29.tar.gz
curl.exe -L -o ssd_mobilenet_v2_coco_2018_03_29.pbtxt https://raw.githubusercontent.com/opencv/opencv_extra/4.x/testdata/dnn/ssd_mobilenet_v2_coco_2018_03_29.pbtxt
cd ..
```

| ファイル | 内容 | 配布元 |
|---|---|---|
| `ssd_mobilenet_v2_coco_2018_03_29/frozen_inference_graph.pb` | 学習済みの重み（COCOデータセットで学習） | TensorFlow Object Detection API（Google） |
| `ssd_mobilenet_v2_coco_2018_03_29.pbtxt` | OpenCVで読み込むための構成ファイル | OpenCV（opencv_extra） |

利用条件は各配布元を参照してください。

#### ダウンロードしたファイルの確認

開発時に取得したファイルの SHA-256 は以下のとおりです。同じ値になるか確認できます。

```powershell
certutil -hashfile models\ssd_mobilenet_v2_coco_2018_03_29\frozen_inference_graph.pb SHA256
certutil -hashfile models\ssd_mobilenet_v2_coco_2018_03_29.pbtxt SHA256
```

| ファイル | SHA-256 |
|---|---|
| `frozen_inference_graph.pb` | `2a8d8a89d695842e60d8c6d144181100555563e21acf2fa1e8f561fec5c3c6ad` |
| `ssd_mobilenet_v2_coco_2018_03_29.pbtxt` | `cfbecf9447c384403ef5cf695f4cd0bb4840c1312938280350639a9a8e82d303` |

※ 配布元による公式のハッシュ値は公開されていないため、上記は開発時に https 経由で取得したファイルの値です。

### 4. カメラの単体確認

```powershell
python -m local.camera
```

画像サイズと平均の明るさが表示されれば成功です。

### 5. 静止画での判定確認（任意）

```powershell
python -m local.detect_image 画像ファイルのパス
```

判定結果が表示され、枠と名前を描き込んだ `result.jpg` が保存されます。

### 6. 配信サーバーの起動

```powershell
python -m local.server
```

ブラウザで http://127.0.0.1:8000/ を開くと、判定結果（枠と物体名）を重ねたカメラ映像が表示されます。

ページの「停止」ボタン、またはターミナルで `Ctrl+C` を押すと、配信を止めてカメラを解放してから終了します。

## トラブルシューティング

| 症状 | 原因と対処 |
|---|---|
| カメラを開けない | 他のアプリ（Windowsのカメラアプリ等）がカメラを使用中。そのアプリを終了する |
| 画像が真っ暗 | 起動直後は自動露出の調整が終わっていない。`Camera` クラスで起動時にフレームを読み捨てて対処済み |
| 目的のカメラが映らない | `local/server.py` の `CAMERA_INDEX` を `1`, `2` … と変更する |
| `No module named local.xxx` | プロジェクトの一番上のフォルダで実行しているか、ファイル名が正しいかを確認する |
| `モデルが見つかりません` | 「3. 学習済みモデルの入手」の手順で `models/` に配置する |
| モデルのダウンロードで `SEC_E_WRONG_PRINCIPAL` | `https://download.tensorflow.org/...` は証明書の名前が一致しない。上記の `storage.googleapis.com` のURLを使う。証明書の確認を無効化（`-k`）する回避策は使わない |