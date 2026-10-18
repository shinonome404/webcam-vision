# webcam-vision

USB Webカメラの映像から物体を判定し、ブラウザ上で表示・対話型AIで解説することを目指すプロジェクトです。

## 目標とする構成

| フェーズ | 内容 | 状況 |
|---|---|---|
| 1. ローカル配信 | カメラ映像をブラウザにストリーミング表示（Windows） | 完了 |
| 2. 物体判定 | OpenCV＋学習済みモデル（MobileNet-SSD v2）で物体を判定 | 未着手 |
| 3. 対話AI | 判定結果を対話型AIで解説 | 未着手 |
| 4. AWS化 | サーバーレス構成（認証付きURLでアクセス） | 未着手 |

### 設計方針

- 判定処理は「画像を受け取り結果を返すだけ」の独立した部品（`core/`）にする
- カメラ取得や通信は差し替え可能な外側の部品とし、ローカル版（`local/`）とAWS版から同じ判定処理を使う
- 外部への依存は最小限にする（Webサーバーは標準ライブラリ `http.server` のみで構成）

## フォルダ構成

```
webcam-vision/
├─ local/            ローカル（Windows）用：カメラ取得と配信
│   ├─ camera.py     カメラからフレームを取得する部品
│   ├─ server.py     ブラウザへMJPEGで配信するサーバー
│   └─ EXPLANATION.md  local の仕組みの解説
├─ prototype/        開発初期に段階的に動作確認したファイル
├─ requirements.txt  必要なPythonライブラリ
└─ README.md
```

※ `core/`（判定処理）、`frontend/`・`backend/`・`infra/`（AWS版）は今後追加予定です。

## 動作環境

- Windows
- Python 3.15
- USB Webカメラ

## 初期構築

PowerShellで、プロジェクトの一番上のフォルダにて実行します。

### 1. 仮想環境の作成と有効化

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

有効化に成功すると、行頭に `(.venv)` が表示されます。

### 2. ライブラリのインストール

```powershell
pip install -r requirements.txt
```

### 3. カメラの単体確認

```powershell
python -m local.camera
```

画像サイズと平均の明るさが表示されれば成功です。

### 4. 配信サーバーの起動

```powershell
python -m local.server
```

ブラウザで http://127.0.0.1:8000/ を開くとカメラ映像が表示されます。

ページの「停止」ボタン、またはターミナルで `Ctrl+C` を押すと、配信を止めてカメラを解放してから終了します。

## トラブルシューティング

| 症状 | 原因と対処 |
|---|---|
| カメラを開けない | 他のアプリ（Windowsのカメラアプリ等）がカメラを使用中。そのアプリを終了する |
| 画像が真っ暗 | 起動直後は自動露出の調整が終わっていない。`Camera` クラスで起動時にフレームを読み捨てて対処済み |
| 目的のカメラが映らない | `local/server.py` の `CAMERA_INDEX` を `1`, `2` … と変更する |
| `No module named local.xxx` | プロジェクトの一番上のフォルダで実行しているか、ファイル名が正しいかを確認する |