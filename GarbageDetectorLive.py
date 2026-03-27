import cv2
import math
import cvzone
from ultralytics import YOLO

# Use DroidCam IP
cap = cv2.VideoCapture("http://192.168.0.222:4747/video")

# Load model
model = YOLO("weights/best1.pt")
frame_skip = 2
count = 0

while True:
    success, img = cap.read()
    if not success:
        break

    count += 1
    if count % frame_skip != 0:
        continue

    img = cv2.resize(img, (320, 240))

    results = model(img, stream=False)

    detected = False  # to check if anything detected

    
    for r in results:
        boxes = r.boxes
        for box in boxes:
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

            w, h = x2 - x1, y2 - y1

            conf = float(box.conf[0])
            cls = int(box.cls[0])

            # 🔥 Balanced filtering
            if conf > 0.3 and w*h < 200000:
                detected = True

                cvzone.cornerRect(img, (x1, y1, w, h), t=2)

                cvzone.putTextRect(
                    img,
                    f'Waste {round(conf, 2)}',
                    (max(0, x1), max(35, y1)),
                    scale=1,
                    thickness=1
                )

    # Show status on screen
    if detected:
        cv2.putText(img, "DETECTED", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    else:
        cv2.putText(img, "NO DETECTION", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("Garbage Detection (Phone Camera)", img)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()