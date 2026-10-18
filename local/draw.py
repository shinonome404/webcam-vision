"""
判定結果を画像に描き込む部品（ローカル表示用）。
"""

import cv2

BOX_COLOR = (0, 255, 0)  # 枠の色（BGRの順なので緑）


def draw_detections(image, detections):
    """画像に判定結果の枠と名前を描き込む（画像を直接書き換える）。"""
    for d in detections:
        left, top, right, bottom = d.box
        cv2.rectangle(image, (left, top), (right, bottom), BOX_COLOR, 2)

        text = f"{d.label} {d.score:.2f}"
        # 文字が画像の上にはみ出さないよう、枠の上端が狭いときは枠の内側に書く
        if top < 20:
            text_y = top + 20
        else:
            text_y = top - 5
        cv2.putText(image, text, (left, text_y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, BOX_COLOR, 2)