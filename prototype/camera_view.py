import cv2

CAMERA_INDEX = 0

cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
if not cap.isOpened():
    print(f"カメラ {CAMERA_INDEX} を開けませんでした")
    raise SystemExit(1)

try:
    while True:
        ok, frame = cap.read()
        if not ok:
            print("フレームを取得できませんでした")
            break

        cv2.imshow("camera", frame)

        # 1ミリ秒キー入力を待つ。q で終了
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    cap.release()
    cv2.destroyAllWindows()