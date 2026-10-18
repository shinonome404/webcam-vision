const video = document.querySelector("#camera");
const canvas = document.querySelector("#overlay");
const context = canvas.getContext("2d");
const cameraView = document.querySelector("#camera-view");
const startButton = document.querySelector("#start-camera");
const stopButton = document.querySelector("#stop-camera");
const cameraSelect = document.querySelector("#camera-select");
const cameraStatus = document.querySelector("#camera-status");
const modelLoading = document.querySelector("#model-loading");
const detectionList = document.querySelector("#detection-list");
const detectionCount = document.querySelector("#detection-count");
const detectionSummary = document.querySelector("#detection-summary");
const chatForm = document.querySelector("#chat-form");
const chatInput = document.querySelector("#chat-input");
const sendButton = document.querySelector("#send-message");
const chatMessages = document.querySelector("#chat-messages");
const aiStatus = document.querySelector("#ai-status");

let stream;
let model;
let detections = [];
let detecting = false;
let animationFrame;
let conversation = [];

function showMessage(text, role = "assistant") {
  const row = document.createElement("div");
  row.className = `chat-message ${role === "user" ? "user-message" : "assistant-message"}`;
  if (role !== "user") {
    const avatar = document.createElement("span");
    avatar.className = "message-avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = "✳";
    row.append(avatar);
  }
  const bubble = document.createElement("p");
  bubble.textContent = text;
  row.append(bubble);
  chatMessages.append(row);
  chatMessages.scrollTop = chatMessages.scrollHeight;
  return row;
}

async function loadCameras() {
  if (!navigator.mediaDevices?.enumerateDevices) return;
  const devices = await navigator.mediaDevices.enumerateDevices();
  const cameras = devices.filter((device) => device.kind === "videoinput");
  cameraSelect.replaceChildren(new Option("自動選択", ""));
  cameras.forEach((camera, index) => {
    cameraSelect.add(new Option(camera.label || `カメラ ${index + 1}`, camera.deviceId));
  });
  cameraSelect.disabled = cameras.length === 0;
}

async function openCamera() {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("このブラウザーではカメラを利用できません。localhost または HTTPS で開いてください。");
  }
  const selectedCamera = cameraSelect.value;
  const constraints = {
    audio: false,
    video: selectedCamera ? { deviceId: { exact: selectedCamera } } : true,
  };
  stream = await navigator.mediaDevices.getUserMedia(constraints);
  video.srcObject = stream;
  await video.play();
  cameraView.classList.add("streaming");
  cameraStatus.classList.add("active");
  cameraStatus.lastChild.textContent = "ライブ";
  startButton.classList.add("hidden");
  stopButton.classList.remove("hidden");
  cameraSelect.disabled = false;
  await loadCameras();
  if (!model) {
    modelLoading.classList.remove("hidden");
    try {
      if (!window.cocoSsd || !window.tf) {
        throw new Error("検出モデルを読み込めません。インターネット接続を確認してください。");
      }
      model = await window.cocoSsd.load();
    } finally {
      modelLoading.classList.add("hidden");
    }
  }
  detecting = true;
  detectFrame();
}

async function detectFrame() {
  if (!detecting || !model || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
    animationFrame = requestAnimationFrame(detectFrame);
    return;
  }
  try {
    detections = await model.detect(video);
    drawDetections();
    updateDetections();
  } catch (error) {
    showMessage(`物体検出に失敗しました: ${error.message}`);
    stopCamera();
    return;
  }
  animationFrame = requestAnimationFrame(detectFrame);
}

function drawDetections() {
  const width = video.videoWidth;
  const height = video.videoHeight;
  if (!width || !height) return;
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }
  context.clearRect(0, 0, width, height);
  context.lineWidth = Math.max(2, width / 400);
  context.font = `600 ${Math.max(12, width / 55)}px "DM Sans", sans-serif`;
  detections.forEach(({ bbox, class: label, score }) => {
    const [x, y, boxWidth, boxHeight] = bbox;
    const labelText = `${label} ${Math.round(score * 100)}%`;
    const textWidth = context.measureText(labelText).width;
    const labelHeight = Math.max(23, width / 36);
    const labelY = Math.max(0, y - labelHeight);
    context.strokeStyle = "#62d9bd";
    context.fillStyle = "#62d9bd";
    context.lineWidth = Math.max(2, width / 400);
    context.strokeRect(x, y, boxWidth, boxHeight);
    context.fillRect(x, labelY, textWidth + 13, labelHeight);
    context.fillStyle = "#10211f";
    context.fillText(labelText, x + 6, labelY + labelHeight * 0.69);
  });
}

function updateDetections() {
  detectionCount.textContent = String(detections.length);
  detectionSummary.textContent = detections.length
    ? "AIが映像から見つけた物体です。"
    : "現在、物体を検出していません。";
  if (!detections.length) {
    detectionList.innerHTML = '<div class="empty-detections">検出された物体はまだありません</div>';
    return;
  }
  detectionList.replaceChildren(...detections.map(({ class: label, score }) => {
    const chip = document.createElement("div");
    chip.className = "detection-chip";
    const name = document.createElement("strong");
    name.textContent = label;
    const confidence = document.createElement("span");
    confidence.textContent = `${Math.round(score * 100)}%`;
    chip.append(name, confidence);
    return chip;
  }));
}

function stopCamera() {
  detecting = false;
  cancelAnimationFrame(animationFrame);
  stream?.getTracks().forEach((track) => track.stop());
  stream = undefined;
  video.srcObject = null;
  context.clearRect(0, 0, canvas.width, canvas.height);
  detections = [];
  updateDetections();
  cameraView.classList.remove("streaming");
  cameraStatus.classList.remove("active");
  cameraStatus.lastChild.textContent = "停止中";
  stopButton.classList.add("hidden");
  startButton.classList.remove("hidden");
  cameraSelect.disabled = false;
}

function setAiStatus(enabled) {
  aiStatus.classList.toggle("enabled", enabled);
  aiStatus.classList.toggle("unavailable", !enabled);
  aiStatus.lastChild.textContent = enabled
    ? "AIチャットを利用できます"
    : "AIチャットにはサーバー側のAPIキー設定が必要です";
}

async function checkAiStatus() {
  try {
    const response = await fetch("/api/status");
    const result = await response.json();
    setAiStatus(response.ok && result.ai_enabled);
  } catch {
    setAiStatus(false);
  }
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = chatInput.value.trim();
  if (!question || sendButton.disabled) return;

  conversation.push({ role: "user", content: question });
  showMessage(question, "user");
  chatInput.value = "";
  sendButton.disabled = true;
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: conversation.slice(-20),
        detections: detections.map(({ class: label, score }) => ({ class: label, score })),
      }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "AIへの接続に失敗しました。");
    conversation.push({ role: "assistant", content: result.answer });
    showMessage(result.answer);
  } catch (error) {
    conversation.pop();
    showMessage(error.message);
  } finally {
    sendButton.disabled = false;
    chatInput.focus();
  }
});

startButton.addEventListener("click", async () => {
  startButton.disabled = true;
  try {
    await openCamera();
  } catch (error) {
    showMessage(error.message);
    stopCamera();
  } finally {
    startButton.disabled = false;
  }
});
stopButton.addEventListener("click", stopCamera);
cameraSelect.addEventListener("change", async () => {
  if (!stream) return;
  stopCamera();
  startButton.click();
});
navigator.mediaDevices?.addEventListener?.("devicechange", loadCameras);

checkAiStatus();
loadCameras().catch(() => {});
