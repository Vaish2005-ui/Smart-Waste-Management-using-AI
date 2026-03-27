from flask import Flask, jsonify, request, send_from_directory
import base64
import os
from datetime import datetime
from urllib.parse import urlparse
import requests
import numpy as np

import cv2
from ultralytics import YOLO

app = Flask(__name__, static_folder=".", static_url_path="")

# Load model once at startup
model = YOLO("weights/best1.pt")

# In-memory history for frontend stats
history = []


def _safe_confidence(value):
    try:
        return round(float(value), 4)
    except Exception:
        return 0.0


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/<path:path>")
def static_proxy(path):
    return send_from_directory(".", path)


@app.route("/history", methods=["GET"])
def get_history():
    return jsonify(history)


@app.route("/capture-droidcam", methods=["POST"])
def capture_droidcam():
    payload = request.get_json(silent=True) or {}
    raw_url = str(payload.get("url", "")).strip()
    if not raw_url:
        return jsonify({"error": "Missing DroidCam URL"}), 400

    parsed = urlparse(raw_url)
    if parsed.scheme not in {"http", "https"}:
        return jsonify({"error": "Invalid URL scheme"}), 400
    if not parsed.hostname:
        return jsonify({"error": "Invalid URL"}), 400

    print(f"DEBUG: [capture-droidcam] Fetching from: {raw_url}")

    try:
        # Add headers that DroidCam expects
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Connection": "keep-alive"
        }

        response = requests.get(raw_url, stream=True, timeout=10, headers=headers)
        print(f"DEBUG: [capture-droidcam] Status code: {response.status_code}")
        print(f"DEBUG: [capture-droidcam] Content-Type: {response.headers.get('Content-Type')}")

        if response.status_code != 200:
            return jsonify({"error": f"DroidCam returned {response.status_code}"}), 400

        frame = None
        buffer = b""
        chunk_count = 0
        ffd8_found = False

        for chunk in response.iter_content(chunk_size=4096):
            if not chunk:
                break

            chunk_count += 1
            buffer += chunk
            print(f"DEBUG: [capture-droidcam] Chunk {chunk_count}: {len(chunk)} bytes, buffer total: {len(buffer)}")

            # Look for JPEG start marker (FFD8)
            if not ffd8_found and b"\xff\xd8" in buffer:
                ffd8_found = True
                jpeg_start = buffer.find(b"\xff\xd8")
                print(f"DEBUG: [capture-droidcam] Found JPEG start at position {jpeg_start}")
                buffer = buffer[jpeg_start:]  # Keep from JPEG start onwards

            # Look for JPEG end marker (FFD9) - only search after we found start
            if ffd8_found and b"\xff\xd9" in buffer:
                jpeg_end = buffer.find(b"\xff\xd9") + 2
                jpg_data = buffer[:jpeg_end]

                print(f"DEBUG: [capture-droidcam] Found JPEG end, frame size: {len(jpg_data)} bytes")

                try:
                    nparr = np.frombuffer(jpg_data, np.uint8)
                    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    if frame is not None and frame.size > 0:
                        print(f"DEBUG: [capture-droidcam] Successfully decoded frame: {frame.shape}")
                        break
                    else:
                        print(f"DEBUG: [capture-droidcam] Frame decode returned None or empty")
                        # Try next frame
                        buffer = buffer[jpeg_end:]
                        ffd8_found = False
                except Exception as e:
                    print(f"DEBUG: [capture-droidcam] Decode error: {str(e)}, trying next frame...")
                    buffer = buffer[jpeg_end:]
                    ffd8_found = False
                    continue

            # Prevent buffer overflow - keep sliding window
            if len(buffer) > 1048576:  # 1MB
                if ffd8_found:
                    # Keep from last FFD8 onwards
                    last_ffd8 = buffer.rfind(b"\xff\xd8", 0, len(buffer) - 65536)
                    if last_ffd8 > 0:
                        print(f"DEBUG: [capture-droidcam] Trimming buffer, keeping from FFD8 at {last_ffd8}")
                        buffer = buffer[last_ffd8:]
                    else:
                        buffer = buffer[-524288:]  # Keep last 512KB
                else:
                    buffer = buffer[-262144:]  # Keep last 256KB

        if frame is None:
            print(f"DEBUG: [capture-droidcam] No valid frame found after {chunk_count} chunks, buffer size: {len(buffer)}")
            # Debug: show what we have in buffer
            if b"\xff\xd8" in buffer:
                print(f"DEBUG: Has FFD8 but no FFD9")
            if b"\xff\xd9" in buffer:
                print(f"DEBUG: Has FFD9 but no FFD8")
            return jsonify({"error": "No valid JPEG frame in stream"}), 400

        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            print("DEBUG: [capture-droidcam] imencode failed")
            return jsonify({"error": "Failed to encode frame"}), 500

        print(f"DEBUG: [capture-droidcam] Successfully captured and encoded frame")
        return jsonify(
            {
                "image_base64": base64.b64encode(buffer).decode("utf-8"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    except requests.exceptions.Timeout:
        print("DEBUG: [capture-droidcam] Request timeout")
        return jsonify({"error": "DroidCam connection timeout"}), 408
    except requests.exceptions.ConnectionError as e:
        print(f"DEBUG: [capture-droidcam] Connection error: {str(e)}")
        return jsonify({"error": "Cannot connect to DroidCam"}), 400
    except Exception as e:
        print(f"DEBUG: [capture-droidcam] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error: {str(e)[:60]}"}), 500


@app.route("/detect", methods=["POST"])
def detect():
    if "image" not in request.files:
        print("DEBUG: No image in request.files")
        return jsonify({"error": "No image uploaded"}), 400

    image_file = request.files["image"]
    if not image_file or image_file.filename == "":
        print("DEBUG: No filename or empty file")
        return jsonify({"error": "Invalid image file"}), 400

    os.makedirs("temp", exist_ok=True)
    image_path = os.path.join("temp", image_file.filename)
    print(f"DEBUG: Saving image to {image_path}")
    image_file.save(image_path)

    img = cv2.imread(image_path)
    if img is None:
        print(f"DEBUG: cv2.imread failed for {image_path}")
        if os.path.exists(image_path):
            os.remove(image_path)
        return jsonify({"error": "Unable to read image"}), 400

    print(f"DEBUG: Image loaded, shape: {img.shape}")
    img = cv2.resize(img, (320, 240))
    print(f"DEBUG: Image resized to {img.shape}")
    annotated = img.copy()

    try:
        print("DEBUG: Running YOLO model...")
        results = model(img)
        print(f"DEBUG: Model returned {len(results)} result(s)")
    except Exception as e:
        print(f"DEBUG: YOLO model error: {str(e)}")
        if os.path.exists(image_path):
            os.remove(image_path)
        return jsonify({"error": f"Model error: {str(e)[:60]}"}), 500

    detections = []
    max_conf = 0.0

    for r in results:
        boxes = r.boxes
        if boxes is None:
            continue
        for box in boxes:
            conf = _safe_confidence(box.conf[0])
            cls_idx = int(box.cls[0])
            class_name = model.names.get(cls_idx, str(cls_idx))

            if conf > 0.3:
                max_conf = max(max_conf, conf)
                x1, y1, x2, y2 = box.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                detections.append(
                    {
                        "class": class_name,
                        "confidence": conf,
                        "bbox": [x1, y1, x2, y2],
                    }
                )

                cv2.rectangle(annotated, (x1, y1), (x2, y2), (57, 255, 122), 2)
                label = f"{class_name} {int(conf * 100)}%"
                cv2.putText(
                    annotated,
                    label,
                    (x1, max(16, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (57, 255, 122),
                    1,
                    cv2.LINE_AA,
                )

    detected = len(detections) > 0
    _, buffer = cv2.imencode(".jpg", annotated)
    annotated_b64 = base64.b64encode(buffer).decode("utf-8")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    response = {
        "detected": detected,
        "type": "waste" if detected else "none",
        "confidence": max_conf,
        "detections": detections,
        "annotated_image": annotated_b64,
        "timestamp": timestamp,
    }

    history.append(
        {
            "detected": detected,
            "confidence": max_conf,
            "detections": detections,
            "timestamp": timestamp,
        }
    )
    if len(history) > 500:
        del history[: len(history) - 500]

    if os.path.exists(image_path):
        os.remove(image_path)

    return jsonify(response)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002, debug=True)