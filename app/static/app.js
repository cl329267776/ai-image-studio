const state = { taskId: null, pollTimer: null };

// 提示词 textarea id 与后端字段映射
const PROMPT_FIELDS = [
  ['main-0', 'main', 0], ['main-1', 'main', 1], ['main-2', 'main', 2],
  ['main-3', 'main', 3], ['main-4', 'main', 4],
  ['detail-0', 'detail', 0], ['detail-1', 'detail', 1],
];

function collectPrompts() {
  const prompts = { main: [], detail: [] };
  PROMPT_FIELDS.forEach(([id, group, idx]) => {
    const el = document.getElementById('prompt-' + id);
    prompts[group][idx] = el ? el.value : '';
  });
  return prompts;
}

function fillPrompts(prompts) {
  PROMPT_FIELDS.forEach(([id, group, idx]) => {
    const el = document.getElementById('prompt-' + id);
    if (el && prompts[group] && prompts[group][idx] !== undefined) {
      el.value = prompts[group][idx];
    }
  });
}

async function loadPrompts() {
  try {
    const resp = await fetch('/api/prompts');
    const data = await resp.json();
    fillPrompts(data);
  } catch (e) { /* 忽略,保留默认空值 */ }
}

async function savePrompts() {
  const statusEl = document.getElementById('prompt-save-status');
  statusEl.textContent = '保存中…';
  try {
    const resp = await fetch('/api/prompts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(collectPrompts()),
    });
    const data = await resp.json();
    statusEl.textContent = data.ok ? '✓ 已保存' : ('✗ ' + (data.error || '保存失败'));
  } catch (e) {
    statusEl.textContent = '✗ 保存失败';
  }
  setTimeout(() => { statusEl.textContent = ''; }, 3000);
}

async function upload() {
  const fileInput = document.getElementById('file');
  if (!fileInput.files.length) { alert('请选择商品原图(可多选)'); return; }
  if (fileInput.files.length > 9) { alert('最多上传 9 张原图'); return; }
  const fd = new FormData();
  for (const f of fileInput.files) fd.append('files', f);
  fd.append('prompts', JSON.stringify(collectPrompts()));
  fd.append('provider', document.getElementById('provider').value);
  setProgress('上传中…');
  const resp = await fetch('/api/upload', { method: 'POST', body: fd });
  const data = await resp.json();
  if (data.error) { setProgress('✗ ' + data.error); return; }
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
  const map = { pending: '排队中…', queued: '排队中(前一个任务完成后自动开始)…', generating: 'AI 生成中(约 1-3 分钟)…', done: '完成', partial: '部分完成', failed: '失败' };
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
document.getElementById('save-prompts-btn').addEventListener('click', savePrompts);
loadPrompts();
loadHistory();
