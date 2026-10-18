"""
カメラからフレーム（画像）を取得するクラス

サーバーや判定処理からはこのクラスを通してカメラを使う。
カメラ以外の処理（通信・判定）は持たない。
"""

import sys  # システム情報を取得するための標準ライブラリ
import cv2  # OpenCVを使ってカメラ映像を取得する
import threading  # スレッド間でカメラアクセスを同期するためのロック用


""" USB Webカメラを扱うクラス """
class Camera:

    # 起動直後の自動露出の調整待ち（この間のフレームは破棄する）
    WARMUP_FRAMES = 30

    # コンストラクタとカメラ操作のメソッドを提供
    def __init__(self, index=0):
        # Windowsでは DirectShow を使い、それ以外のOSはOpenCVに自動選択させる
        if sys.platform == "win32":
            backend = cv2.CAP_DSHOW
        else:
            backend = cv2.CAP_ANY
        # カメラを開く
        self._cap = cv2.VideoCapture(index, backend)
        
        # カメラが正しく開けたか確認する
        if not self._cap.isOpened():
            # 他のアプリ（カメラアプリ等）が使用中だと開けないことがある
            raise RuntimeError(f"カメラ {index} を開けませんでした")

        # 複数のスレッドから同時にカメラを読まないようにするロック
        self._lock = threading.Lock()

        # 起動直後の自動露出の調整が終わるまでのフレームを破棄する
        for _ in range(self.WARMUP_FRAMES):
            self._cap.read()

    # 1フレーム取得するメソッド
    def read(self):
        """1フレーム取得する。取得できなければ None を返す。"""
        with self._lock:
            ok, frame = self._cap.read()
        return frame if ok else None

    # カメラを解放するメソッド
    def release(self):
        """カメラを解放する（解放しないと他のアプリから使えなくなる）。"""
        self._cap.release()


""" 単体での動作確認用 """
if __name__ == "__main__":
    # 単体での動作確認用：1枚取得して情報を表示する
    camera = Camera()
    try:
        frame = camera.read()
        if frame is None:
            print("フレームを取得できませんでした")
        else:
            print("画像サイズ:", frame.shape)
            print("平均の明るさ:", frame.mean())
    finally:
        camera.release()