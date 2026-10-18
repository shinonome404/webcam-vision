import cv2

CAMERA_INDEX = 0

cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
if not cap.isOpened():
    print(f"カメラ {CAMERA_INDEX} を開けませんでした")
    raise SystemExit(1)

# 起動直後は暗いので、数十フレーム読み捨てて明るさ調整を待つ
for _ in range(30):
    ok, frame = cap.read()

cap.release()

if not ok:
    print("フレームを取得できませんでした")
    raise SystemExit(1)

print("画像サイズ:", frame.shape)
print("平均の明るさ:", frame.mean())
cv2.imwrite("snapshot.jpg", frame)
print("snapshot.jpg を保存しました")