"""
画像から物体を判定する部品。

画像（NumPy配列）を受け取り、判定結果のリストを返すだけで、
カメラ取得や通信の処理は持たない。
ローカル版・AWS版のどちらからも共通で使う。
"""

from dataclasses import dataclass
from pathlib import Path

import cv2

from core.coco_labels import COCO_LABELS

# プロジェクトの一番上のフォルダ（このファイルの2つ上）
PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_MODEL_PATH = (
    PROJECT_ROOT / "models" / "ssd_mobilenet_v2_coco_2018_03_29"
    / "frozen_inference_graph.pb"
)
DEFAULT_CONFIG_PATH = (
    PROJECT_ROOT / "models" / "ssd_mobilenet_v2_coco_2018_03_29.pbtxt"
)

# モデルが学習時に想定している入力画像のサイズ
INPUT_SIZE = (300, 300)


@dataclass
class Detection:
    """判定結果1件分。"""

    label: str    # 物体の名前
    score: float  # 確からしさ（0.0〜1.0）
    box: tuple    # 枠の位置（左, 上, 右, 下）のピクセル座標


class Detector:
    """学習済みモデルで物体を判定するクラス。"""

    def __init__(self, model_path=DEFAULT_MODEL_PATH,
                 config_path=DEFAULT_CONFIG_PATH, score_threshold=0.5):
        if not Path(model_path).exists():
            raise FileNotFoundError(f"モデルが見つかりません: {model_path}")
        if not Path(config_path).exists():
            raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")

        self._net = cv2.dnn.readNetFromTensorflow(
            str(model_path), str(config_path)
        )
        # この値より確からしさが低い結果は捨てる
        self._score_threshold = score_threshold

    def detect(self, image):
        """画像を判定し、Detection のリストを返す。"""
        height, width = image.shape[:2]

        # モデルの入力形式に変換する
        # （300x300に縮小し、OpenCVのBGRをモデルが学習したRGBの順に並べ替える）
        blob = cv2.dnn.blobFromImage(
            image, size=INPUT_SIZE, swapRB=True, crop=False
        )
        self._net.setInput(blob)
        output = self._net.forward()

        # output の形は (1, 1, 件数, 7)
        # 各行: [画像番号, クラスID, 確からしさ, 左, 上, 右, 下]
        # 座標は 0.0〜1.0 の割合なので、元画像のピクセルに戻す
        results = []
        for row in output[0, 0]:
            score = float(row[2])
            if score < self._score_threshold:
                continue

            class_id = int(row[1])
            label = COCO_LABELS.get(class_id, f"unknown({class_id})")

            left = int(row[3] * width)
            top = int(row[4] * height)
            right = int(row[5] * width)
            bottom = int(row[6] * height)

            results.append(Detection(label, score, (left, top, right, bottom)))

        return results