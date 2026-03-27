from flask import Flask, request, jsonify
import os
import cv2
from ultralytics import YOLO

app = Flask(__name__)

# 🔥 Load model once
model = YOLO("weights/best1.pt")

@app.route('/detect', methods=['POST'])
def detect():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded'}), 400

    image_file = request.files['image']

    # Save image temporarily
    os.makedirs('temp', exist_ok=True)
    image_path = os.path.join('temp', image_file.filename)
    image_file.save(image_path)

    # Read image
    img = cv2.imread(image_path)

    # Resize (same as live for consistency)
    img = cv2.resize(img, (320, 240))

    # Run detection
    results = model(img)

    detected = False
    confidence = 0

    for r in results:
        boxes = r.boxes
        if boxes is not None:
            for box in boxes:
                conf = float(box.conf[0])

                # Same filtering as live
                if conf > 0.3:
                    detected = True
                    confidence = round(conf, 2)
                    break

    # Remove temp file
    os.remove(image_path)

    return jsonify({
        'detected': detected,
        'type': 'waste' if detected else 'none',
        'confidence': confidence
    })


if __name__ == '__main__':
    app.run(port=5002)