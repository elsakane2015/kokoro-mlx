const form = document.querySelector("#speech-form");
const text = document.querySelector("#text");
const characterCount = document.querySelector("#character-count");
const voice = document.querySelector("#voice");
const voiceNote = document.querySelector("#voice-note");
const language = document.querySelector("#language");
const speed = document.querySelector("#speed");
const speedValue = document.querySelector("#speed-value");
const generateButton = document.querySelector("#generate-button");
const serverStatus = document.querySelector("#server-status");
const serverStatusText = document.querySelector("#server-status-text");
const resultPanel = document.querySelector("#result-panel");
const resultTitle = document.querySelector("#result-title");
const resultMessage = document.querySelector("#result-message");
const audioPlayer = document.querySelector("#audio-player");
const downloadButton = document.querySelector("#download-button");
const localAddress = document.querySelector("#local-address");

let audioUrl = null;

const voiceGroups = {
  af: "美式英语 · 女声",
  am: "美式英语 · 男声",
  bf: "英式英语 · 女声",
  bm: "英式英语 · 男声",
  ef: "西班牙语 · 女声",
  em: "西班牙语 · 男声",
  ff: "法语 · 女声",
  hf: "印地语 · 女声",
  hm: "印地语 · 男声",
  if: "意大利语 · 女声",
  im: "意大利语 · 男声",
  jf: "日语 · 女声",
  jm: "日语 · 男声",
  pf: "葡萄牙语 · 女声",
  pm: "葡萄牙语 · 男声",
  zf: "普通话 · 女声",
  zm: "普通话 · 男声",
};

function setServerStatus(state, message) {
  serverStatus.dataset.state = state;
  serverStatusText.textContent = message;
}

function updateCharacterCount() {
  characterCount.textContent = text.value.length.toString();
}

function updateSpeed() {
  speedValue.textContent = `${Number(speed.value).toFixed(2)}×`;
}

function humanizeVoice(name) {
  return name
    .slice(3)
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function populateVoices(voices, defaultVoice) {
  voice.replaceChildren();
  const grouped = new Map();

  for (const name of voices) {
    const prefix = name.slice(0, 2);
    if (!grouped.has(prefix)) grouped.set(prefix, []);
    grouped.get(prefix).push(name);
  }

  for (const [prefix, names] of grouped) {
    const group = document.createElement("optgroup");
    group.label = voiceGroups[prefix] || prefix.toUpperCase();
    for (const name of names) {
      const option = document.createElement("option");
      option.value = name;
      option.textContent = `${humanizeVoice(name)} (${name})`;
      option.selected = name === defaultVoice;
      group.append(option);
    }
    voice.append(group);
  }

  voice.disabled = false;
  updateVoiceNote();
}

function updateVoiceNote() {
  const prefix = voice.value.slice(0, 2);
  voiceNote.textContent = voiceGroups[prefix] || "音色会自动选择对应语言。";
}

function describeError(payload, status) {
  if (typeof payload?.detail === "string") return payload.detail;
  if (Array.isArray(payload?.detail)) {
    return payload.detail.map((item) => item.msg).join("；");
  }
  return `请求失败（HTTP ${status}）`;
}

async function loadServerData() {
  try {
    const [healthResponse, voicesResponse] = await Promise.all([
      fetch("/api/health"),
      fetch("/api/voices"),
    ]);
    if (!healthResponse.ok || !voicesResponse.ok) throw new Error("服务初始化失败");

    const health = await healthResponse.json();
    const voiceData = await voicesResponse.json();
    populateVoices(voiceData.voices, voiceData.default_voice);
    setServerStatus("ready", `模型已就绪 · ${health.voice_count} 个音色`);
  } catch (error) {
    setServerStatus("error", error.message || "无法连接本地服务");
    voice.replaceChildren(new Option("音色加载失败", ""));
  }
}

function setGenerating(isGenerating) {
  generateButton.disabled = isGenerating;
  generateButton.dataset.loading = isGenerating.toString();
  generateButton.querySelector(".button-label").textContent = isGenerating ? "正在生成" : "生成语音";
}

function resetAudioUrl() {
  if (audioUrl) URL.revokeObjectURL(audioUrl);
  audioUrl = null;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setGenerating(true);
  resultPanel.dataset.state = "loading";
  resultTitle.textContent = "正在生成语音";
  resultMessage.textContent = "模型正在本地处理文本，请保持页面打开。";
  audioPlayer.hidden = true;
  downloadButton.hidden = true;

  try {
    const sampleRate = document.querySelector('input[name="sample_rate"]:checked').value;
    const payload = {
      text: text.value,
      voice: voice.value,
      language: language.value || null,
      speed: Number(speed.value),
      sample_rate: Number(sampleRate),
    };
    const response = await fetch("/api/speech", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let details = null;
      try {
        details = await response.json();
      } catch {
        details = null;
      }
      throw new Error(describeError(details, response.status));
    }

    const blob = await response.blob();
    resetAudioUrl();
    audioUrl = URL.createObjectURL(blob);
    audioPlayer.src = audioUrl;
    downloadButton.href = "/api/speech/download";
    audioPlayer.hidden = false;
    downloadButton.hidden = false;

    const duration = Number(response.headers.get("X-Audio-Duration") || 0);
    const rate = Number(response.headers.get("X-Audio-Sample-Rate") || sampleRate) / 1000;
    resultPanel.dataset.state = "success";
    resultTitle.textContent = "语音已生成";
    resultMessage.textContent = `${duration.toFixed(2)} 秒 · ${rate} kHz · ${voice.value}`;
  } catch (error) {
    resultPanel.dataset.state = "error";
    resultTitle.textContent = "生成失败";
    resultMessage.textContent = error.message || "未知错误";
  } finally {
    setGenerating(false);
  }
});

text.addEventListener("input", updateCharacterCount);
speed.addEventListener("input", updateSpeed);
voice.addEventListener("change", updateVoiceNote);
window.addEventListener("beforeunload", resetAudioUrl);

localAddress.textContent = window.location.origin;
updateCharacterCount();
updateSpeed();
loadServerData();

downloadButton.addEventListener("click", (event) => {
  const handler = window.webkit?.messageHandlers?.downloadAudio;
  if (!handler) return;
  event.preventDefault();
  handler.postMessage({ filename: "speech.wav" });
});
