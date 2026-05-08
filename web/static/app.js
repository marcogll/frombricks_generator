/* ─── State ─── */
let state = {
  env: '',
  envObj: null,
  envs: [],
  surveys: [],
  currentSurvey: null,
  editingQuestion: null,
  builder: {
    name: 'My Survey',
    type: 'link',
    status: 'draft',
    welcomeCard: { enabled: true, headline: { default: 'Welcome!' }, subheader: { default: '' }, buttonLabel: { default: 'Start' }, timeToFinish: true, showResponseCount: false },
    endings: [{ type: 'endScreen', headline: { default: 'Thank you!' }, subheader: { default: '' }, buttonLabel: { default: 'Close' } }],
    questions: [],
    hiddenFields: { enabled: false, fieldIds: [] },
    variables: [],
    displayOption: 'displayOnce',
    singleUse: { enabled: false, isEncrypted: true },
    recaptcha: { enabled: false, threshold: 0.1 },
  }
};

/* ─── Init ─── */
document.addEventListener('DOMContentLoaded', async () => {
  initTheme();
  initSidebar();
  await loadEnvs();
  document.getElementById('env-select').addEventListener('change', (e) => {
    const env = state.envs.find(x => x.name === e.target.value);
    state.env = e.target.value;
    state.envObj = env || null;
    state.currentSurvey = null;
    newSurvey();
    loadSurveys();
  });
  document.getElementById('new-survey-btn').addEventListener('click', newSurvey);
  document.getElementById('save-survey-btn').addEventListener('click', saveSurvey);
  document.getElementById('download-json-btn').addEventListener('click', downloadJSON);
  document.getElementById('templates-btn').addEventListener('click', openTemplates);
  document.getElementById('import-btn').addEventListener('click', openImport);
  document.getElementById('modal-close').addEventListener('click', closeTemplates);
  document.getElementById('import-modal-close').addEventListener('click', closeImport);
  document.getElementById('import-fix-btn').addEventListener('click', fixAndLoadJSON);
  document.getElementById('import-file-input').addEventListener('change', handleFileImport);
  document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
  document.getElementById('eval-export-btn').addEventListener('click', evalExport);
  document.getElementById('eval-template-btn').addEventListener('click', evalDownloadTemplate);
  document.getElementById('eval-grade-btn').addEventListener('click', evalGrade);
  document.getElementById('eval-load-key-btn').addEventListener('click', () => document.getElementById('eval-key-input').click());
  document.getElementById('eval-key-input').addEventListener('change', evalLoadKeyFile);
});

/* ─── Env ─── */
async function loadEnvs() {
  const res = await fetch('/api/envs');
  state.envs = await res.json();
  const sel = document.getElementById('env-select');
  const groups = {};
  state.envs.forEach(e => {
    const g = e.group || e.label || e.name;
    if (!groups[g]) groups[g] = [];
    groups[g].push(e);
  });
  sel.innerHTML = Object.entries(groups).map(([g, envs]) =>
    `<optgroup label="${g}">${envs.map(e =>
      `<option value="${e.name}">${e.env_type || 'dev'}</option>`
    ).join('')}</optgroup>`
  ).join('');
  if (state.envs.length) {
    state.env = state.envs[0].name;
    state.envObj = state.envs[0];
    loadSurveys();
  }
}

/* ─── Surveys ─── */
async function loadSurveys() {
  const list = document.getElementById('survey-list');
  list.innerHTML = '<div class="loading">Loading surveys</div>';
  try {
    const res = await fetch(`/api/surveys?env=${state.env}`);
    state.surveys = await res.json();
    renderSurveyList();
  } catch(e) {
    list.innerHTML = `<div class="loading" style="color:var(--red)">Error: ${e.message}</div>`;
  }
}

function renderSurveyList() {
  const list = document.getElementById('survey-list');
  if (!state.surveys.length) { list.innerHTML = '<div style="color:var(--text2);font-size:13px">No surveys found</div>'; return; }
  list.innerHTML = state.surveys.map(s => `
    <div class="survey-item ${state.currentSurvey && state.currentSurvey.id === s.id ? 'active' : ''}" onclick="loadSurvey('${s.id}')">
      <div>
        <div class="name">${esc(s.name)}</div>
        <div class="meta">${s.questions ? s.questions.length : 0} questions · ${esc(s.status)}</div>
      </div>
      <span class="status-badge status-${s.status}">${s.status}</span>
    </div>
  `).join('');
}

async function loadSurvey(id) {
  const res = await fetch(`/api/surveys/${id}?env=${state.env}`);
  const survey = await res.json();
  state.currentSurvey = survey;
  state.editingQuestion = null;

  state.builder = {
    name: survey.name || '',
    type: survey.type || 'link',
    status: survey.status || 'draft',
    welcomeCard: survey.welcomeCard || state.builder.welcomeCard,
    endings: survey.endings || [],
    questions: survey.questions || [],
    hiddenFields: survey.hiddenFields || { enabled: false, fieldIds: [] },
    variables: survey.variables || [],
    displayOption: survey.displayOption || 'displayOnce',
    singleUse: survey.singleUse || { enabled: false, isEncrypted: true },
    recaptcha: survey.recaptcha || { enabled: false, threshold: 0.1 },
  };

  renderSurveyList();
  renderBuilder();
  showSurveyLinks(survey.id);
}

function newSurvey() {
  state.currentSurvey = null;
  state.editingQuestion = null;
  state.builder = {
    name: 'My Survey',
    type: 'link',
    status: 'draft',
    welcomeCard: { enabled: true, headline: { default: 'Welcome!' }, subheader: { default: '' }, buttonLabel: { default: 'Start' }, timeToFinish: true, showResponseCount: false },
    endings: [{ type: 'endScreen', headline: { default: 'Thank you!' }, subheader: { default: '' }, buttonLabel: { default: 'Close' } }],
    questions: [],
    hiddenFields: { enabled: false, fieldIds: [] },
    variables: [],
    displayOption: 'displayOnce',
    singleUse: { enabled: false, isEncrypted: true },
    recaptcha: { enabled: false, threshold: 0.1 },
  };
  renderBuilder();
  document.querySelectorAll('.survey-item').forEach(el => el.classList.remove('active'));
}

/* ─── Builder ─── */
function renderBuilder() {
  const b = state.builder;
  document.getElementById('survey-name').value = b.name;
  document.getElementById('survey-type').value = b.type;
  document.getElementById('survey-status').value = b.status;
  document.getElementById('display-option').value = b.displayOption;
  renderWelcomeCard();
  renderEndings();
  renderQuestions();
  renderAdvanced();
  renderJSON();
}

/* ─── Welcome Card ─── */
function renderWelcomeCard() {
  const wc = state.builder.welcomeCard || {};
  const el = document.getElementById('welcome-section');
  el.innerHTML = `
    <div class="form-row-inline">
      <input type="checkbox" id="wc-enabled" ${wc.enabled ? 'checked' : ''} onchange="updateWelcome()">
      <label for="wc-enabled">Enable Welcome Card</label>
    </div>
    <div id="wc-fields" style="margin-top:10px;${wc.enabled ? '' : 'display:none'}">
      <div class="form-row"><label>Headline</label><input id="wc-headline" value="${esc((wc.headline||{}).default||'')}" oninput="updateWelcome()"></div>
      <div class="form-row"><label>Subheader (HTML)</label><textarea id="wc-subheader" oninput="updateWelcome()">${esc((wc.subheader||{}).default||'')}</textarea></div>
      <div class="form-row"><label>Button Label</label><input id="wc-button" value="${esc((wc.buttonLabel||{}).default||'Start')}" oninput="updateWelcome()"></div>
      <div class="form-row-inline">
        <input type="checkbox" id="wc-time" ${wc.timeToFinish ? 'checked' : ''} onchange="updateWelcome()"> <label for="wc-time">Show time to finish</label>
        <input type="checkbox" id="wc-count" ${wc.showResponseCount ? 'checked' : ''} onchange="updateWelcome()"> <label for="wc-count">Show response count</label>
      </div>
    </div>
  `;
}

function updateWelcome() {
  const enabled = document.getElementById('wc-enabled').checked;
  state.builder.welcomeCard = {
    enabled,
    headline: { default: document.getElementById('wc-headline')?.value || '' },
    subheader: { default: document.getElementById('wc-subheader')?.value || '' },
    buttonLabel: { default: document.getElementById('wc-button')?.value || 'Start' },
    timeToFinish: document.getElementById('wc-time')?.checked || false,
    showResponseCount: document.getElementById('wc-count')?.checked || false,
  };
  renderJSON();
}

/* ─── Endings ─── */
function renderEndings() {
  const endings = state.builder.endings || [];
  const el = document.getElementById('endings-section');
  if (!endings.length) {
    el.innerHTML = '<div style="color:var(--text2);font-size:13px">No endings configured. <a href="#" onclick="addEnding();return false" style="color:var(--accent)">Add ending screen</a></div>';
    return;
  }
  el.innerHTML = endings.map((e, i) => `
    <div class="question-card">
      <div class="q-header">
        <div><span class="q-title">Ending Screen ${i+1}</span><span class="q-type"> ${e.type||'endScreen'}</span></div>
        <div class="q-actions"><button onclick="removeEnding(${i})" title="Remove">✕</button></div>
      </div>
      <div class="form-row"><label>Headline</label><input value="${esc((e.headline||{}).default||'')}" oninput="updateEnding(${i},'headline',this.value)"></div>
      <div class="form-row"><label>Subheader</label><textarea oninput="updateEnding(${i},'subheader',this.value)">${esc((e.subheader||{}).default||'')}</textarea></div>
      <div class="form-row"><label>Button Label</label><input value="${esc((e.buttonLabel||{}).default||'Close')}" oninput="updateEnding(${i},'buttonLabel',this.value)"></div>
      <div class="form-row"><label>Button Link (optional)</label><input value="${esc(e.buttonLink||'')}" oninput="updateEndingLink(${i},this.value)"></div>
    </div>
  `).join('') + `<button class="btn btn-secondary btn-sm" onclick="addEnding()">+ Add Another Ending</button>`;
}

function addEnding() {
  state.builder.endings.push({ type: 'endScreen', headline: { default: '' }, subheader: { default: '' }, buttonLabel: { default: 'Close' } });
  renderEndings(); renderJSON();
}

function removeEnding(i) {
  state.builder.endings.splice(i, 1);
  renderEndings(); renderJSON();
}

function updateEnding(i, field, val) {
  const e = state.builder.endings[i];
  if (!e[field]) e[field] = { default: '' };
  e[field].default = val;
  renderJSON();
}

function updateEndingLink(i, val) {
  state.builder.endings[i].buttonLink = val || undefined;
  renderJSON();
}

/* ─── Questions ─── */
function renderQuestions() {
  const qs = state.builder.questions;
  const el = document.getElementById('questions-section');
  if (!qs.length) {
    el.innerHTML = '<div style="color:var(--text2);font-size:13px">No questions yet.</div>';
    return;
  }
  el.innerHTML = qs.map((q, i) => {
    const hl = (q.headline||{}).default || q.id || 'Untitled';
    return `
      <div class="question-card">
        <div class="q-header">
          <div>
            <span class="q-title">${esc(hl)}</span>
            <span class="q-type">${q.type}</span>
          </div>
          <div class="q-actions">
            <button onclick="editQuestion(${i})" title="Edit">✎</button>
            <button onclick="duplicateQuestion(${i})" title="Duplicate">⧉</button>
            <button onclick="moveQuestion(${i},-1)" title="Move up">↑</button>
            <button onclick="moveQuestion(${i},1)" title="Move down">↓</button>
            <button class="del-btn" onclick="removeQuestion(${i})" title="Delete">✕</button>
          </div>
        </div>
        <div style="font-size:11px;color:var(--text2)">
          ${q.type === 'multipleChoiceSingle' || q.type === 'multipleChoiceMulti' ? (q.choices||[]).length + ' choices · ' : ''}
          ${q.required ? 'required' : 'optional'}
        </div>
      </div>
    `;
  }).join('');
}

function addQuestion(type) {
  if (type) {
    fetch(`/api/templates?type=${type}`).then(r => r.json()).then(tpl => {
      state.builder.questions.push(JSON.parse(JSON.stringify(tpl)));
      renderQuestions(); renderJSON();
    });
  } else {
    // Quick add openText
    const id = 'q' + (state.builder.questions.length + 1);
    state.builder.questions.push({
      id, type: 'openText', headline: { default: '' }, required: true,
      inputType: 'text', buttonLabel: { default: 'Next' }
    });
    renderQuestions(); renderJSON();
  }
}

function removeQuestion(i) {
  state.builder.questions.splice(i, 1);
  if (state.editingQuestion === i) state.editingQuestion = null;
  else if (state.editingQuestion > i) state.editingQuestion--;
  renderQuestions(); renderJSON();
  renderQuestionEditor();
}

function duplicateQuestion(i) {
  const q = JSON.parse(JSON.stringify(state.builder.questions[i]));
  q.id = q.id + '_copy';
  state.builder.questions.splice(i + 1, 0, q);
  renderQuestions(); renderJSON();
}

function moveQuestion(i, dir) {
  const j = i + dir;
  if (j < 0 || j >= state.builder.questions.length) return;
  [state.builder.questions[i], state.builder.questions[j]] = [state.builder.questions[j], state.builder.questions[i]];
  if (state.editingQuestion === i) state.editingQuestion = j;
  else if (state.editingQuestion === j) state.editingQuestion = i;
  renderQuestions(); renderJSON(); renderQuestionEditor();
}

function editQuestion(i) {
  state.editingQuestion = i;
  renderQuestionEditor();
}

function renderQuestionEditor() {
  const el = document.getElementById('question-editor');
  const i = state.editingQuestion;
  if (i === null || i === undefined || !state.builder.questions[i]) {
    el.innerHTML = '<div style="color:var(--text2);font-size:13px;padding:12px 0">Select a question to edit its details.</div>';
    return;
  }
  const q = state.builder.questions[i];
  el.innerHTML = buildQuestionForm(i, q);
  el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function buildQuestionForm(i, q) {
  const hl = (q.headline||{}).default || '';
  const sub = (q.subheader||{}).default || '';
  const ph = (q.placeholder||{}).default || '';
  const btn = (q.buttonLabel||{}).default || 'Next';
  const back = (q.backButtonLabel||{}).default || '';
  let extra = '';
  let choicesHTML = '';

  if (q.type === 'openText') {
    extra = `
      <div class="form-row"><label>Input Type</label><select onchange="updateQuestionField(${i},'inputType',this.value)">
        ${['text','number','phone','email'].map(t => `<option value="${t}" ${q.inputType===t?'selected':''}>${t}</option>`).join('')}
      </select></div>
      <div class="form-row-inline">
        <input type="checkbox" id="q-long-${i}" ${q.longAnswer?'checked':''} onchange="updateQuestionField(${i},'longAnswer',this.checked)"> <label for="q-long-${i}">Long answer</label>
      </div>
      <div class="form-row"><label>Placeholder</label><input value="${esc(ph)}" oninput="updateQuestionI18n(${i},'placeholder',this.value)"></div>
    `;
  } else if (q.type === 'multipleChoiceSingle' || q.type === 'multipleChoiceMulti') {
    const ch = q.choices || [];
    choicesHTML = `
      <div class="choices-container">
        <label>Choices</label>
        <div class="choices-list">
          ${ch.map((c, ci) => `
            <div class="choice-row">
              <input value="${esc((c.label||{}).default||'')}" oninput="updateChoice(${i},${ci},this.value)" placeholder="Option ${ci+1}">
              <button onclick="removeChoice(${i},${ci})">✕</button>
            </div>
          `).join('')}
        </div>
        <button class="btn btn-secondary btn-sm" onclick="addChoice(${i})" style="margin-top:4px">+ Add Choice</button>
      </div>
      <div class="form-row" style="margin-top:8px"><label>Shuffle</label>
        <select onchange="updateQuestionField(${i},'shuffleOption',this.value)">
          <option value="none" ${q.shuffleOption==='none'?'selected':''}>None</option>
          <option value="all" ${q.shuffleOption==='all'?'selected':''}>All</option>
          <option value="exceptLast" ${q.shuffleOption==='exceptLast'?'selected':''}>Except last</option>
        </select>
      </div>
    `;
  } else if (q.type === 'nps') {
    extra = `
      <div class="form-row"><label>Lower label</label><input value="${esc((q.lowerLabel||{}).default||'')}" oninput="updateQuestionI18n(${i},'lowerLabel',this.value)"></div>
      <div class="form-row"><label>Upper label</label><input value="${esc((q.upperLabel||{}).default||'')}" oninput="updateQuestionI18n(${i},'upperLabel',this.value)"></div>
    `;
  } else if (q.type === 'rating') {
    extra = `
      <div class="form-row"><label>Max rating</label><input type="number" value="${q.rate||5}" oninput="updateQuestionField(${i},'rate',parseInt(this.value)||5)" min="2" max="10"></div>
      <div class="form-row"><label>Lower label</label><input value="${esc((q.lowerLabel||{}).default||'')}" oninput="updateQuestionI18n(${i},'lowerLabel',this.value)"></div>
      <div class="form-row"><label>Upper label</label><input value="${esc((q.upperLabel||{}).default||'')}" oninput="updateQuestionI18n(${i},'upperLabel',this.value)"></div>
    `;
  } else if (q.type === 'date') {
    extra = `
      <div class="form-row"><label>Format</label>
        <select onchange="updateQuestionField(${i},'format',this.value)">
          <option value="d-M-y" ${q.format==='d-M-y'?'selected':''}>d-M-y</option>
          <option value="M-d-y" ${q.format==='M-d-y'?'selected':''}>M-d-y</option>
          <option value="y-M-d" ${q.format==='y-M-d'?'selected':''}>y-M-d</option>
        </select>
      </div>
    `;
  } else if (q.type === 'consent') {
    extra = `<div class="form-row"><label>Checkbox label</label><input value="${esc((q.label||{}).default||'')}" oninput="updateQuestionI18n(${i},'label',this.value)"></div>`;
  } else if (q.type === 'fileUpload') {
    extra = `
      <div class="form-row-inline">
        <input type="checkbox" id="q-multi-${i}" ${q.allowMultipleFiles?'checked':''} onchange="updateQuestionField(${i},'allowMultipleFiles',this.checked)"> <label for="q-multi-${i}">Allow multiple files</label>
      </div>
      <div class="form-row"><label>Max size (MB)</label><input type="number" value="${q.maxSizeInMB||10}" oninput="updateQuestionField(${i},'maxSizeInMB',parseInt(this.value)||10)"></div>
      <div class="form-row"><label>Allowed extensions (comma sep)</label><input value="${esc(((q.validation||{}).rules||[{}])[0]?.params?.extensions||[]).join(',')}" oninput="updateFileExts(${i},this.value)"></div>
    `;
  } else if (q.type === 'matrix') {
    const cols = q.columns || [];
    const rows = q.rows || [];
    choicesHTML = `
      <div class="choices-container">
        <label>Columns</label>
        <div class="choices-list">
          ${cols.map((c, ci) => `
            <div class="choice-row">
              <input value="${esc((c.label||{}).default||'')}" oninput="updateMatrixItem(${i},'columns',${ci},this.value)" placeholder="Column ${ci+1}">
              <button onclick="removeMatrixItem(${i},'columns',${ci})">✕</button>
            </div>
          `).join('')}
        </div>
        <button class="btn btn-secondary btn-sm" onclick="addMatrixItem(${i},'columns')" style="margin-top:4px">+ Column</button>
      </div>
      <div class="choices-container" style="margin-top:8px">
        <label>Rows</label>
        <div class="choices-list">
          ${rows.map((r, ri) => `
            <div class="choice-row">
              <input value="${esc((r.label||{}).default||'')}" oninput="updateMatrixItem(${i},'rows',${ri},this.value)" placeholder="Row ${ri+1}">
              <button onclick="removeMatrixItem(${i},'rows',${ri})">✕</button>
            </div>
          `).join('')}
        </div>
        <button class="btn btn-secondary btn-sm" onclick="addMatrixItem(${i},'rows')" style="margin-top:4px">+ Row</button>
      </div>
    `;
  }

  return `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <strong style="font-size:14px">Edit Question ${i+1}</strong>
      <span style="font-size:11px;color:var(--accent);font-weight:500">${q.type}</span>
    </div>
    <div class="form-row"><label>Question ID</label><input value="${esc(q.id)}" oninput="updateQuestionField(${i},'id',this.value)"></div>
    <div class="form-row"><label>Headline</label><input value="${esc(hl)}" oninput="updateQuestionI18n(${i},'headline',this.value)"></div>
    <div class="form-row"><label>Subheader (HTML)</label><textarea oninput="updateQuestionI18n(${i},'subheader',this.value)">${esc(sub)}</textarea></div>
    <div class="form-row-inline">
      <input type="checkbox" id="q-req-${i}" ${q.required?'checked':''} onchange="updateQuestionField(${i},'required',this.checked)"> <label for="q-req-${i}">Required</label>
    </div>
    ${extra}
    ${choicesHTML}
    <div class="form-row"><label>Next button label</label><input value="${esc(btn)}" oninput="updateQuestionI18n(${i},'buttonLabel',this.value)"></div>
    <div class="form-row-inline">
      <input type="checkbox" id="q-back-${i}" ${q.backButtonLabel?'checked':''} onchange="toggleBackBtn(${i},this.checked)"> <label for="q-back-${i}">Show back button</label>
    </div>
    <div id="q-back-field-${i}" style="${q.backButtonLabel?'':'display:none'};margin-top:-4px">
      <div class="form-row"><label>Back button label</label><input value="${esc(back)}" oninput="updateQuestionI18n(${i},'backButtonLabel',this.value)"></div>
    </div>
    <div class="btn-group" style="margin-top:8px">
      <button class="btn btn-secondary btn-sm" onclick="deleteQuestionFromEditor(${i})">🗑 Delete</button>
    </div>
  `;
}

/* ─── Question helpers ─── */
function updateQuestionField(i, field, val) {
  state.builder.questions[i][field] = val;
  renderQuestions(); renderJSON();
}

function updateQuestionI18n(i, field, val) {
  if (!state.builder.questions[i][field]) state.builder.questions[i][field] = {};
  state.builder.questions[i][field].default = val;
  renderQuestions(); renderJSON();
}

function toggleBackBtn(i, show) {
  if (show) {
    state.builder.questions[i].backButtonLabel = { default: 'Back' };
  } else {
    delete state.builder.questions[i].backButtonLabel;
  }
  renderQuestionEditor(); renderQuestions(); renderJSON();
}

function addChoice(i) {
  const q = state.builder.questions[i];
  if (!q.choices) q.choices = [];
  q.choices.push({ id: 'c' + (q.choices.length + 1), label: { default: '' } });
  renderQuestionEditor(); renderJSON();
}

function removeChoice(i, ci) {
  state.builder.questions[i].choices.splice(ci, 1);
  renderQuestionEditor(); renderJSON();
}

function updateChoice(i, ci, val) {
  const c = state.builder.questions[i].choices[ci];
  if (!c.label) c.label = {};
  c.label.default = val;
  renderJSON();
}

function updateFileExts(i, val) {
  const q = state.builder.questions[i];
  const exts = val.split(',').map(s => s.trim()).filter(Boolean);
  q.validation = { logic: 'and', rules: [{ type: 'fileExtensionIs', params: { extensions: exts } }] };
  renderJSON();
}

function addMatrixItem(i, type) {
  const q = state.builder.questions[i];
  if (!q[type]) q[type] = [];
  const prefix = type === 'columns' ? 'col' : 'row';
  q[type].push({ id: prefix + (q[type].length + 1), label: { default: '' } });
  renderQuestionEditor(); renderJSON();
}

function removeMatrixItem(i, type, idx) {
  state.builder.questions[i][type].splice(idx, 1);
  renderQuestionEditor(); renderJSON();
}

function updateMatrixItem(i, type, idx, val) {
  const item = state.builder.questions[i][type][idx];
  if (!item.label) item.label = {};
  item.label.default = val;
  renderJSON();
}

function deleteQuestionFromEditor(i) {
  state.builder.questions.splice(i, 1);
  state.editingQuestion = null;
  renderQuestions(); renderJSON(); renderQuestionEditor();
}

/* ─── Advanced ─── */
function renderAdvanced() {
  const b = state.builder;
  const el = document.getElementById('advanced-section');
  el.innerHTML = `
    <div class="form-row-inline">
      <input type="checkbox" id="hf-enabled" ${(b.hiddenFields||{}).enabled?'checked':''} onchange="updateAdvanced()"> <label for="hf-enabled">Enable Hidden Fields</label>
    </div>
    <div class="form-row-inline" style="margin-top:8px">
      <input type="checkbox" id="su-enabled" ${(b.singleUse||{}).enabled?'checked':''} onchange="updateAdvanced()"> <label for="su-enabled">Single-use links</label>
    </div>
    <div class="form-row-inline" style="margin-top:8px">
      <input type="checkbox" id="rc-enabled" ${(b.recaptcha||{}).enabled?'checked':''} onchange="updateAdvanced()"> <label for="rc-enabled">reCAPTCHA protection</label>
    </div>
  `;
}

function updateAdvanced() {
  state.builder.hiddenFields = { enabled: document.getElementById('hf-enabled').checked, fieldIds: [] };
  state.builder.singleUse = { enabled: document.getElementById('su-enabled').checked, isEncrypted: true };
  state.builder.recaptcha = { enabled: document.getElementById('rc-enabled').checked, threshold: 0.1 };
  renderJSON();
}

/* ─── JSON ─── */
function buildSurveyJSON() {
  const b = state.builder;
  const json = {
    name: b.name,
    type: b.type,
    status: b.status,
    welcomeCard: b.welcomeCard,
    endings: b.endings,
    questions: b.questions,
    hiddenFields: b.hiddenFields,
    displayOption: b.displayOption,
  };
  if (b.singleUse?.enabled) json.singleUse = b.singleUse;
  if (b.recaptcha?.enabled) json.recaptcha = b.recaptcha;
  if (b.variables?.length) json.variables = b.variables;
  // Clean up empty endings, empty questions
  if (!json.endings?.length) delete json.endings;
  if (!json.questions?.length) json.questions = [];
  json.thankYouCard = { enabled: false };
  return json;
}

function renderJSON() {
  const json = buildSurveyJSON();
  const el = document.getElementById('json-preview');
  el.textContent = JSON.stringify(json, null, 2);
}

/* ─── Save ─── */
async function saveSurvey() {
  const json = buildSurveyJSON();
  const isNew = !state.currentSurvey;

  if (isNew && !confirm('¿Estás seguro de enviar esta encuesta a Formbricks?')) return;

  try {
    let res;
    if (state.currentSurvey) {
      res = await fetch(`/api/surveys/${state.currentSurvey.id}?env=${state.env}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(json)
      });
    } else {
      res = await fetch(`/api/surveys?env=${state.env}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(json)
      });
    }
    const data = await res.json();
    if (!res.ok) { toast(data.error || 'Save failed', 'error'); return; }
    toast('Survey saved!', 'success');
    state.currentSurvey = data;
    await loadSurveys();
    showSurveyLinks(data.id);
  } catch(e) { toast(e.message, 'error'); }
}

function showSurveyLinks(surveyId) {
  const el = document.getElementById('survey-links');
  const env = state.envObj;
  if (!env || !surveyId) { el.style.display = 'none'; return; }
  const base = env.base_url.replace(/\/+$/, '');
  const respUrl = `${base}/s/${surveyId}`;
  const editUrl = `${base}/environments/${env.environment_id}/surveys/${surveyId}/edit`;
  document.getElementById('link-response').href = respUrl;
  document.getElementById('link-response').textContent = respUrl;
  document.getElementById('link-edit').href = editUrl;
  document.getElementById('link-edit').textContent = editUrl;
  el.style.display = 'block';
}

/* ─── Download ─── */
function downloadJSON() {
  const json = buildSurveyJSON();
  const blob = new Blob([JSON.stringify(json, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = (json.name || 'survey').replace(/[^a-zA-Z0-9]/g, '_') + '.json';
  a.click();
  URL.revokeObjectURL(a.href);
  toast('JSON downloaded', 'success');
}

/* ─── Templates Modal ─── */
function openTemplates() {
  const grid = document.getElementById('template-grid');
  const types = [
    { type: 'openText', icon: '✏️', name: 'Open Text', desc: 'Free text input' },
    { type: 'multipleChoiceSingle', icon: '🔘', name: 'Single Choice', desc: 'Radio buttons' },
    { type: 'multipleChoiceMulti', icon: '☑️', name: 'Multi Choice', desc: 'Checkboxes' },
    { type: 'nps', icon: '📊', name: 'NPS', desc: '0-10 scale' },
    { type: 'rating', icon: '⭐', name: 'Rating', desc: 'Star rating' },
    { type: 'date', icon: '📅', name: 'Date', desc: 'Date picker' },
    { type: 'consent', icon: '✓', name: 'Consent', desc: 'Checkbox agree' },
    { type: 'fileUpload', icon: '📎', name: 'File Upload', desc: 'File picker' },
    { type: 'matrix', icon: '📋', name: 'Matrix', desc: 'Grid rating' },
  ];
  grid.innerHTML = types.map(t => `
    <div class="template-card" onclick="addQuestionTemplate('${t.type}')" title="Click to add to survey">
      <div class="icon">${t.icon}</div>
      <div class="name">${t.name}</div>
      <div class="desc">${t.desc}</div>
    </div>
  `).join('');
  document.getElementById('templates-modal').classList.add('open');
}

function closeTemplates() {
  document.getElementById('templates-modal').classList.remove('open');
}

function addQuestionTemplate(type) {
  addQuestion(type);
  closeTemplates();
  toast(`Added ${type} question`, 'success');
}

async function downloadTemplate(type) {
  const res = await fetch(`/api/templates?type=${type}`);
  const data = await res.json();
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `template_${type}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
  toast(`Template ${type} downloaded`, 'success');
}

function openSurveyDocs() {
  closeTemplates();
  window.open('/api/templates/docs/survey-structure?format=md', '_blank');
  toast('Survey structure docs opened in new tab', 'success');
}

function downloadSurveyDocs() {
  fetch('/api/templates/docs/survey-structure?format=md')
    .then(r => r.text())
    .then(md => {
      const blob = new Blob([md], { type: 'text/markdown' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'formbricks-survey-structure.md';
      a.click();
      URL.revokeObjectURL(a.href);
      toast('Survey structure docs downloaded', 'success');
    });
}

/* ─── Utils ─── */
function esc(s) { if (s === null || s === undefined) return ''; return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function toast(msg, type) {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();
  const el = document.createElement('div');
  el.className = `toast ${type || ''}`;
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

function toggleSection(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = el.style.display === 'none' ? 'block' : 'none';
}

/* ─── Theme ─── */
function initTheme() {
  const saved = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = saved || (prefersDark ? 'dark' : 'light');
  applyTheme(theme);
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  document.getElementById('theme-toggle').textContent = theme === 'dark' ? '🌙' : '☀️';
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  localStorage.setItem('theme', next);
}

/* ─── Sidebar Collapse ─── */
function initSidebar() {
  const saved = localStorage.getItem('sidebarCollapsed');
  if (saved === 'true') {
    document.getElementById('sidebar').classList.add('collapsed');
    document.getElementById('app-layout').classList.add('sidebar-collapsed');
  }
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const layout = document.getElementById('app-layout');
  sidebar.classList.toggle('collapsed');
  layout.classList.toggle('sidebar-collapsed');
  localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
}

/* ─── Import JSON ─── */
function openImport() {
  document.getElementById('import-textarea').value = '';
  document.getElementById('import-status').textContent = '';
  document.getElementById('import-modal').classList.add('open');
}

function closeImport() {
  document.getElementById('import-modal').classList.remove('open');
}

function handleFileImport(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => {
    document.getElementById('import-textarea').value = ev.target.result;
    document.getElementById('import-status').innerHTML = '<span style="color:var(--green)">✓ File loaded. Click <strong>Fix & Load</strong> to process.</span>';
  };
  reader.onerror = () => {
    document.getElementById('import-status').innerHTML = '<span style="color:var(--red)">Error reading file</span>';
  };
  reader.readAsText(file);
  e.target.value = '';
}

function fixSurveyJSON(raw) {
  let data;
  try {
    data = typeof raw === 'string' ? JSON.parse(raw) : JSON.parse(JSON.stringify(raw));
  } catch(e) {
    document.getElementById('import-status').innerHTML = '<span style="color:var(--red)">Invalid JSON: ' + esc(e.message) + '</span>';
    return null;
  }
  let fixed = false;
  const msgs = [];

  if (!data.name) { data.name = 'Imported Survey'; msgs.push('name'); fixed = true; }
  if (!data.type) { data.type = 'link'; msgs.push('type → link'); fixed = true; }
  if (!data.status) { data.status = 'draft'; msgs.push('status → draft'); fixed = true; }
  if (!data.displayOption) { data.displayOption = 'displayOnce'; msgs.push('displayOption'); fixed = true; }
  if (!data.thankYouCard) { data.thankYouCard = { enabled: false }; msgs.push('thankYouCard'); fixed = true; }
  if (!data.welcomeCard) { data.welcomeCard = { enabled: false }; msgs.push('welcomeCard'); fixed = true; }

  if (!data.questions || !Array.isArray(data.questions)) {
    data.questions = [];
    msgs.push('questions array');
    fixed = true;
  }

  // Convert blocks.elements format to questions
  if (!data.questions.length && data.blocks && Array.isArray(data.blocks)) {
    const extracted = [];
    data.blocks.forEach(b => {
      if (b.elements && Array.isArray(b.elements)) extracted.push(...b.elements);
    });
    if (extracted.length) {
      data.questions = extracted;
      delete data.blocks;
      msgs.push('converted blocks→questions');
      fixed = true;
    }
  }

  // Fix each question
  data.questions.forEach((q, i) => {
    if (!q.id) { q.id = 'q' + (i + 1); msgs.push('q' + (i + 1) + ' id'); fixed = true; }
    if (!q.type) { q.type = 'openText'; msgs.push(q.id + ' type → openText'); fixed = true; }
    if (!q.headline) {
      q.headline = { default: 'Question ' + (i + 1) };
      msgs.push(q.id + ' headline');
      fixed = true;
    } else if (typeof q.headline === 'string') {
      q.headline = { default: q.headline };
      msgs.push(q.id + ' headline (converted)');
      fixed = true;
    }
    if (!q.buttonLabel) { q.buttonLabel = { default: 'Next' }; msgs.push(q.id + ' buttonLabel'); fixed = true; }

    if (q.type === 'multipleChoiceSingle' || q.type === 'multipleChoiceMulti') {
      if (!q.choices || !Array.isArray(q.choices)) {
        q.choices = [];
        msgs.push(q.id + ' choices');
        fixed = true;
      }
      q.choices.forEach((c, ci) => {
        if (!c.id) { c.id = 'c' + (ci + 1); msgs.push(q.id + ' choice ' + (ci + 1) + ' id'); fixed = true; }
        if (!c.label) {
          c.label = { default: 'Option ' + (ci + 1) };
          msgs.push(q.id + ' choice ' + (ci + 1) + ' label');
          fixed = true;
        } else if (typeof c.label === 'string') {
          c.label = { default: c.label };
          msgs.push(q.id + ' choice ' + (ci + 1) + ' label (converted)');
          fixed = true;
        }
      });
    }
  });

  // Ensure endings array
  if (!data.endings || !Array.isArray(data.endings)) {
    data.endings = [{ type: 'endScreen', headline: { default: 'Thank you!' }, subheader: { default: '' }, buttonLabel: { default: 'Close' } }];
    msgs.push('endings');
    fixed = true;
  }

  // Ensure hiddenFields
  if (!data.hiddenFields) {
    data.hiddenFields = { enabled: false, fieldIds: [] };
    msgs.push('hiddenFields');
    fixed = true;
  }

  const statusEl = document.getElementById('import-status');
  if (fixed) {
    statusEl.innerHTML = '<span style="color:var(--green)">✓ Fixed: ' + msgs.join(', ') + '.<br>Ready to load into builder.</span>';
  } else {
    statusEl.innerHTML = '<span style="color:var(--green)">✓ JSON looks clean — no fixes needed.</span>';
  }
  return data;
}

function fixAndLoadJSON() {
  const raw = document.getElementById('import-textarea').value.trim();
  if (!raw) {
    document.getElementById('import-status').innerHTML = '<span style="color:var(--orange)">Paste some JSON first or upload a file.</span>';
    return;
  }
  const data = fixSurveyJSON(raw);
  if (!data) return;
  loadIntoBuilder(data);
  closeImport();
  toast('Survey imported from JSON', 'success');
}

function loadIntoBuilder(data) {
  state.currentSurvey = null;
  state.editingQuestion = null;
  state.builder = {
    name: data.name || 'Imported Survey',
    type: data.type || 'link',
    status: data.status || 'draft',
    welcomeCard: data.welcomeCard || { enabled: true, headline: { default: 'Welcome!' }, subheader: { default: '' }, buttonLabel: { default: 'Start' }, timeToFinish: true, showResponseCount: false },
    endings: Array.isArray(data.endings) && data.endings.length ? data.endings : [{ type: 'endScreen', headline: { default: 'Thank you!' }, subheader: { default: '' }, buttonLabel: { default: 'Close' } }],
    questions: Array.isArray(data.questions) ? data.questions : [],
    hiddenFields: data.hiddenFields || { enabled: false, fieldIds: [] },
    variables: Array.isArray(data.variables) ? data.variables : [],
    displayOption: data.displayOption || 'displayOnce',
    singleUse: data.singleUse || { enabled: false, isEncrypted: true },
    recaptcha: data.recaptcha || { enabled: false, threshold: 0.1 },
  };
  renderBuilder();
}

/* ─── Evaluation ─── */
function showEvalSection() {
  const el = document.getElementById('eval-section');
  if (state.currentSurvey && state.currentSurvey.id) {
    el.style.display = 'block';
  } else {
    el.style.display = 'none';
  }
}

async function evalExport() {
  if (!state.currentSurvey) { toast('Select a survey first', 'error'); return; }
  const a = document.createElement('a');
  a.href = `/api/eval/export/${state.currentSurvey.id}?env=${state.env}`;
  a.download = `responses_${state.currentSurvey.id}.csv`;
  a.click();
  toast('Downloading responses CSV', 'success');
}

async function evalDownloadTemplate() {
  if (!state.currentSurvey) { toast('Select a survey first', 'error'); return; }
  const res = await fetch(`/api/eval/template/${state.currentSurvey.id}?env=${state.env}`);
  const data = await res.json();
  if (!res.ok) { toast(data.error || 'Error', 'error'); return; }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `answer_key_${state.currentSurvey.id}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
  toast('Answer key template downloaded', 'success');
  document.getElementById('eval-answer-key').value = JSON.stringify(data, null, 2);
}

function evalLoadKeyFile(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (ev) => {
    document.getElementById('eval-answer-key').value = ev.target.result;
    toast('Answer key loaded', 'success');
  };
  reader.readAsText(file);
  e.target.value = '';
}

async function evalGrade() {
  if (!state.currentSurvey) { toast('Select a survey first', 'error'); return; }
  const raw = document.getElementById('eval-answer-key').value.trim();
  if (!raw) { toast('Paste an answer key first', 'error'); return; }
  let answerKey;
  try { answerKey = JSON.parse(raw); } catch(e) { toast('Invalid JSON in answer key', 'error'); return; }

  const res = await fetch(`/api/eval/grade/${state.currentSurvey.id}?env=${state.env}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answer_key: answerKey }),
  });
  const results = await res.json();
  if (!res.ok) { toast(results.error || 'Grade failed', 'error'); return; }

  renderEvalResults(results);
  toast(`Graded ${results.length} responses`, 'success');
}

function renderEvalResults(results) {
  const el = document.getElementById('eval-results');
  if (!results.length) {
    el.innerHTML = '<div style="color:var(--text2);font-size:13px">No responses to grade.</div>';
    el.style.display = 'block';
    return;
  }

  const total = results.length;
  const avgPct = results.reduce((s, r) => s + (r.percentage || 0), 0) / total;
  const qids = results[0].questions ? Object.keys(results[0].questions) : [];

  let html = `
    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:12px">
      <div class="stat-box"><strong>${total}</strong><br><span>Responses</span></div>
      <div class="stat-box"><strong>${avgPct.toFixed(1)}%</strong><br><span>Avg Score</span></div>
    </div>
    <div style="max-height:400px;overflow:auto">
    <table style="width:100%;font-size:11px;border-collapse:collapse">
      <thead>
        <tr style="background:var(--surface2);position:sticky;top:0">
          <th style="padding:6px 8px;text-align:left">Response</th>
          <th style="padding:6px 8px;text-align:left">Person</th>
          <th style="padding:6px 8px;text-align:center">Score</th>
          ${qids.map(q => `<th style="padding:6px 8px;text-align:left">${esc(q)}</th>`).join('')}
        </tr>
      </thead>
      <tbody>
  `;

  results.forEach(r => {
    const status = r.percentage >= 80 ? '🟢' : r.percentage >= 50 ? '🟡' : '🔴';
    html += `<tr style="border-bottom:1px solid var(--border)">`;
    html += `<td style="padding:6px 8px">${esc(r.response_id.slice(0, 12))}…</td>`;
    html += `<td style="padding:6px 8px">${esc(r.person_id.slice(0, 12)) || '—'}</td>`;
    html += `<td style="padding:6px 8px;text-align:center">${status} ${r.score}/${r.max_score} (${r.percentage}%)</td>`;
    qids.forEach(qid => {
      const q = r.questions[qid] || {};
      const st = q.status === 'correct' ? '🟢' : q.status === 'incorrect' ? '🔴' : '⚪';
      html += `<td style="padding:6px 8px;max-width:200px;overflow:hidden;text-overflow:ellipsis" title="${esc(q.reason || '')}">${st} ${esc(String(q.given || '').slice(0, 30))}</td>`;
    });
    html += `</tr>`;
  });

  html += `
      </tbody>
    </table>
    </div>
    <div class="btn-group" style="margin-top:10px">
      <button class="btn btn-secondary btn-sm" onclick="evalDownloadResults()">⬇ Download JSON</button>
    </div>
  `;

  el.innerHTML = html;
  el.style.display = 'block';
  window.__evalResults = results;
}

function evalDownloadResults() {
  const data = window.__evalResults;
  if (!data) { toast('No results to download', 'error'); return; }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  const name = state.currentSurvey ? state.currentSurvey.name : 'evaluation';
  a.download = `${name}_results.json`;
  a.click();
  URL.revokeObjectURL(a.href);
  toast('Results downloaded', 'success');
}

// Patch loadSurvey to show eval section after loading
const _origLoadSurvey = loadSurvey;
loadSurvey = async function(id) {
  await _origLoadSurvey(id);
  showEvalSection();
};
