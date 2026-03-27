const imageInput = document.getElementById('imageInput');
const uploadArea = document.getElementById('uploadArea');
const originalPreview = document.getElementById('originalPreview');
const detectBtn = document.getElementById('detectBtn');
const clearBtn = document.getElementById('clearBtn');
const loading = document.getElementById('loading');
const resultContent = document.getElementById('resultContent');

// NEW (Camera)
const cameraBtn = document.getElementById("cameraBtn");
const video = document.getElementById("camera");
const canvas = document.getElementById("canvas");

let selectedFile = null;
let stream = null;
let cameraActive = false;

// ================= UPLOAD =================
uploadArea.addEventListener('click', () => imageInput.click());

imageInput.addEventListener('change', e => {
  if (e.target.files[0]) handleFile(e.target.files[0]);
});

uploadArea.addEventListener('dragover', e => { 
  e.preventDefault(); 
  uploadArea.style.borderColor = '#10b981'; 
});

uploadArea.addEventListener('dragleave', () => { 
  uploadArea.style.borderColor = '#22c55e'; 
});

uploadArea.addEventListener('drop', e => {
  e.preventDefault();
  uploadArea.style.borderColor = '#22c55e';
  if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
});

function handleFile(file) {
  if (!file.type.startsWith('image/')) return alert("Please upload an image only!");

  selectedFile = file;

  const reader = new FileReader();
  reader.onload = ev => {
    originalPreview.src = ev.target.result;
    originalPreview.style.display = 'block';
    detectBtn.disabled = false;
  };
  reader.readAsDataURL(file);
}

// ================= CAMERA =================
cameraBtn.addEventListener("click", async () => {

  // START CAMERA
  if (!cameraActive) {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: true });
      video.srcObject = stream;
      video.style.display = "block";

      cameraBtn.textContent = "📸 Capture Image";
      cameraActive = true;
    } catch (err) {
      alert("Camera not accessible!");
    }
  } 

  // CAPTURE IMAGE
  else {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0);

    canvas.toBlob((blob) => {
      selectedFile = new File([blob], "capture.png", { type: "image/png" });

      // Preview
      originalPreview.src = URL.createObjectURL(blob);
      originalPreview.style.display = "block";

      detectBtn.disabled = false;

      // Stop camera
      stream.getTracks().forEach(track => track.stop());
      video.style.display = "none";

      cameraBtn.textContent = "📷 Use Camera";
      cameraActive = false;
    });
  }
});

// ================= DETECTION =================
detectBtn.addEventListener('click', async () => {
  if (!selectedFile) return;

  loading.style.display = 'block';
  resultContent.innerHTML = '';
  detectBtn.disabled = true;

  const formData = new FormData();
  formData.append('image', selectedFile);

  try {
    const res = await fetch('http://127.0.0.1:5002/detect', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();

    let html = `<div class="comparison-grid">`;

    html += `
      <div>
        <small>Original Image</small>
        <img src="${originalPreview.src}" style="width:100%; border-radius:16px; margin-top:8px;" />
      </div>`;

    if (data.annotated_image) {
      html += `
        <div>
          <small>AI Detection Result</small>
          <img src="data:image/jpeg;base64,${data.annotated_image}" 
               style="width:100%; border-radius:16px; margin-top:8px;" />
        </div>`;
    }

    html += `</div>`;

    if (data.detected) {
      html += `<div class="status" style="color:#22c55e;">✅ GARBAGE DETECTED</div>`;

      data.detections.forEach(d => {
        const percent = Math.round(d.confidence * 100);

        html += `
          <div style="margin:20px 0;">
            <strong>${d.class}</strong>
            <div class="confidence-bar">
              <div class="fill" style="width:${percent}%"></div>
            </div>
            <small>${percent}% Confidence</small>
          </div>`;
      });

    } else {
      html += `<div class="status" style="color:#ef4444;">❌ NO GARBAGE DETECTED</div>`;
    }

    resultContent.innerHTML = html;

  } catch (err) {
    resultContent.innerHTML = `
      <p style="color:red; text-align:center;">
        ❌ Backend is not running.<br>Run: python app.py
      </p>`;
  } finally {
    loading.style.display = 'none';
    detectBtn.disabled = false;
  }
});

// ================= RESET =================
clearBtn.addEventListener('click', () => {

  // Stop camera if running
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
    video.style.display = "none";
    cameraActive = false;
  }

  originalPreview.style.display = 'none';

  resultContent.innerHTML = `
    <div style="text-align:center; padding:5rem 1rem; opacity:0.6;">
      <span style="font-size:5rem;">♻️</span>
      <p>Upload image to detect waste</p>
    </div>`;

  detectBtn.disabled = true;
  selectedFile = null;

  cameraBtn.textContent = "📷 Use Camera";
});