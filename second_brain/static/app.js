const $ = (q, root = document) => root.querySelector(q);
const el = (tag, attrs = {}, children = []) => {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
    else if (key === 'text') node.textContent = value;
    else if (key === 'class') node.className = value;
    else if (value !== null && value !== undefined) node.setAttribute(key, value);
  }
  for (const child of Array.isArray(children) ? children : [children]) if (child != null) node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  return node;
};
let language = localStorage.getItem('brain-language') || 'tr';
const tr = (a, b) => language === 'tr' ? a : b;
const labels = {
  dashboard: ['Genel bakış', 'Overview'], memories: ['Hafıza gezgini', 'Memory explorer'], profile: ['Kişisel profil', 'Personal profile'], projects: ['Proje hafızası', 'Project memory'], timeline: ['Zaman çizelgesi', 'Timeline'], graph: ['Bilgi grafiği', 'Knowledge graph'], learning: ['Öğrenme merkezi', 'Learning center'], skills: ['Skill & araçlar', 'Skills & tools'], connections: ['AI bağlantıları', 'AI connections'], capture: ['Yakalama & senkron', 'Capture & sync'], search: ['Hafızada ara', 'Memory search'], comparison: ['Motor karşılaştırma', 'Engine comparison'], benchmarks: ['Benchmark merkezi', 'Benchmark center'], privacy: ['Gizlilik & güvenlik', 'Privacy & security'], backups: ['Yedek & kurtarma', 'Backup & recovery'], diagnostics: ['Sistem tanılama', 'Diagnostics']
};
const icons = ['▦', '◫', '◎', '▱', '◷', '⌘', '✧', '◇', '⬡', '⇄', '⌕', '≋', '▥', '♧', '▤', '⚙'];
const types = ['USER_ASSERTED_FACT', 'USER_PREFERENCE', 'OBSERVED_EVENT', 'MODEL_INFERENCE', 'PROJECT_STATE', 'DECISION', 'CORRECTION', 'LESSON', 'PROCEDURE', 'SKILL', 'POLICY', 'EXTERNAL_KNOWLEDGE'];
const fmt = x => x ? new Date(x).toLocaleString(language === 'tr' ? 'tr-TR' : 'en-US', { dateStyle: 'medium', timeStyle: 'short' }) : '—';
const badge = state => el('span', { class: 'badge ' + state, text: state });
const button = (text, action, cls = '') => el('button', { class: cls, text, onclick: async event => { const b = event.currentTarget; b.disabled = true; try { await action(event); } catch (error) { toast(error.message, true); } finally { b.disabled = false; } } });
const link = (text, hash) => el('a', { href: '#' + hash, class: 'link-button', text });
const field = (label, control, cls = '') => {
  if (!control.id) control.id = 'field-' + crypto.randomUUID();
  return el('div', { class: 'field ' + cls }, [el('label', { text: label, for: control.id }), control]);
};
const input = (placeholder = '', type = 'text', value = '') => el('input', { type, placeholder, value });
const select = values => el('select', {}, values.map(v => el('option', { value: Array.isArray(v) ? v[0] : v, text: Array.isArray(v) ? v[1] : v })));
const empty = (message = tr('Henüz bir kayıt yok.', 'No records yet.')) => el('div', { class: 'empty' }, [el('span', { class: 'empty-icon', text: '◫' }), message]);
function panel(title, body, action) { return el('section', { class: 'panel' }, [el('div', { class: 'panel-header' }, [el('h2', { text: title }), action]), body]); }
function heading(id, subtitle, action) { return el('div', { class: 'page-heading' }, [el('div', {}, [el('p', { class: 'eyebrow', text: 'YOUR INDEPENDENT MEMORY' }), el('h1', { text: labels[id][language === 'tr' ? 0 : 1] }), el('p', { class: 'subtitle', text: subtitle })]), action]); }
function toast(message, error = false) { const target = $('#toast'); target.textContent = message; target.hidden = false; target.classList.toggle('error', error); clearTimeout(toast.timer); toast.timer = setTimeout(() => target.hidden = true, 7000); }
async function api(path, body, method) {
  const options = { method: method || (body === undefined ? 'GET' : 'POST'), headers: { 'X-Brain-Request': '1' } };
  if (body instanceof FormData) options.body = body;
  else if (body !== undefined) { options.headers['Content-Type'] = 'application/json'; options.body = JSON.stringify(body); }
  let response;
  try { response = await fetch('/api/' + path, options); }
  catch { throw new Error(tr('Yerel sunucuya ulaşılamıyor. Start.ps1 ile başlatıp yeniden dene.', 'Cannot reach the local server. Run Start.ps1 and retry.')); }
  let data;
  try { data = await response.json(); }
  catch { throw new Error(tr('Sunucudan geçerli bir yanıt alınamadı.', 'The server returned an invalid response.')); }
  if (!response.ok) {
    const error = new Error(data.error || JSON.stringify(data)); error.status = response.status;
    if (response.status === 403 && data.error === 'Authentication required' && !$('#shell').hidden) {
      $('#dialog').close(); $('#shell').hidden = true; $('#login').hidden = false;
      $('#login-error').textContent = tr('Oturumun sona erdi. Sahip anahtarıyla tekrar giriş yap.', 'Your session expired. Sign in again with your owner key.');
    }
    throw error;
  }
  return data;
}
const action = (operation, args = {}) => api('action/brain.' + operation, args);
function showDialog(title, content) { $('#dialog-content').replaceChildren(el('h2', { text: title }), content); if (!$('#dialog').open) $('#dialog').showModal(); }
function jsonView(data) { return el('pre', { text: typeof data === 'string' ? data : JSON.stringify(data, null, 2) }); }
const jsonDialog = (title, data) => showDialog(title, jsonView(data));
function sourceButton(id) { return button(tr('Kaynağı gör', 'View source') + ' ↗', async () => { const event = await api('events/' + id); const content = el('div', {}, [el('p', { class: 'note', text: tr('Orijinal kaynak içeriği; kullanıcı talimatı sayılmaz.', 'Original source content; not user instructions.') }), jsonView(event)]); for (const asset of event.attachments) content.append(el('a', { href: '/api/assets/' + asset, text: tr('Orijinal dosyayı indir', 'Download original file') })); showDialog(tr('Kaynak kanıtı', 'Source evidence'), content); }, 'link-button'); }
function renderMemory(row, compact = false) {
  const excerpt = row.match ? row.match.text : row.value;
  const actions = el('div', { class: 'row-actions' });
  if (!compact) {
    actions.append(button(tr('İncele', 'Inspect'), () => memoryDetails(row)));
    if (['candidate', 'disputed'].includes(row.status)) {
      actions.append(button(tr('Onayla', 'Approve'), async () => { const result = await api(`memories/${row.id}/approve`, {}); toast(result.status === 'active' ? tr('Hafıza etkinleştirildi.', 'Memory activated.') : tr('Çelişki var; düzeltme bağlantısı gerekli.', 'Conflict detected; explicit correction required.')); await render(); }));
      actions.append(button(tr('Reddet', 'Reject'), async () => { await api(`memories/${row.id}/reject`, {}); await render(); }));
    }
  }
  return el('article', { class: 'memory-row' }, [el('span', { class: 'row-icon', text: row.memory_type === 'POLICY' ? '♧' : row.memory_type === 'DECISION' ? '◇' : '◫' }), el('div', { class: 'row-body' }, [el('div', { class: 'row-title', text: row.subject + ' · ' + row.predicate }), el('div', { class: 'row-value', text: excerpt.slice(0, compact ? 160 : 360) }), row.match ? el('small', { text: tr('Eşleşen kaynak aralığı: ', 'Matching source span: ') + row.match.start_char + '–' + row.match.end_char }) : null, el('div', { class: 'row-meta' }, [badge(row.status), el('span', { class: 'badge', text: row.memory_type }), row.scope, '·', fmt(row.valid_from), sourceButton(row.source_event_ids[0])])]), actions]);
}
async function memoryDetails(row) {
  const content = el('div', {}, [jsonView(row), el('div', { class: 'actions' }, row.source_event_ids.map(sourceButton))]);
  if (row.status === 'active') content.append(el('div', { class: 'actions' }, [button(tr('Düzeltme öner', 'Propose correction'), () => correctionForm(row)), button(tr('Erişimden kaldır', 'Hide current memory'), async () => { await api(`memories/${row.id}/hide`, {}); $('#dialog').close(); await render(); }), button(tr('Kalıcı silme kapsamı', 'Preview permanent erasure'), () => forgetPreview(row), 'danger')]));
  showDialog(tr('Hafıza ayrıntısı', 'Memory details'), content);
}
function correctionForm(row) {
  const value = el('textarea', {}, row.value), date = input('', 'datetime-local'), evidence = el('textarea', { placeholder: tr('Düzeltmenin doğrudan kullanıcı beyanı', 'Direct user assertion supporting the correction') });
  const form = el('form', {}, [field(tr('Yeni değer', 'New value'), value), field(tr('Gerçek dünyada geçerlilik başlangıcı', 'Valid from in the real world'), date), field(tr('Kaynak beyan', 'Source assertion'), evidence)]);
  date.required = true; evidence.required = true;
  form.append(button(tr('Onaya gönder', 'Submit for approval'), async event => { event.preventDefault(); if (!form.reportValidity()) return; const source = await api('events', { source: 'dashboard', source_id: crypto.randomUUID(), actor: 'user', text: evidence.value, scope: row.scope, sensitivity: row.sensitivity }); const result = await action('correct_memory', { id: row.id, value: value.value, valid_from: new Date(date.value).toISOString(), source_event_ids: [source.id] }); $('#dialog').close(); toast(tr('Düzeltme onay bekliyor.', 'Correction awaits approval.')); await memoryDetails(result); }, 'primary'));
  showDialog(tr('Geçmişi koruyarak düzelt', 'Correct while preserving history'), form);
}
async function forgetPreview(row) {
  const preview = await action('forget', { id: row.id });
  const confirmation = input(tr('Kaydın tam kimliğini yaz', 'Type the full memory ID'));
  showDialog(tr('Kalıcı silme', 'Permanent erasure'), el('div', {}, [el('p', { class: 'note', text: preview.warning }), jsonView(preview), field('ID: ' + row.id, confirmation), button(tr('Kaynakları ve türevleri kalıcı sil', 'Permanently erase sources and derivatives'), async () => { if (confirmation.value !== row.id) throw new Error(tr('Tam kayıt kimliği eşleşmeli.', 'Exact memory ID must match.')); await action('forget', { id: row.id, confirmation: row.id }); $('#dialog').close(); toast(tr('Silme tamamlandı.', 'Erasure completed.')); await render(); }, 'danger')]));
}
function newMemory() {
  const kind = select(types), subject = input('', 'text', 'user'), predicate = input(tr('ör. cevap_dili', 'e.g. response_language')), value = el('textarea'), scope = input('', 'text', 'global'), date = input('', 'datetime-local'), sensitivity = select([['1', 'Private'], ['0', 'Shareable'], ['2', 'Sensitive'], ['3', 'Secret']]);
  const form = el('form', { class: 'form-grid' }, [field(tr('Tür', 'Type'), kind), field(tr('Konu', 'Subject'), subject), field(tr('Özellik / ilişki', 'Predicate'), predicate), field(tr('Kapsam / proje', 'Scope / project'), scope), field(tr('Kullanıcının açık beyanı', 'Direct user assertion'), value, 'full'), field(tr('Geçerli olduğu zaman (boş: şimdi)', 'Valid from (empty: now)'), date), field(tr('Gizlilik', 'Sensitivity'), sensitivity)]);
  value.required = true; predicate.required = true;
  form.append(button(tr('Onay kuyruğuna ekle', 'Add to approval queue'), async e => { e.preventDefault(); if (!form.reportValidity()) return; const source = await api('events', { source: 'dashboard', source_id: crypto.randomUUID(), actor: 'user', text: value.value, scope: scope.value, sensitivity: +sensitivity.value }); await api('memories', { memory_type: kind.value, subject: subject.value, predicate: predicate.value, value: value.value, scope: scope.value, sensitivity: +sensitivity.value, source_event_ids: [source.id], valid_from: date.value ? new Date(date.value).toISOString() : null }); $('#dialog').close(); toast(tr('Kayıt onay bekliyor.', 'Memory awaits approval.')); location.hash = 'learning'; await render(); }, 'primary'));
  showDialog(tr('Yeni hafıza', 'New memory'), form);
}
async function dashboard(main) {
  const status = await api('status');
  const memories = await api('search', { query: '', limit: 5 });
  main.append(heading('dashboard', tr('Bütün bilgin, sana ait tek bir yerde. Bugün ne üzerinde çalışıyoruz?', 'All your knowledge in one place you own. What are we working on today?'), button(tr('+ Yeni hafıza', '+ New memory'), newMemory, 'primary')));
  const counts = [['Toplam hafıza', 'Memory records', status.counts.memories, '◫', 'Sürümler ve onay bekleyenler dahil', 'Including versions and candidates'], ['Kaynak olay', 'Source events', status.counts.events, '◷', 'Kaynağı korunan orijinal kayıtlar', 'Original records with provenance'], ['Bekleyen onay', 'Awaiting approval', status.memory_states.filter(x => ['candidate', 'disputed'].includes(x.status)).reduce((a, x) => a + x.count, 0), '✧', 'Etkinleşmeden önce sen incelersin', 'You review before activation'], ['Veri boyutu', 'Data size', (status.storage_bytes / 1048576).toFixed(1) + ' MB', '▤', 'Bu cihazdaki beyin klasörü', 'Brain directory on this device']];
  main.append(el('div', { class: 'stats-grid' }, counts.map(c => el('div', { class: 'stat-card' }, [el('div', { class: 'stat-top' }, [tr(c[0], c[1]), el('span', { class: 'stat-icon', text: c[3] })]), el('div', { class: 'stat-value', text: c[2] }), el('small', { text: tr(c[4], c[5]) })]))));
  main.append(el('div', { class: 'scan-card' }, [el('span', { class: 'scan-mark', text: '✳' }), el('div', {}, [el('h2', { text: tr('Yeni bir modele, aynı hafızayla başla.', 'A new model. The same memory.') }), el('p', { text: tr('“Beynimi tara” ile kaynaklı ve bütçeli bir başlangıç bağlamı oluştur.', 'Create a source-grounded, bounded context with “Scan my brain”.') })]), button(tr('Beynimi tara ↗', 'Scan my brain ↗'), async () => jsonDialog(tr('Başlangıç bağlamı', 'Bootstrap context'), await action('prepare_context', { query: 'Beynimi tara', budget: 6000 })), 'primary')]));
  const recent = memories.items.length ? el('div', {}, memories.items.map(r => renderMemory(r, true))) : empty(tr('Beynin ilk kaydı için hazır. Bir hafıza ekle veya konuşma export’unu içeri al.', 'Your brain is ready for its first record. Add a memory or import a conversation export.'));
  const health = el('div', {}, status.engines.slice(0, 4).map(engine => el('div', { class: 'health-row' }, [el('div', {}, [engine.name, el('small', { text: engine.role || engine.reason })]), badge(engine.status)])));
  const grid = el('div', { class: 'grid' }, [el('div', {}, [panel(tr('Son geçerli hafızalar', 'Recent active memories'), recent, link(tr('Tümünü gör →', 'View all →'), 'memories')), panel(tr('Çalışma ilkesi', 'How your brain works'), el('p', { class: 'note', text: tr('Kaynaklar korunur. Çıkarımlar ayrı tutulur. Değişen bilgiler geçmişi silmez. Hiçbir model tek başına kanonik gerçeğin sahibi olmaz.', 'Sources are preserved. Inferences stay distinct. Changes preserve history. The canonical brain stays independent of every model.') }))]), el('div', {}, [panel(tr('Motor durumu', 'Engine status'), health, link(tr('Tanılama →', 'Diagnostics →'), 'diagnostics')), panel(tr('Hızlı erişim', 'Quick access'), el('div', { class: 'stack' }, [link(tr('↓ Konuşma veya dosya içeri al', '↓ Import conversations or files'), 'capture'), link(tr('◇ AI bağlantısını yapılandır', '◇ Configure an AI connection'), 'connections'), link(tr('▤ Şifreli yedek oluştur', '▤ Create an encrypted backup'), 'backups')])), panel(tr('Model maliyeti', 'Model cost'), el('div', {}, [el('div', { class: 'stat-value', text: '$' + status.usage.cost.toFixed(4) }), el('small', { text: tr(`${status.usage.calls} kayıtlı model çağrısı · Bulut harcaması kapalı`, `${status.usage.calls} recorded model calls · Cloud spending disabled`) })]))])]);
  main.append(grid);
}
async function memoryPage(main, id, defaults = {}) {
  main.append(heading(id, tr('Kaynağına, kapsamına ve geçerlilik zamanına göre incele.', 'Explore by evidence, scope and validity.'), button(tr('+ Yeni hafıza', '+ New memory'), newMemory, 'primary')));
  const query = input(tr('Hafızanda ne arıyorsun?', 'What are you looking for?'));
  const kind = select([['', tr('Tüm hafıza türleri', 'All memory types')], ...types]);
  const engine = select([['economy', tr('Ekonomik · indeks + bağlantılar', 'Economy · index + links')], ['fts', 'SQLite FTS5'], ['bm25', 'BM25'], ['hybrid', 'Hybrid'], ['vector', 'Semantic · MiniLM'], ['graph', 'Graph + lexical'], ['mem0', 'Mem0 · local projection']]);
  const scope = input('Scope', 'text', defaults.scope || ''), valid = input('', 'datetime-local'), known = input('', 'datetime-local'), source = input(tr('Kaynak sistemi', 'Source system'));
  const results = el('div'); const meta = el('p', { class: 'metric-note' }); let offset = 0;
  query.setAttribute('aria-label', tr('Hafıza sorgusu', 'Memory query')); kind.setAttribute('aria-label', tr('Hafıza türü', 'Memory type')); engine.setAttribute('aria-label', tr('Arama motoru', 'Search engine'));
  const previous = button(tr('← Önceki', '← Previous'), async () => { offset = Math.max(0, offset - 100); await find(false); });
  const next = button(tr('Sonraki →', 'Next →'), async () => { offset += 100; await find(false); });
  async function find(reset = true) { if (reset) offset = 0; const result = await api('search', { query: query.value, engine: engine.value, memory_type: kind.value || null, scope: scope.value || null, valid_at: valid.value ? new Date(valid.value).toISOString() : null, known_at: known.value ? new Date(known.value).toISOString() : null, source: source.value || null, limit: 100, offset, ...defaults }); results.replaceChildren(...(result.items.length ? result.items.map(r => renderMemory(r)) : [empty(tr('Bu kapsam ve zamanda destekleyen bir kanıt bulunamadı.', 'No supporting evidence in this scope and time.'))])); meta.textContent = `${offset + 1}–${offset + result.items.length} · ${result.elapsed_ms} ms · ${result.engine}`; previous.disabled = offset === 0; next.hidden = result.items.length < 100; }
  const form = el('form', {}, [el('div', { class: 'filters' }, [query, kind, engine]), el('div', { class: 'filter-more' }, [field('Scope', scope), field(tr('Geçerli olduğu zaman', 'Valid time'), valid), field(tr('Sistemin bildiği zaman', 'Known time'), known), field(tr('Kaynak', 'Source'), source)]), button(tr('Ara', 'Search'), async e => { e.preventDefault(); await find(); }, 'primary')]);
  main.append(panel(tr('Hafıza sorgusu', 'Memory query'), form), panel(tr('Kanıta dayalı sonuçlar', 'Evidence-grounded results'), el('div', {}, [meta, results, el('div', { class: 'actions' }, [previous, next])])));
  await find();
}
async function projects(main) {
  const result = await api('search', { query: '', limit: 100 });
  const scopes = [...new Set(result.items.map(r => r.scope).filter(s => s !== 'global'))];
  main.append(heading('projects', tr('Proje kararları, mevcut durum ve geçmiş tek bir kapsamda.', 'Project decisions, current state and history in one scope.'), button(tr('+ Proje kaydı', '+ Project memory'), newMemory, 'primary')));
  main.append(scopes.length ? el('div', { class: 'project-grid' }, scopes.map(scope => panel(scope, el('div', {}, [el('p', { class: 'note', text: `${result.items.filter(r => r.scope === scope).length} ${tr('görüntülenen geçerli kayıt', 'visible active records')}` }), button(tr('Proje bağlamını aç →', 'Open project context →'), async () => jsonDialog(scope, await action('get_project_state', { scope })))])))) : empty(tr('Proje hafızası eklerken kapsam alanına proje adını yaz.', 'Set the scope to a project name when adding memory.')));
}
async function timeline(main) {
  main.append(heading('timeline', tr('Orijinal olaylar ve kaynak zamanları. Model yorumlarından ayrı.', 'Original events and source timestamps, separate from model interpretations.')));
  const list = el('div'); let offset = 0;
  const more = button(tr('Daha eski olaylar', 'Older events'), async () => { offset += 100; await load(); });
  async function load() { const events = await action('timeline', { limit: 100, offset }); if (!events.length && !offset) list.append(empty()); for (const event of events) list.append(el('article', { class: 'memory-row' }, [el('span', { class: 'row-icon', text: '◷' }), el('div', { class: 'row-body' }, [el('div', { class: 'row-title', text: event.event_type + ' · ' + event.actor }), el('p', { class: 'row-value', text: event.text.slice(0, 300) }), el('div', { class: 'row-meta' }, [badge(event.source), event.scope, fmt(event.occurred_at), sourceButton(event.id)]), button(tr('Açık tercih/kural çıkar', 'Extract explicit preference/rule'), async () => jsonDialog(tr('Çıkarım sonucu', 'Extraction result'), await api('extract/' + event.id, {})), 'link-button')])])); more.hidden = events.length < 100; }
  main.append(panel(tr('Olay arşivi', 'Event archive'), el('div', {}, [list, more]))); await load();
}
async function graph(main) {
  const data = await api('graph');
  main.append(heading('graph', tr('Yalnızca geçerli ve onaylı kayıtların ilişkileri.', 'Relationships from current, approved records.')));
  if (!data.nodes.length) { main.append(empty(tr('İlişkileri görmek için hafıza ekleyip onayla.', 'Add and approve memory to see relationships.'))); return; }
  const ns = 'http://www.w3.org/2000/svg', svg = document.createElementNS(ns, 'svg'); svg.classList.add('graph'); svg.setAttribute('viewBox', '0 0 900 480'); svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', tr('Hafıza ilişkileri', 'Memory relationships'));
  const coords = new Map(data.nodes.map((node, i) => [node.id, { x: 450 + Math.cos(i / data.nodes.length * Math.PI * 2) * 310, y: 240 + Math.sin(i / data.nodes.length * Math.PI * 2) * 175 }]));
  function shape(tag, attrs, text) { const node = document.createElementNS(ns, tag); for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v); if (text) node.textContent = text; return node; }
  for (const edge of data.edges) { const a = coords.get(edge.source), b = coords.get(edge.target); svg.append(shape('line', { x1: a.x, y1: a.y, x2: b.x, y2: b.y }), shape('text', { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2, class: 'edge-label' }, edge.label.slice(0, 25))); }
  for (const node of data.nodes) { const p = coords.get(node.id), g = shape('g', { tabindex: 0, role: 'button', 'aria-label': node.label }); g.append(shape('circle', { cx: p.x, cy: p.y, r: node.kind === 'subject' ? 21 : 14 }), shape('text', { x: p.x, y: p.y + 36, 'text-anchor': 'middle' }, node.label.slice(0, 27))); const inspect = () => jsonDialog(node.label, data.edges.filter(e => e.source === node.id || e.target === node.id)); g.addEventListener('click', inspect); g.addEventListener('keydown', e => { if (e.key === 'Enter') inspect(); }); svg.append(g); }
  const merge = button(tr('Varlıkları birleştir', 'Merge entities'), () => {
    const canonical = input(tr('Kanonik ad', 'Canonical name')), alias = input(tr('Diğer ad', 'Alias name'));
    showDialog(tr('Kaynak geçmişini koruyarak birleştir', 'Merge while preserving source history'), el('div', {}, [field(tr('Kanonik ad', 'Canonical name'), canonical), field(tr('Diğer mevcut ad', 'Existing alias name'), alias), button(tr('Birleştir', 'Merge'), async () => { const result = await api('entities/merge', { canonical: canonical.value, alias: alias.value }); jsonDialog(tr('Birleştirme sonucu', 'Merge result'), result); }, 'primary')]));
  });
  main.append(panel(tr('Kaynaklı ilişki görünümü', 'Evidence-linked relationship view'), svg, merge));
}
async function learning(main) {
  main.append(heading('learning', tr('Düzeltmelerden ders çıkar. Kalıcı davranış değişikliklerini sen onayla.', 'Learn from corrections. You approve persistent behavior changes.')));
  const pending = await Promise.all(['candidate', 'disputed'].map(status => api('search', { query: '', status, limit: 100 })));
  const candidates = pending.flatMap(result => result.items);
  main.append(panel(tr('İncelemeni bekleyenler', 'Awaiting your review'), candidates.length ? el('div', {}, candidates.map(r => renderMemory(r))) : empty(tr('Onay kuyruğu boş.', 'Approval queue is empty.'))));
  const text = el('textarea', { placeholder: tr('Öğrenilmesini istediğin düzeltme veya başarılı yöntem', 'Correction or successful procedure to learn') }), scope = input('', 'text', 'global'), outcome = select([['correction', tr('Düzeltme', 'Correction')], ['success', tr('Başarılı deneyim', 'Success')], ['failure', tr('Başarısız deneyim', 'Failure')]]);
  main.append(panel(tr('Geri bildirim kaydet', 'Record feedback'), el('div', {}, [field(tr('Deneyim / düzeltme', 'Experience / correction'), text), el('div', { class: 'form-grid' }, [field('Scope', scope), field(tr('Sonuç', 'Outcome'), outcome)]), button(tr('Kaydet', 'Record'), async () => { const result = await action('record_feedback', { text: text.value, scope: scope.value, outcome: outcome.value }); jsonDialog(tr('Öğrenme sonucu', 'Learning result'), result); }, 'primary'), el('p', { class: 'metric-note', text: tr('Üç farklı kaynak olayından sonra ders adayı oluşur. Başarısız deneyimler tek başına skill oluşturmaz.', 'Three distinct evidence events produce a lesson candidate. Failed experiences alone never produce skills.') })])));
  const feedback = await api('feedback');
  main.append(panel(tr('Öğrenme geçmişi', 'Learning history'), feedback.length ? table([tr('Ders', 'Lesson'), 'Scope', tr('Sonuç', 'Outcome'), tr('Kanıt', 'Evidence')], feedback.map(r => [r.lesson, r.scope, r.outcome, r.evidence_count])) : empty()));
}
function table(headers, rows) {
  const head = el('thead', {}, el('tr', {}, headers.map(h => el('th', { text: h }))));
  const body = el('tbody', {}, rows.map(row => el('tr', {}, row.map(cell => el('td', {}, cell instanceof Node ? cell : String(cell ?? '—'))))));
  return el('div', { class: 'table-wrap' }, el('table', {}, [head, body]));
}
async function skills(main) {
  main.append(heading('skills', tr('Taşınabilir prosedürler. Gerçek yetenek ve bağımlılık denetimiyle.', 'Portable procedures with explicit capability and dependency checks.')));
  const file = input('', 'file'); file.accept = '.zip';
  main.append(panel(tr('Agent Skills paketi', 'Agent Skills package'), el('div', {}, [el('p', { class: 'note', text: tr('ZIP kökünde SKILL.md ve isteğe bağlı manifest.json, scripts/, references/, assets/ bulunmalı. Betikler otomatik çalıştırılmaz.', 'ZIP root must contain SKILL.md, optionally manifest.json, scripts/, references/, assets/. Scripts never run automatically.') }), file, button(tr('Paketi incelemeye al', 'Import for review'), async () => { if (!file.files.length) throw new Error(tr('Önce ZIP seç.', 'Select a ZIP first.')); const data = new FormData(); data.append('file', file.files[0]); await api('skills/import', data); await render(); }, 'primary')])));
  const entries = await action('list_skills');
  const rows = entries.map(row => {
    const actions = el('div', { class: 'actions' }, [
      button(tr('Tanımı aç', 'View definition'), () => jsonDialog(row.name, row.content)),
      button(tr('Uyumluluk denetle', 'Check compatibility'), async () => jsonDialog(tr('Yetenek eşlemesi', 'Capability mapping'), await api(`skills/${row.id}/compatibility`, {}))),
      button(row.state === 'enabled' ? tr('Devre dışı bırak', 'Disable') : tr('Bu sürümü etkinleştir', 'Enable this version'), async () => { await api(`skills/${row.id}/state`, { enabled: row.state !== 'enabled' }); await render(); }),
      el('a', { href: `/api/skills/${row.id}/export`, text: tr('Paketi dışa aktar', 'Export package') })
    ]);
    return el('article', { class: 'memory-row' }, [el('span', { class: 'row-icon', text: '◇' }), el('div', { class: 'row-body' }, [el('h3', { text: row.name + ' · v' + row.version }), el('p', { class: 'row-value', text: row.description }), badge(row.state), actions])]);
  });
  main.append(panel(tr('Skill sürümleri', 'Skill versions'), rows.length ? el('div', {}, rows) : empty()));
  main.append(await toolPanel());
}
async function toolPanel() {
  const entries = await api('tools'), name = input('python'), binary = select(['python', 'node', 'git', 'tesseract', 'ffmpeg', 'ollama']);
  const body = el('div', {}, [el('p', { class: 'note', text: tr('Tanım etkinliği, keyfi kod çalıştırma izni vermez. Sağlık denetimi yalnız sabit --version sorgusunu çalıştırır.', 'Enabling a definition does not grant arbitrary execution. Probes only run a fixed --version query.') }), el('div', { class: 'form-grid' }, [field(tr('Envanter adı', 'Inventory name'), name), field(tr('Yerel binary', 'Local binary'), binary)]), button(tr('Araç tanımı ekle', 'Add tool definition'), async () => { await api('tools', { name: name.value || binary.value, kind: 'binary', config: { binary: binary.value } }); await render(); }, 'primary')]);
  if (entries.length) body.append(table(['Name', 'Kind', 'State', ''], entries.map(row => [row.name, row.kind, row.enabled ? 'enabled' : 'disabled', el('div', { class: 'actions' }, [button(tr('Sağlığı denetle', 'Probe health'), async () => jsonDialog(row.name, await api(`tools/${row.id}/probe`, {}))), button(row.enabled ? tr('Kapat', 'Disable') : tr('Etkinleştir', 'Enable'), async () => { await api(`tools/${row.id}/state`, { enabled: !row.enabled }); await render(); })])])));
  return panel(tr('Araç & MCP envanteri', 'Tool & MCP inventory'), body);
}
async function connections(main) {
  const data = await action('list_capabilities');
  main.append(heading('connections', tr('Her istemcinin gerçek erişim sınırları ayrı gösterilir.', 'Each client’s actual integration capabilities are listed separately.')));
  const contract = await api('assistant-contract');
  const portable = contract.instructions + '\nManual JSON format (replace example values with actual conversation evidence):\n' + JSON.stringify(contract.example, null, 2);
  const instructions = el('textarea', { readonly: '', rows: '9', 'aria-label': tr('AI hafıza talimatı', 'AI memory instructions') }, portable);
  main.append(panel(tr('Gereken bilgileri beyne kaydet', 'Save useful information to the brain'), el('div', {}, [
    el('p', { class: 'note', text: tr('Bilgiyi konuştuğun yapay zekâ seçer. Beyin ayrı bir model çağırmadan kaydeder ve indekslerle arar. Talimatı bağlı istemcinin kalıcı talimatlarına ekleyebilirsin; MCP bağlantısı ve platform izinleri gerekir. Ek sohbet kullanımı mevcut hesabının kotasına veya ücretine yansıyabilir.', 'Your conversation AI selects facts. The brain saves and searches indexes without a separate model call. Add these instructions to a connected client; MCP access and host permissions are required. Extra conversation usage can affect your existing quota or bill.') }),
    instructions,
    button(tr('Talimatı kopyala', 'Copy instructions'), async () => { await navigator.clipboard.writeText(portable); toast(tr('Talimat kopyalandı.', 'Instructions copied.')); }),
    el('p', { class: 'metric-note', text: tr('Açık kullanıcı beyanları direct_user ile kaydedildiğinde sıradan bilgiler ve güncellemeler ayrıca onay istemez. Belirsiz çıkarımlar ve davranış/skill değişiklikleri Öğrenme merkezinde incelenir. Ekonomik arama ayrı model çağırmaz.', 'Ordinary explicit user statements and updates saved as direct_user need no second approval. Uncertain inferences and behavior/skill changes remain in Learning center for review. Economy retrieval calls no separate model.') })
  ])));
  const packet = el('textarea', { placeholder: JSON.stringify(contract.example, null, 2), rows: '8', 'aria-label': tr('AI hafıza JSON paketi', 'AI memory JSON packet') });
  main.append(panel(tr('Bağlantısız platformdan aktar', 'Import from an unconnected platform'), el('div', {}, [
    el('p', { class: 'note', text: tr('AI’nın gerçek konuşmadan hazırladığı JSON paketini yapıştır. Kaynak alıntısı ve kısa kayıtlar birlikte alınır; yükleme için ikinci bir model kullanılmaz.', 'Paste the JSON packet prepared from your actual conversation. The source excerpt and compact facts are imported together without a second model.') }),
    packet,
    button(tr('Paketi kaydet', 'Save packet'), async () => {
      const result = await action('remember', JSON.parse(packet.value));
      packet.value = ''; jsonDialog(tr('Kayıt sonucu', 'Save result'), result);
    }, 'primary')
  ])));
  main.append(panel(tr('İstemci yetenekleri', 'Client capabilities'), table(['Client', tr('Geçmiş', 'History'), tr('Canlı yakalama yöntemi', 'Capture method'), tr('Okuma / yazma', 'Read / write'), tr('Doğrulanan kapsam', 'Verification scope')], data.client_integrations.map(c => [c.client, c.history, c.capture, c.read + ' / ' + c.write, c.verified]))));
  const host = select(['codex', 'claude-code', 'gemini-cli', 'cursor']);
  main.append(panel(tr('Bağlantı kurulumu', 'Connection setup'), el('div', {}, [el('p', { class: 'note', text: tr('Önce Gizlilik & Güvenlik alanından kısıtlı model token’ı üret. Aşağıdaki komut mevcut yapılandırmayı değiştirmeden birleştirilecek örnekleri verir. Canlı capture, istemcide hook güveni ve etkinleştirme gerektirir.', 'Create a restricted model token in Privacy & Security. This command generates examples to merge with existing configuration. Live capture requires host hook trust and activation.') }), host, button(tr('Kurulum komutunu göster', 'Show setup command'), () => jsonDialog(tr('Yerel terminal', 'Local terminal'), `.\\.venv\\Scripts\\python.exe -m second_brain client-config --client ${host.value}`)), el('p', { class: 'note', text: tr('ChatGPT web için localhost evrensel olarak erişilebilir değildir. Hesap desteği ve kimlik doğrulamalı uzak MCP kurulumu olmadan bağlı gösterilmez.', 'ChatGPT web cannot universally reach localhost. It is not marked connected without account support and authenticated remote MCP hosting.') })])));
}
async function capture(main) {
  main.append(heading('capture', tr('Orijinal konuşmaları ve dosyaları koruyarak içeri al.', 'Import and preserve original conversations and files.')));
  const file = input('', 'file'), scope = input('', 'text', 'global'), sensitivity = select([['1', 'Private'], ['0', 'Shareable'], ['2', 'Sensitive'], ['3', 'Secret']]);
  main.append(panel(tr('Yeni kaynak', 'New source'), el('div', { class: 'upload-zone' }, [el('h3', { text: tr('ChatGPT export ZIP / JSON veya yerel dosya', 'ChatGPT export ZIP / JSON or local file') }), el('p', { class: 'note', text: tr('PDF, DOCX, Markdown, kod, CSV, JSON ve medya orijinalleri desteklenir. Görsel/ses/video içerik çıkarımı için yapılandırılmış yerel işlemci gerekir.', 'PDF, DOCX, Markdown, code, CSV, JSON and media originals are supported. Image/audio/video content extraction needs a configured local processor.') }), field(tr('Dosya (en fazla 100 MiB)', 'File (up to 100 MiB)'), file), el('div', { class: 'form-grid' }, [field('Scope', scope), field(tr('Gizlilik', 'Sensitivity'), sensitivity)]), button(tr('İçeri aktarma kuyruğuna ekle', 'Queue import'), async () => { if (!file.files.length) throw new Error(tr('Dosya seçilmedi.', 'No file selected.')); const form = new FormData(); form.append('file', file.files[0]); form.append('scope', scope.value); form.append('sensitivity', sensitivity.value); const job = await api('import', form); toast(tr('İş kuyruğa eklendi: ', 'Job queued: ') + job.id); await render(); }, 'primary')])));
  const data = await action('sync_status');
  main.append(panel(tr('Kalıcı iş kuyruğu', 'Persistent job queue'), data.jobs.length ? table(['ID / Type', tr('Durum', 'State'), tr('Deneme', 'Attempts'), tr('İlerleme / sonuç', 'Progress / result'), ''], data.jobs.map(job => [job.id.slice(0, 10) + ' · ' + job.kind, badge(job.state), job.attempts, job.error || job.result || '—', el('div', { class: 'actions' }, [button(tr('İncele', 'Inspect'), () => jsonDialog('Job ' + job.id, job)), ['dead', 'cancelled'].includes(job.state) ? button(tr('Yeniden dene', 'Retry'), async () => { await api('jobs/' + job.id + '/retry', {}); await render(); }) : null, ['pending', 'running'].includes(job.state) ? button(tr('İşi iptal et', 'Cancel job'), async () => { await api('jobs/' + job.id + '/cancel', {}); toast(tr('İş iptal edildi. Kaydedilmiş adaylar ve orijinal korunur.', 'Job cancelled. Existing candidates and original are retained.')); await render(); }, 'danger') : null])])) : empty()));
  main.append(panel('Checkpoints', data.checkpoints.length ? table(['Source', 'Cursor', 'Version', 'Updated'], data.checkpoints.map(c => [c.source, c.cursor, c.adapter_version, fmt(c.updated_at)])) : empty(), button(tr('Yenile', 'Refresh'), render, 'quiet')));
  const assets = await api('assets');
  const capabilities = await api('media/capabilities');
  main.append(panel(tr('Yerel medya işlemcileri', 'Local media processors'), el('div', {}, [table([tr('İşlem', 'Processor'), tr('Durum', 'State')], [['Image OCR', capabilities.images.ocr], ['Speech → text', capabilities.audio.automatic_transcription], ['Video OCR + audio', capabilities.video.automatic_extraction]]), el('p', { class: 'note', text: tr('Çıktılar kaynak konumuyla birlikte onay bekleyen belge bilgisi olur. Küçük ses modeli hata yapabilir; video 15 saniye arayla örneklenir. Sonucu orijinalinden kontrol et.', 'Outputs become document candidates with source locations. The small speech model can make errors; video is sampled every 15 seconds. Check results against the original.') })])));
  function processAsset(asset) {
    const operations = asset.mime.startsWith('image/') ? [['ocr', 'Image OCR']] : asset.mime === 'application/pdf' ? [['pdf_ocr', tr('Taranmış sayfalara OCR', 'Scanned page OCR')]] : asset.mime.startsWith('video/') ? [['video', tr('Video kareleri + ses', 'Video frames + audio')], ['transcribe', tr('Yalnız ses dökümü', 'Audio transcription only')]] : [['transcribe', tr('Ses dökümü', 'Speech transcription')]];
    const operation = select(operations), language = select([['', tr('Otomatik dil', 'Detect language')], ['tr', 'Türkçe'], ['en', 'English'], ['de', 'Deutsch'], ['fr', 'Français'], ['es', 'Español']]);
    showDialog(tr('Yerel dosyayı işle', 'Process local asset'), el('div', {}, [el('p', { class: 'note', text: asset.name }), field(tr('İşlem', 'Operation'), operation), field(tr('Konuşma dili', 'Speech language'), language), el('p', { class: 'note', text: tr('İşlem bu cihazda kuyrukta çalışır. Sayfayı yenileyerek ilerlemeyi görebilir, işi iptal edebilirsin. Orijinal dosya korunur.', 'Processing runs in the local job queue. Refresh to view progress or cancel. The original file is retained.') }), button(tr('İşleme kuyruğuna ekle', 'Queue processing'), async () => { const job = await api(`assets/${asset.id}/process`, { operation: operation.value, language: ['transcribe', 'video'].includes(operation.value) ? language.value || null : null }); $('#dialog').close(); toast(tr('İş kuyruğa eklendi: ', 'Job queued: ') + job.id); await render(); }, 'primary')]));
  }
  function sidecar(asset) {
    const kind = select(['transcript', 'caption', 'ocr', 'video_notes']), location = input(tr('ör. 00:10–00:35 veya sayfa 2', 'e.g. 00:10–00:35 or page 2')), text = el('textarea');
    showDialog(tr('Orijinale bağlı türev', 'Derivative linked to original'), el('div', {}, [el('p', { class: 'note', text: asset.name }), field(tr('Türev türü', 'Derivative kind'), kind), field(tr('Kaynak konumu / zaman aralığı', 'Source location / time range'), location), field(tr('Metin', 'Text'), text), button(tr('Aday olarak kaydet', 'Save as candidate'), async () => { const result = await api(`assets/${asset.id}/derivative`, { text: text.value, kind: kind.value, location: location.value }); jsonDialog(tr('Türev sonucu', 'Derivative result'), result); }, 'primary')]));
  }
  main.append(panel(tr('Korunan orijinal dosyalar', 'Preserved original assets'), assets.length ? table(['File', 'Type', 'Scope', ''], assets.map(asset => [asset.name, asset.mime, asset.scope, el('div', { class: 'actions' }, [el('a', { href: `/api/assets/${asset.id}`, text: tr('İndir', 'Download') }), button(tr('Türev ekle', 'Add derivative'), () => sidecar(asset)), /^(image|audio|video)\//.test(asset.mime) || asset.mime === 'application/pdf' ? button(tr('Yerel işlemci', 'Local processor'), () => processAsset(asset)) : null])])) : empty()));
}
async function comparison(main) {
  main.append(heading('comparison', tr('Aynı kanonik hafızada aynı soruyu motorlar arasında karşılaştır.', 'Compare engines on the same query and canonical memory.')));
  const query = input(tr('Soru / arama', 'Question / query')), result = el('div');
  main.append(panel(tr('Karşılaştırma', 'Comparison'), el('div', { class: 'search-main' }, [query, button(tr('Karşılaştır', 'Compare'), async () => { result.replaceChildren(); for (const engine of ['fts', 'bm25', 'hybrid']) { const data = await api('search', { query: query.value, engine, limit: 5 }); result.append(panel(`${engine} · ${data.elapsed_ms} ms`, data.items.length ? el('div', {}, data.items.map(r => renderMemory(r, true))) : empty())); } }, 'primary')])), result);
}
async function benchmarks(main) {
  main.append(heading('benchmarks', tr('Sentetik Türkçe değerlendirme. Sonuçlar ölçülür, hazır başarı değeri kullanılmaz.', 'Synthetic Turkish evaluation. Results are measured, never preset.')));
  const split = select([['validation', 'Validation · 100'], ['development', 'Development · 300'], ['test', 'Locked test · 100'], ['all', 'All · 500']]), result = el('div');
  main.append(panel('SecondBrain-TR-Eval', el('div', {}, [el('p', { class: 'note', text: tr('Bu küme şablon tabanlı sentetik bir regresyon testidir; gerçek konuşma kalitesi veya modelin cevap doğruluğu ölçümü değildir. Kilitli test bölümü karşılaştırma geliştirmesinde kullanılmamalı.', 'This template-generated synthetic suite measures regression behavior, not real conversation quality or model answer accuracy. Keep the test split out of tuning.') }), split, button(tr('Değerlendirmeyi çalıştır', 'Run evaluation'), async () => { result.replaceChildren(el('p', { text: tr('Testler çalışıyor…', 'Running evaluation…') })); const data = await api('benchmarks', { split: split.value }); result.replaceChildren(jsonView(data)); }, 'primary')])), result);
  const runs = await api('benchmarks');
  main.append(panel(tr('Ölçüm geçmişi', 'Evaluation history'), runs.length ? table(['Date', 'ID', ''], runs.map(r => [fmt(r.created_at), r.id.slice(0, 10), button(tr('Raporu aç', 'Open report'), () => jsonDialog(r.id, JSON.parse(r.result)))])) : empty()));
}
async function privacy(main) {
  main.append(heading('privacy', tr('Kapsamlı izinler, kaynak ayrımı ve denetlenebilir erişim.', 'Scoped permissions, provenance boundaries and auditable access.')));
  main.append(panel(tr('Veri sahipliği', 'Data ownership'), el('div', {}, [el('p', { class: 'note', text: tr('Ham dosyalar AES-256-GCM ile, yedekler parola ile şifrelenir. Kanonik SQLite alanları ve arama indeksleri okunabilir; cihaz diski şifrelemesi önerilir. Dışarıdaki export/yedek kopyaları uygulamanın kontrolünde değildir.', 'Raw files use AES-256-GCM; backups use passphrase encryption. Canonical SQLite fields and search indexes are plaintext; use device disk encryption. External export/backup copies are outside application control.') }), el('div', { class: 'actions' }, ['json', 'jsonl', 'markdown'].map(format => el('a', { href: '/api/export/' + format, text: tr('Dışa aktar · ', 'Export · ') + format.toUpperCase() })))])));
  const name = input(tr('ör. Codex', 'e.g. Codex')), scopes = input('', 'text', 'global'), clearance = select([['1', 'Private'], ['0', 'Shareable'], ['2', 'Sensitive']]);
  main.append(panel(tr('Kısıtlı model erişimi oluştur', 'Create restricted model access'), el('div', {}, [el('div', { class: 'form-grid' }, [field(tr('Bağlantı adı', 'Connection name'), name), field(tr('İzinli kapsamlar (virgülle)', 'Allowed scopes (comma-separated)'), scopes), field(tr('Gizlilik üst sınırı', 'Maximum clearance'), clearance)]), button(tr('Token üret', 'Generate token'), async () => { const data = await api('tokens', { name: name.value || 'model', principal: { id: 'model-' + crypto.randomUUID(), tenant: 'local', role: 'agent', scopes: scopes.value.split(',').map(s => s.trim()).filter(Boolean), permissions: ['read', 'propose', 'capture'], clearance: +clearance.value } }); showDialog(tr('Token yalnızca şimdi gösterilir', 'Token is shown only now'), el('div', {}, [el('p', { class: 'note', text: tr('SB_TOKEN ortam değişkenine kaydet. Bu token onaylama, silme ve yönetim yetkisi vermez.', 'Save as SB_TOKEN. This token grants no approval, erasure or administration permissions.') }), jsonView(data)])); }, 'primary')])));
  const tokens = await api('tokens');
  main.append(panel(tr('Bağlantı anahtarları', 'Connection keys'), tokens.length ? table(['Name', 'Created', 'State', ''], tokens.map(t => [t.name, fmt(t.created_at), t.revoked ? 'revoked' : 'active', t.revoked ? '—' : button(tr('İptal et', 'Revoke'), async () => { await api('tokens/' + t.id, undefined, 'DELETE'); await render(); }, 'danger')])) : empty()));
  const audit = await api('audit'); main.append(panel(tr('Erişim ve işlem günlüğü', 'Access and operation audit'), audit.length ? table(['Time', 'Actor', 'Action', 'Target'], audit.map(a => [fmt(a.created_at), a.actor, a.action, a.target?.slice(0, 14)])) : empty()));
}
async function backups(main) {
  main.append(heading('backups', tr('Şifreli snapshot, bütünlük kontrolü ve silme günlüğüyle geri yükleme.', 'Encrypted snapshots, integrity checks and restore with erasure replay.')));
  const password = input(tr('En az 12 karakter', 'At least 12 characters'), 'password');
  main.append(panel(tr('Yeni şifreli yedek', 'New encrypted backup'), el('div', {}, [field(tr('Yedek parolası', 'Backup passphrase'), password), button(tr('Yedek oluştur', 'Create backup'), async () => { await api('backups', { password: password.value }); password.value = ''; toast(tr('Şifreli yedek oluşturuldu.', 'Encrypted backup created.')); await render(); }, 'primary'), el('p', { class: 'metric-note', text: tr('Parola saklanmaz; kaybolursa yedek açılamaz. Kalıcı silme, yönetilen eski yedekleri de geçersiz kılıp kaldırır.', 'The passphrase is not stored. Lost passphrases cannot be recovered. Permanent erasure invalidates and removes managed older backups.') })])));
  const upload = input('', 'file'), uploadPassword = input('', 'password'); upload.accept = '.sbbackup';
  main.append(panel(tr('Dış yedeği doğrulayarak içeri al', 'Import and verify an external backup'), el('div', {}, [field(tr('Yedek dosyası', 'Backup file'), upload), field(tr('Yedek parolası', 'Backup passphrase'), uploadPassword), button(tr('İçeri al ve doğrula', 'Import and verify'), async () => { if (!upload.files.length) throw new Error(tr('Yedek dosyası seç.', 'Select a backup file.')); const body = new FormData(); body.append('file', upload.files[0]); body.append('password', uploadPassword.value); const result = await api('backups/import', body); uploadPassword.value = ''; jsonDialog(tr('Yedek doğrulandı; geri yükleme ayrı onay gerektirir', 'Backup verified; restore requires separate confirmation'), result); }, 'primary')])));
  const list = await api('backups');
  function backupAction(row, restore) { const pass = input('', 'password'), confirm = input(tr('Yedek kimliğini yaz', 'Type the backup ID')); const fields = [field(tr('Yedek parolası', 'Backup passphrase'), pass)]; if (restore) fields.push(el('p', { class: 'note', text: tr('Mevcut beyin snapshot ile değişir. Güncel silme kayıtları korunur. Önce güncel bir yedek oluştur.', 'The snapshot replaces the current brain. Current erasure records are retained. Create a current backup first.') }), field('ID: ' + row.id, confirm)); fields.push(button(restore ? tr('Geri yükle', 'Restore') : tr('Bütünlüğü doğrula', 'Verify integrity'), async () => { const result = await api(`backups/${row.id}/${restore ? 'restore' : 'verify'}`, { password: pass.value, confirmation: confirm.value }); jsonDialog(tr('İşlem sonucu', 'Operation result'), result); }, restore ? 'danger' : 'primary')); showDialog(row.id, el('div', {}, fields)); }
  main.append(panel(tr('Yönetilen yedekler', 'Managed backups'), list.length ? table(['ID', 'MB', ''], list.map(row => [row.id, (row.size / 1048576).toFixed(2), el('div', { class: 'actions' }, [button(tr('Doğrula', 'Verify'), () => backupAction(row, false)), button(tr('Geri yükle', 'Restore'), () => backupAction(row, true)), el('a', { href: `/api/backups/${row.id}/download`, text: tr('İndir', 'Download') })])])) : empty()));
}
async function diagnostics(main) {
  const data = await api('diagnostics');
  main.append(heading('diagnostics', tr('Sağlık, motorlar, kaynak kullanımı ve açık sınırlamalar.', 'Health, engines, resource use and explicit limitations.')));
  main.append(panel(tr('Motorlar', 'Engines'), table(['Engine', 'Status', 'Details'], data.engines.map(e => [e.name, badge(e.status), e.reason || e.role]))), panel(tr('Bakım işlemleri', 'Maintenance'), el('div', { class: 'actions' }, [button(tr('FTS / graph yeniden oluştur', 'Rebuild FTS / graph'), async () => jsonDialog('Reindex', await api('reindex', {}))), button(tr('Yerel vektör indeksi oluştur', 'Build local vector index'), async () => jsonDialog('Vector index', await api('reindex', { vectors: true })))])), panel(tr('Sistem bilgisi', 'System information'), jsonView(data)));
}
let renderVersion = 0;
async function render() {
  const version = ++renderVersion;
  const id = (location.hash.slice(1).split('?')[0] || 'dashboard');
  const route = labels[id] ? id : 'dashboard';
  const nav = $('#nav'); nav.replaceChildren(...Object.keys(labels).flatMap((key, i) => [i === 8 || i === 13 ? el('div', { class: 'nav-separator' }) : null, el('a', { href: '#' + key, class: route === key ? 'active' : '', 'aria-current': route === key ? 'page' : null }, [el('span', { class: 'nav-icon', text: icons[i] }), labels[key][language === 'tr' ? 0 : 1]])]).filter(Boolean));
  $('#crumb').textContent = labels[route][language === 'tr' ? 0 : 1]; $('#language-button').textContent = language === 'tr' ? 'EN' : 'TR';
  const main = $('#main'); main.replaceChildren(el('div', { class: 'loader', text: tr('Hafıza okunuyor…', 'Reading memory…') }));
  const staged = el('div');
  try {
    const renderers = { dashboard, memories: m => memoryPage(m, 'memories'), profile: m => memoryPage(m, 'profile', { subject: 'user' }), search: m => memoryPage(m, 'search'), projects, timeline, graph, learning, skills, connections, capture, comparison, benchmarks, privacy, backups, diagnostics };
    await renderers[route](staged);
    if (version === renderVersion) main.replaceChildren(...staged.childNodes);
    if (version === renderVersion) $('#footer-health').textContent = tr('v0.1 beta · Çevrimiçi', 'v0.1 beta · Online');
  } catch (error) {
    if (version === renderVersion) { $('#footer-health').textContent = tr('Bağlantı denetlenmeli', 'Check connection'); main.replaceChildren(heading(route, ''), el('p', { class: 'error', text: error.message }), button(tr('Yeniden dene', 'Retry'), render)); }
  }
}
async function start() {
  syncSidebar();
  document.body.classList.toggle('dark', localStorage.getItem('brain-theme') === 'dark');
  try { await api('status'); $('#login').hidden = true; $('#shell').hidden = false; await render(); }
  catch (error) { $('#login').hidden = false; $('#shell').hidden = true; if (error.status !== 403) $('#login-error').textContent = error.message; }
}
$('#login-form').addEventListener('submit', async event => { event.preventDefault(); const submit = event.submitter; if (submit) submit.disabled = true; try { await api('login', { token: $('#login-key').value }); $('#login-key').value = ''; $('#login-error').textContent = ''; await start(); } catch (error) { $('#login-error').textContent = error.message; } finally { if (submit) submit.disabled = false; } });
$('#theme-button').addEventListener('click', () => { document.body.classList.toggle('dark'); localStorage.setItem('brain-theme', document.body.classList.contains('dark') ? 'dark' : 'light'); });
$('#language-button').addEventListener('click', async () => { language = language === 'tr' ? 'en' : 'tr'; localStorage.setItem('brain-language', language); document.documentElement.lang = language; await render(); });
function syncSidebar() {
  const closed = window.matchMedia('(max-width: 760px)').matches && !$('.sidebar').classList.contains('open');
  $('.sidebar').inert = closed; $('.sidebar').setAttribute('aria-hidden', String(closed));
  $('#menu-button').setAttribute('aria-expanded', String(!closed));
}
$('#menu-button').addEventListener('click', () => { $('.sidebar').classList.toggle('open'); syncSidebar(); });
$('#logout-button').addEventListener('click', async () => { try { await api('logout', {}); $('#shell').hidden = true; $('#login-error').textContent = ''; await start(); } catch (error) { toast(error.message, true); } });
window.addEventListener('resize', syncSidebar);
window.addEventListener('hashchange', () => { $('.sidebar').classList.remove('open'); syncSidebar(); render(); });
await start();
