"""
静止画1枚を判定し、結果を表示して枠付き画像を保存する。

使い方（プロジェクトの一番上のフォルダで実行）:
    python -m local.detect_image 画像ファイルのパス
"""

import sys

import cv2

from core.detector import Detector
from local.draw import draw_detections

OUTPUT_PATH = "result.jpg"


def main():
    if len(sys.argv) < 2:
        print("使い方: python -m local.detect_image 画像ファイルのパス")
        return

    image = cv2.imread(sys.argv[1])
    if image is None:
        print(f"画像を読み込めませんでした: {sys.argv[1]}")
        return

    detector = Detector()
    detections = detector.detect(image)

    print(f"{len(detections)} 件見つかりました")
    for d in detections:
        print(f"  {d.label}  確からしさ: {d.score:.2f}  枠: {d.box}")

    draw_detections(image, detections)
    cv2.imwrite(OUTPUT_PATH, image)
    print(f"{OUTPUT_PATH} を保存しました")


if __name__ == "__main__":
    main()