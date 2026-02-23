'use strict';

const dropZone      = document.getElementById('drop-zone');
const fileInput     = document.getElementById('file-input');
const uploadBtn     = document.getElementById('upload-btn');
const uploadSection = document.getElementById('upload-section');
const progressSection = document.getElementById('progress-section');
const progressBar   = document.getElementById('progress-bar');
const progressLabel = document.getElementById('progress-label');
const resultList    = document.getElementById('result-list');
const downloadSection = document.getElementById('download-section');
const downloadLink  = document.getElementById('download-link');
const resetBtn      = document.getElementById('reset-btn');

let selectedFiles = [];

// --- File selection ---
function setFiles(files) {
  selectedFiles = Array.from(files);
  uploadBtn.disabled = selectedFiles.length === 0;
  if (selectedFiles.length > 0) {
    dropZone.querySelector('p').textContent =
      `${selectedFiles.length} file(s) selected`;
  }
}

fileInput.addEventListener('change', () => setFiles(fileInput.files));
dropZone.addEventListener('click', (e) => {
  if (e.target.tagName !== 'LABEL') fileInput.click();
});
dropZone.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') fileInput.click();
});
dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  setFiles(e.dataTransfer.files);
});

// --- Upload ---
uploadBtn.addEventListener('click', async () => {
  if (selectedFiles.length === 0) return;

  uploadSection.hidden = true;
  progressSection.hidden = false;
  progressBar.style.width = '0%';
  progressLabel.textContent = 'Uploading files…';
  resultList.innerHTML = '';

  const formData = new FormData();
  selectedFiles.forEach(f => formData.append('files', f));

  let sessionId;
  try {
    const resp = await fetch('/upload', { method: 'POST', body: formData });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.error || 'Upload failed');
    }
    const data = await resp.json();
    sessionId = data.session_id;
  } catch (err) {
    progressLabel.textContent = `Upload error: ${err.message}`;
    return;
  }

  // --- SSE stream ---
  const es = new EventSource(`/stream/${sessionId}`);
  let total = selectedFiles.length;
  let done = 0;

  es.onmessage = (e) => {
    const msg = JSON.parse(e.data);

    if (msg.type === 'start') {
      total = msg.total;
      progressLabel.textContent = `Processing 0 / ${total}…`;
    } else if (msg.type === 'progress') {
      progressLabel.textContent = `Processing ${msg.index + 1} / ${total}: ${msg.filename}`;
    } else if (msg.type === 'done') {
      done++;
      progressBar.style.width = `${(done / total) * 100}%`;
      const li = document.createElement('li');
      li.className = 'ok';
      li.textContent = `✓ ${msg.filename}`;
      resultList.appendChild(li);
    } else if (msg.type === 'error') {
      const li = document.createElement('li');
      li.className = 'err';
      li.textContent = `✗ ${msg.filename || ''}: ${msg.message}`;
      resultList.appendChild(li);
    } else if (msg.type === 'complete') {
      es.close();
      progressBar.style.width = '100%';
      progressLabel.textContent = 'Done! Building Excel…';
      downloadLink.href = msg.download_url;
      progressSection.hidden = true;
      downloadSection.hidden = false;
    }
  };

  es.onerror = () => {
    es.close();
    progressLabel.textContent = 'Connection error. Please try again.';
  };
});

// --- Reset ---
resetBtn.addEventListener('click', () => {
  selectedFiles = [];
  fileInput.value = '';
  uploadBtn.disabled = true;
  dropZone.querySelector('p').textContent = 'Drag & drop receipts here';
  downloadSection.hidden = true;
  progressSection.hidden = true;
  uploadSection.hidden = false;
});
