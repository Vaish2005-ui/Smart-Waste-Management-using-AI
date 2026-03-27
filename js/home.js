let selectedImage = null;

// Image Upload Preview
document.getElementById("imageInput").addEventListener("change", function(e){
  const file = e.target.files[0];
  if (!file) return;

  selectedImage = file;

  const reader = new FileReader();
  reader.onload = function(e){
    const img = document.getElementById("preview");
    img.src = e.target.result;
    img.style.display = "block";
  };
  reader.readAsDataURL(file);
});

// Redirect to detect page
function goToDetect(){
  if (!selectedImage){
    alert("Please upload image first!");
    return;
  }

  localStorage.setItem("image", document.getElementById("preview").src);
  window.location.href = "detect.html";
}

// CAMERA
let stream;

function startCamera(){
  navigator.mediaDevices.getUserMedia({ video: true })
  .then(s => {
    stream = s;
    const video = document.getElementById("video");
    video.srcObject = stream;
    video.style.display = "block";
  });
}

function capture(){
  const video = document.getElementById("video");

  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;

  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0);

  const imgData = canvas.toDataURL("image/png");

  localStorage.setItem("image", imgData);

  // Stop camera
  stream.getTracks().forEach(track => track.stop());

  window.location.href = "detect.html";
}