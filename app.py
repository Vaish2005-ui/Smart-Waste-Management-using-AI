import streamlit as st
import cv2
import numpy as np
from ultralytics import YOLO

st.set_page_config(page_title="WasteWatch AI", page_icon="🗑️", layout="centered")

# ── SIMPLE CLEAN UI ─────────────────────────
st.markdown("""
<style>
body {
    background: linear-gradient(135deg, #0f172a, #1e293b);
    color: #e2e8f0;
    font-family: 'Segoe UI', sans-serif;
}
.block-container {
    max-width: 900px;
    padding: 2rem;
}
#MainMenu, footer, header {
    visibility: hidden;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #22c55e, #06b6d4);
    color: white !important;
}
img {
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# ── HEADER ─────────────────────────
st.markdown("## 🗑 WasteWatch AI")
st.caption("Detect waste using YOLOv8 (Upload or Live Camera)")

# ── MODEL ─────────────────────────
@st.cache_resource
def load_model():
    return YOLO("weights/best1.pt")

CLASS_LABELS = ['0', 'c', 'garbage', 'garbage_bag', 'sampah-detection', 'trash']

# ── CONFIDENCE ─────────────────────
conf_thresh = st.slider("Confidence Threshold", 0.10, 0.90, 0.30, 0.05)

# ── DETECTION FUNCTION ─────────────
def detect(img_bgr, conf_thresh):
    model = load_model()
    results = model(img_bgr, verbose=False)
    detections = []
    out = img_bgr.copy()

    for r in results:
        for box in r.boxes:
            conf = float(box.conf[0])
            if conf < conf_thresh:
                continue

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cls = int(box.cls[0])
            label = CLASS_LABELS[cls] if cls < len(CLASS_LABELS) else "waste"

            detections.append({"label": label, "conf": conf})

            cv2.rectangle(out, (x1, y1), (x2, y2), (16, 185, 129), 2)
            cv2.putText(out, f"{label} {conf:.0%}", (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (16,185,129), 2)

    return out, detections

# ── RESULT DISPLAY ─────────────────
def show_result(annotated_bgr, detections):
    rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
    st.image(rgb, use_container_width=True)

    if detections:
        st.error(f"⚠ Waste Detected ({len(detections)} objects)")
        for d in detections:
            st.write(f"- {d['label']} ({int(d['conf']*100)}%)")
    else:
        st.success("✅ Area Clean")

# ── TABS ──────────────────────────
tab1, tab2 = st.tabs(["📁 Upload Image", "📷 Camera (DroidCam)"])

# ── IMAGE UPLOAD ──────────────────
with tab1:
    uploaded = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])

    if uploaded:
        file_bytes = np.frombuffer(uploaded.read(), np.uint8)
        img_bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

        col1, col2 = st.columns(2)

        with col1:
            st.image(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB), caption="Original")

        with col2:
            with st.spinner("Detecting..."):
                annotated, dets = detect(img_bgr, conf_thresh)
            st.image(cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB), caption="Result")

        show_result(annotated, dets)

# ── DROIDCAM LIVE CAMERA ───────────
with tab2:
    st.info("Make sure your phone is connected via DroidCam and on same WiFi")

    ip = st.text_input("Enter DroidCam IP", "http://172.16.240.211:4747/")

    start = st.button("Start Camera")
    stop = st.button("Stop Camera")

    if "run_cam" not in st.session_state:
        st.session_state.run_cam = False

    if start:
        st.session_state.run_cam = True
    if stop:
        st.session_state.run_cam = False

    FRAME_WINDOW = st.image([])

    if st.session_state.run_cam:
        cap = cv2.VideoCapture(f"http://{ip}:4747/video")

        for i in range(200):  # limit frames to prevent crash
            ret, frame = cap.read()
            if not ret:
                st.error("Camera not working. Check IP.")
                break

            annotated, dets = detect(frame, conf_thresh)
            frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)

            FRAME_WINDOW.image(frame_rgb)

        cap.release()

# ── FOOTER ────────────────────────
st.markdown("---")
st.caption("WasteWatch AI · YOLOv8 · Custom Model")