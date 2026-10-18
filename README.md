# Webcam Vision

USB Webカメラの映像から物体を検出し、検出結果について対話型AIに質問できるブラウザーアプリです。物体検出には TensorFlow.js と COCO-SSD を使用します。

## 起動方法

Python 3.9 以降を用意し、リポジトリのディレクトリで次を実行します。

```sh
python3 server.py
```

ブラウザーで <http://127.0.0.1:8000> を開き、カメラへのアクセスを許可してください。カメラは localhost または HTTPS の安全な接続で利用できます。TensorFlow.js と COCO-SSD は初回に CDN から読み込まれるため、インターネット接続が必要です。

## 対話型AI

AIチャットを利用する場合は、OpenAI API キーを環境変数に設定してからサーバーを起動します。

```sh
OPENAI_API_KEY=your-api-key python3 server.py
```

必要に応じて `OPENAI_MODEL`（既定値: `gpt-4o-mini`）で利用モデルを変更できます。API キーはサーバー側だけで使用し、ブラウザーには送信・保存しません。キーを設定しない場合もカメラと物体検出は利用できますが、チャットは利用できません。API の利用には OpenAI のアカウントと利用料金が発生する場合があります。

サーバーの待受アドレスとポートは `HOST`（既定値: `127.0.0.1`）と `PORT`（既定値: `8000`）で変更できます。カメラとAPIキーを保護するため、信頼できるネットワーク以外にサーバーを公開しないでください。

## テスト

```sh
python3 -m unittest discover -s tests
```
