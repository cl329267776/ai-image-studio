const state = { taskId: null, pollTimer: null };

async function upload() {
  const fileInput = document.getElementById('file');
  const promptInput = document.getElementById('prompt');
  if (!fileInput.files.length) { alert('请选择商品原图'); return; }
  const fd = new FormData();
  fd.append('file', fileInput.files[0]);
  fd.append('custom_prompt', promptInput.value);
  setProgress('上传中…');
  const resp = await fetch('/api/upload', { method: 'POST', body: fd });
  const data = await resp.json();
  state.taskId = data.task_id;
  startPoll();
}

function startPoll() {
  clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    const resp = await fetch(`/api/task/${state.taskId}`);
    const t = await resp.json();
    renderProgress(t);
    if (['done', 'partial', 'failed'].includes(t.status)) {
      clearInterval(state.pollTimer);
      renderResults(t);
      loadHistory();
    }
  }, 3000);
}

function renderProgress(t) {
  const map = { pending: '排队中…', generating: 'AI 生成中(约 1-3 分钟)…', done: '完成', partial: '部分完成', failed: '失败' };
  document.getElementById('progress').style.display = 'block';
  document.getElementById('progress').textContent = map[t.status] || t.status;
  if (t.error) document.getElementById('progress').textContent += ' ⚠ ' + t.error;
}

function renderResults(t) {
  const mainBox = document.getElementById('main-images');
  mainBox.innerHTML = '';
  t.main_images.forEach((f, i) => {
    const url = `/outputs/${t.task_dir.split('/').slice(-2).join('/')}/${encodeURIComponent(f)}`;
    mainBox.insertAdjacentHTML('beforeend',
      `<figure><img src="${url}" alt="主图${i+1}"><figcaption>主图 ${i+1}<button onclick="location.reload()">重新生成</button></figcaption></figure>`);
  });
  const detailBox = document.getElementById('detail-images');
  detailBox.innerHTML = '';
  t.detail_images.forEach((f, i) => {
    const url = `/outputs/${t.task_dir.split('/').slice(-2).join('/')}/${encodeURIComponent(f)}`;
    detailBox.insertAdjacentHTML('beforeend',
      `<figure><img src="${url}" alt="详情图${i+1}"><figcaption>详情图 ${i+1}<a href="${url}" download>下载</a></figcaption></figure>`);
  });
}

async function loadHistory() {
  try {
    const resp = await fetch('/api/tasks');
    const data = await resp.json();
    const box = document.getElementById('history');
    if (data.tasks && data.tasks.length) {
      box.innerHTML = '<ul>' + data.tasks.map(t =>
        `<li>${t.date} / ${t.task_id}</li>`).join('') + '</ul>';
    }
  } catch (e) { /* 忽略 */ }
}

function setProgress(text) { document.getElementById('progress').style.display = 'block'; document.getElementById('progress').textContent = text; }

document.getElementById('upload-btn').addEventListener('click', upload);
loadHistory();
