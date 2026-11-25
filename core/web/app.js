"use strict";
/* ============ utilities ============ */
const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const debounce = (fn, ms) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms) } };
const ICONS = {
  home: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
  users: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/>',
  key: '<path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.78 7.78 5.5 5.5 0 0 1 7.78-7.78zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>',
  building: '<rect x="4" y="2" width="16" height="20" rx="2"/><line x1="9" y1="22" x2="9" y2="18"/><line x1="15" y1="22" x2="15" y2="18"/><line x1="8" y1="6" x2="8.01" y2="6"/><line x1="12" y1="6" x2="12.01" y2="6"/><line x1="16" y1="6" x2="16.01" y2="6"/><line x1="8" y1="10" x2="8.01" y2="10"/><line x1="12" y1="10" x2="12.01" y2="10"/><line x1="16" y1="10" x2="16.01" y2="10"/><line x1="8" y1="14" x2="8.01" y2="14"/><line x1="12" y1="14" x2="12.01" y2="14"/><line x1="16" y1="14" x2="16.01" y2="14"/>',
  list: '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
  db: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>',
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  warn: '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  check: '<polyline points="20 6 9 17 4 12"/>', x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  sun: '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
  moon: '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
  globe: '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
  user: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
  sort: '<path d="M3 6h11M3 12h8M3 18h5"/><path d="M18 5v14m0 0-3-3m3 3 3-3"/>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
  refresh: '<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>',
  chev: '<polyline points="9 18 15 12 9 6"/>',
  box: '<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
  folder: '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
  swap: '<polyline points="17 1 21 5 17 9"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><polyline points="7 23 3 19 7 15"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/>',
  idcard: '<rect x="2" y="4" width="20" height="16" rx="2"/><circle cx="8" cy="11" r="2.5"/><path d="M4.5 17a3.5 3.5 0 0 1 7 0"/><line x1="14" y1="9" x2="19" y2="9"/><line x1="14" y1="13" x2="19" y2="13"/>',
  file: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
  image: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
  printer: '<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>',
  sheet: '<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/>',
  chart: '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
  tool: '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
  inbox: '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  bell: '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/>',
  qr: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><line x1="14" y1="14" x2="14" y2="14.01"/><line x1="17" y1="17" x2="21" y2="17"/><line x1="21" y1="14" x2="21" y2="21"/><line x1="14" y1="21" x2="17" y2="21"/>',
  mail: '<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>'
};
const ic = (n, sz) => `<svg class="i" viewBox="0 0 24 24"${sz ? ` style="font-size:${sz}px"` : ''}>${ICONS[n] || ''}</svg>`;

/* ============ i18n ============ */
let DICT = { en: {}, ar: {} }, LANG = 'en';
function t(key, vars) {
  let s = DICT[LANG][key] ?? DICT.en[key] ?? key;
  if (vars) for (const k in vars) s = s.split('{' + k + '}').join(vars[k]);
  return s;
}
const errText = e => (e && e.code && (DICT[LANG]['err.' + e.code] || DICT.en['err.' + e.code])) ? t('err.' + e.code, e) : (e && e.error) || t('err.generic');
const nameOf = (o, base = 'name') => (LANG === 'ar' ? (o[base + '_ar'] || o[base + '_en']) : (o[base + '_en'] || o[base + '_ar'])) || '';
const loc = () => LANG === 'ar' ? 'ar-u-nu-latn' : 'en-GB';
function fmtDate(iso, withTime) {
  if (!iso) return '—';
  const d = new Date(iso.length === 10 ? iso + 'T00:00:00Z' : iso);
  if (isNaN(d)) return iso;
  return d.toLocaleString(loc(), withTime ? { dateStyle: 'medium', timeStyle: 'short' } : { dateStyle: 'medium', timeZone: 'UTC' });
}
async function loadDicts() {
  const [en, ar] = await Promise.all(['en', 'ar'].map(l => fetch(`/static/i18n/${l}.json`).then(r => r.json())));
  DICT = { en, ar };
}

/* ============ api ============ */
let CSRF = null;
async function api(path, o = {}) {
  const opt = { method: o.method || 'GET', headers: {}, credentials: 'same-origin' };
  if (CSRF && opt.method !== 'GET') opt.headers['X-CSRF-Token'] = CSRF;
  if (o.body !== undefined) { opt.body = JSON.stringify(o.body); opt.headers['Content-Type'] = 'application/json'; }
  if (o.raw !== undefined) opt.body = o.raw;
  if (o.headers) Object.assign(opt.headers, o.headers);
  let res;
  try { res = await fetch(path, opt); } catch (e) { throw { code: 'network', error: 'Network error' }; }
  let data = {};
  try { data = await res.json(); } catch (e) { }
  if (!res.ok) {
    if (res.status === 401 && data.code === 'not_authenticated' && S.user) { S.user = null; CSRF = null; go('#/login'); }
    if (res.status === 402 && data.code === 'license_required' && S.user) { S.license = { state: data.state, locked: true }; if (!location.hash.startsWith('#/license')) go('#/license'); }
    throw Object.assign({ status: res.status }, data);
  }
  return data;
}

/* ============ state, theme, language ============ */
const S = { user: null, brand: null, license: null, page: null };
const has = p => !!(S.user && S.user.permissions.includes(p));
const canSee = perm => !perm || (Array.isArray(perm) ? perm.some(has) : has(perm));     // a menu item can need any one of several permissions
function applyTheme() {
  const pref = (S.user && S.user.theme) || localStorage.getItem('am_theme') || (S.brand && S.brand.default_theme) || 'light';
  const dark = pref === 'dark' || (pref === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  S.themePref = pref;
}
function applyLang() {
  LANG = (S.user && S.user.lang) || localStorage.getItem('am_lang') || (S.brand && S.brand.default_language) || 'en';
  document.documentElement.lang = LANG;
  document.documentElement.dir = LANG === 'ar' ? 'rtl' : 'ltr';
  document.title = appName();
}
function applyBrand() {
  const b = S.brand; if (!b) return;
  const r = document.documentElement.style;
  r.setProperty('--brand', b.primary_color); r.setProperty('--brand2', b.accent_color);
  const tc = document.querySelector('meta[name="theme-color"]'); if (tc && b.primary_color) tc.content = b.primary_color;   // phone status bar
}
const appName = () => S.brand ? (LANG === 'ar' ? S.brand.app_name_ar : S.brand.app_name_en) : 'Asset Manager';
const companyName = () => S.brand ? (LANG === 'ar' ? (S.brand.name_ar || S.brand.name_en) : (S.brand.name_en || S.brand.name_ar)) : '';
function logoHTML() {
  if (S.brand && S.brand.logo) return `<div class="logo"><img src="${esc(S.brand.logo)}" alt=""></div>`;
  return `<div class="logo">${esc((companyName() || appName() || 'A').trim().charAt(0).toUpperCase())}</div>`;
}
async function setLang(l) {
  localStorage.setItem('am_lang', l);
  if (S.user) { S.user.lang = l; api('/api/auth/prefs', { method: 'PUT', body: { lang: l, theme: S.themePref } }).catch(() => { }); }
  applyLang(); applyTheme(); render();
}
async function setTheme(th) {
  localStorage.setItem('am_theme', th);
  if (S.user) { S.user.theme = th; api('/api/auth/prefs', { method: 'PUT', body: { lang: LANG, theme: th } }).catch(() => { }); }
  applyTheme(); render();
}

/* ============ toasts & modals ============ */
function toast(title, msg, kind = 'ok') {
  const life = kind === 'err' ? 7000 : 4000;
  const el = document.createElement('div'); el.className = 'toast ' + (kind === 'err' ? 'err' : '');
  el.setAttribute('role', kind === 'err' ? 'alert' : 'status'); el.style.setProperty('--life', life + 'ms');
  el.innerHTML = `${ic(kind === 'err' ? 'warn' : 'check', 20)}<div><b>${esc(title)}</b>${msg ? `<span>${esc(msg)}</span>` : ''}</div>`;
  const bye = () => { el.classList.add('out'); setTimeout(() => el.remove(), 230); };
  el.onclick = bye;
  $('#toasts').appendChild(el); setTimeout(bye, life);
}
const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
/* numbers in summary cards count up once when the dashboard opens */
function countUp(root) {
  if (reducedMotion()) return;
  $$('.kpi .num', root).forEach(el => {
    const raw = el.textContent.trim();
    if (!/^\d{1,7}$/.test(raw) || +raw < 2) return;
    const end = +raw, t0 = performance.now(), dur = 650;
    const step = now => { const p = Math.min(1, (now - t0) / dur); el.textContent = Math.round(end * (1 - Math.pow(1 - p, 3))); if (p < 1) requestAnimationFrame(step); };
    el.textContent = '0'; requestAnimationFrame(step);
  });
}
const fail = (e, title) => toast(title || t('toast.failed'), errText(e), 'err');
function modal(html, cls = '') {
  const ov = document.createElement('div'); ov.className = 'ov'; ov.innerHTML = `<div class="md ${cls}" role="dialog" aria-modal="true">${html}</div>`;
  const close = () => { ov.remove(); document.removeEventListener('keydown', kd); };
  const kd = e => { if (e.key === 'Escape' && ov === $('#modal-root').lastElementChild) ov.close(); };   // topmost dialog only
  document.addEventListener('keydown', kd);
  ov.addEventListener('mousedown', e => { if (e.target === ov) ov.close(); });
  $('#modal-root').appendChild(ov); ov.close = close;
  const f = $('input,select,textarea', ov); if (f) f.focus();
  return ov;
}
function confirmBox(title, text, okLabel, danger = true) {
  return new Promise(res => {
    const m = modal(`<h2>${esc(title)}</h2><div class="sub">${esc(text)}</div><div class="foot"><button class="btn" id="c-no">${t('common.cancel')}</button><button class="btn ${danger ? 'dng' : 'pri'}" id="c-yes">${esc(okLabel)}</button></div>`, 'sm');
    $('#c-no', m).onclick = () => { m.close(); res(false); }; $('#c-yes', m).onclick = () => { m.close(); res(true); };
  });
}
function secretBox(title, sub, secret) {
  const m = modal(`<h2>${esc(title)}</h2><div class="sub">${esc(sub)}</div><div class="pw"><span class="mono" id="sec">${esc(secret)}</span><button class="btn sm" id="cp">${ic('copy', 15)}${t('common.copy')}</button></div><div class="foot"><button class="btn pri" id="ok">${t('common.done')}</button></div>`, 'sm');
  $('#cp', m).onclick = () => { navigator.clipboard && navigator.clipboard.writeText(secret).then(() => toast(t('common.copied'))); };
  $('#ok', m).onclick = () => m.close();
}
const field = (id, label, input, opts = {}) => `<div class="fld ${opts.full ? 'full' : ''}" data-f="${id}"><label for="f-${id}">${esc(label)}${opts.req ? '<span class="req">*</span>' : ''}</label>${input}${opts.hint ? `<div class="hint">${esc(opts.hint)}</div>` : ''}<div class="em"></div></div>`;
const inp = (id, v = '', a = '') => `<input id="f-${id}" name="${id}" value="${esc(v)}" ${a}>`;
function showErrors(root, e) {
  $$('.fld.err', root).forEach(f => { f.classList.remove('err'); $('.em', f).textContent = ''; });
  if (e && e.field) { const f = $(`[data-f="${CSS.escape(String(e.field))}"]`, root); if (f) { f.classList.add('err'); $('.em', f).textContent = errText(e); const i = $('input,select', f); i && i.focus(); return true; } }
  return false;
}
const go = h => { if (location.hash === h) render(); else location.hash = h; };
/* "Sort by" on lists. The choice is remembered per list in this browser (a convenience only). */
const sortPref = (k, def, allowed) => { try { const v = localStorage.getItem('am_sort_' + k); return v && allowed.includes(v) ? v : def; } catch (e) { return def; } };
const sortSave = (k, v) => { try { localStorage.setItem('am_sort_' + k, v); } catch (e) { } };
const sortSel = (id, opts, cur) => `<label class="sortsel" title="${esc(t('sort.by'))}">${ic('sort', 16)}<select class="sel" id="${id}" aria-label="${esc(t('sort.by'))}">${opts.map(o => `<option value="${o}" ${o === cur ? 'selected' : ''}>${esc(t('sort.' + o))}</option>`).join('')}</select></label>`;
const cmpText = (x, y) => String(x).localeCompare(String(y), LANG === 'ar' ? 'ar' : 'en', { numeric: true, sensitivity: 'base' });
const isBlank = v => v === null || v === undefined || v === '';
/* comparator on one value; blanks always go last, whatever the direction */
const by = (get, desc = false) => (a, b) => {
  const x = get(a), y = get(b), bx = isBlank(x), byy = isBlank(y);
  if (bx || byy) return bx === byy ? 0 : bx ? 1 : -1;
  const r = typeof x === 'number' && typeof y === 'number' ? x - y : cmpText(x, y);
  return desc ? -r : r;
};
const sortRows = (rows, cmp) => cmp ? rows.slice().sort(cmp) : rows;

/* ============ auth screens ============ */
function authTools() {
  return `<div class="tools"><button class="chip" id="t-lang" title="${t('common.language')}">${ic('globe', 17)}${LANG === 'ar' ? 'English' : 'العربية'}</button>
  <button class="chip" id="t-theme" title="${t('common.theme')}">${ic(document.documentElement.dataset.theme === 'dark' ? 'sun' : 'moon', 17)}</button></div>`;
}
function bindTools() {
  const l = $('#t-lang'); if (l) l.onclick = () => setLang(LANG === 'ar' ? 'en' : 'ar');
  const th = $('#t-theme'); if (th) th.onclick = () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
}
function renderLogin() {
  $('#root').innerHTML = `<div class="auth split">${authTools()}
  <div class="hero">${logoHTML()}<h1>${esc(companyName() || appName())}</h1><p>${esc(appName())}</p>
    <ul><li><span>${ic('box')}</span>${t('login.f1')}</li><li><span>${ic('printer')}</span>${t('login.f2')}</li><li><span>${ic('shield')}</span>${t('login.f3')}</li></ul></div>
  <div class="formside"><div class="box"><div class="head">${logoHTML()}<h1>${esc(companyName() || appName())}</h1><p>${esc(appName())}</p></div>
  <form class="card" id="lf" novalidate><h3>${t('login.title')}</h3><div class="sub">${t('login.sub')}</div><div class="grid" style="gap:14px">
  ${field('username', t('login.username'), inp('username', '', 'autocomplete="username" autocapitalize="off" dir="ltr"'))}
  ${field('password', t('login.password'), inp('password', '', 'type="password" autocomplete="current-password" dir="ltr"'))}
  <div id="lerr" class="banner bad" style="display:none;margin:0"></div>
  <button class="btn pri" type="submit" id="lbtn">${t('login.signin')}</button></div>
  ${S.brand.access_requests ? `<div class="authalt">${t('acc.no_account')} <a href="#/request-access">${t('acc.request_link')}</a></div>` : ''}</form></div></div></div>`;
  bindTools();
  $('#f-username').focus();
  $('#lf').onsubmit = async e => {
    e.preventDefault(); const b = $('#lbtn'); b.disabled = true; $('#lerr').style.display = 'none';
    try {
      const r = await api('/api/auth/login', { method: 'POST', body: { username: $('#f-username').value, password: $('#f-password').value } });
      CSRF = r.csrf; S.user = r.user; S.license = r.license;
      applyLang(); applyTheme();
      const next = S.next; S.next = null;
      go(S.user.is_super && S.license.locked ? '#/license' : (next && !S.user.must_change_password ? next : '#/dashboard'));
    } catch (err) {
      const box = $('#lerr'); box.style.display = 'flex'; box.innerHTML = `${ic('warn', 18)}<div>${esc(errText(err))}</div>`; b.disabled = false;
    }
  };
}
/* request access (public): a person without an account asks for one; an administrator approves it on the Users page */
function renderRequestAccess() {
  if (!S.brand.access_requests) return go('#/login');
  const ta = (id, a = '') => `<textarea id="f-${id}" class="txt" rows="3" maxlength="500" ${a}></textarea>`;
  const doms = S.brand.access_domains || [];
  $('#root').innerHTML = `<div class="auth">${authTools()}<div class="box wide"><div class="head">${logoHTML()}<h1>${t('acc.title')}</h1><p>${esc(t('acc.sub', { company: companyName() || appName() }))}</p></div>
  <form class="card" id="af" novalidate><div class="fg">
  ${field('full_name', t('users.full_name'), inp('full_name', '', 'autocomplete="name" maxlength="120"'), { req: true })}
  ${field('email', t('acc.work_email'), inp('email', '', `type="email" autocomplete="email" dir="ltr" maxlength="160"${doms.length ? ` placeholder="name@${esc(doms[0])}"` : ''}`), { req: true, hint: doms.length ? t('acc.email_hint_domains', { domains: doms.map(d => '@' + d).join(', ') }) : t('acc.email_hint') })}
  ${field('department', t('acc.department'), inp('department', '', 'maxlength="120"'))}
  ${field('job_title', t('acc.job_title'), inp('job_title', '', 'autocomplete="organization-title" maxlength="120"'))}
  ${field('phone', t('acc.phone'), inp('phone', '', 'type="tel" autocomplete="tel" dir="ltr" maxlength="40"'))}
  ${field('username', t('acc.username'), inp('username', '', 'dir="ltr" autocomplete="off" autocapitalize="off" maxlength="40"'), { hint: t('acc.username_hint') })}
  ${field('reason', t('acc.reason'), ta('reason'), { full: true, hint: t('acc.reason_hint') })}
  <div class="hp" aria-hidden="true"><label for="f-website">Website</label><input id="f-website" name="website" tabindex="-1" autocomplete="off"></div>
  <div class="full"><button class="btn pri" type="submit" id="abtn" style="width:100%">${t('acc.send')}</button></div>
  <div class="full authalt" style="margin:0">${t('acc.have_account')} <a href="#/login">${t('login.signin')}</a></div></div></form></div></div>`;
  bindTools();
  $('#f-full_name').focus();
  $('#af').onsubmit = async e => {
    e.preventDefault(); const f = $('#af'), b = $('#abtn');
    const body = { lang: LANG }; ['full_name', 'email', 'department', 'job_title', 'phone', 'username', 'reason', 'website'].forEach(k => body[k] = $('#f-' + k).value);
    b.disabled = true; showErrors(f, null);
    try {
      await api('/api/access-requests', { method: 'POST', body });
      $('#af').outerHTML = `<div class="card done-card" role="status">${ic('check', 40)}<h3>${t('acc.sent_title')}</h3><p>${esc(t('acc.sent_text', { email: body.email.trim() }))}</p><a class="btn pri" href="#/login">${t('acc.back')}</a></div>`;
    } catch (err) { b.disabled = false; if (!showErrors(f, err)) fail(err); }
  };
}
/* invitation link (public): #/invite?t=<secret>. The person chooses a password; the role was chosen by the administrator */
async function renderInvite() {
  const token = new URLSearchParams(location.hash.split('?')[1] || '').get('t') || '';
  const shell = inner => { $('#root').innerHTML = `<div class="auth">${authTools()}<div class="box">${inner}</div></div>`; bindTools(); };
  const dead = err => shell(`<div class="head">${logoHTML()}<h1>${esc(companyName() || appName())}</h1><p>${esc(appName())}</p></div>
    <div class="card done-card" role="alert">${ic('warn', 40)}<h3>${t('inv.dead_title')}</h3><p>${esc(errText(err))}</p><p class="mut">${t('inv.dead_text')}</p><a class="btn pri" href="#/login">${t('acc.back')}</a></div>`);
  shell(`<div class="skel">${t('common.loading')}</div>`);
  let inv;
  try { inv = await api('/api/invite/check', { method: 'POST', body: { token } }); } catch (err) { return dead(err); }
  const cname = (LANG === 'ar' ? (inv.company_ar || inv.company_en) : (inv.company_en || inv.company_ar)) || companyName() || appName();
  shell(`<div class="head">${logoHTML()}<h1>${esc(t('inv.welcome', { company: cname }))}</h1><p>${esc(t('inv.welcome_sub', { role: nameOf(inv, 'role_name') }))}</p></div>
  <form class="card" id="jf" novalidate><div class="grid" style="gap:14px">
  ${field('email', t('users.email'), inp('email', inv.email, 'type="email" dir="ltr" readonly'))}
  ${field('full_name', t('users.full_name'), inp('full_name', inv.full_name, 'autocomplete="name" maxlength="120"'), { req: true })}
  ${field('username', t('login.username'), inp('username', inv.suggested, `dir="ltr" autocomplete="username" autocapitalize="off" maxlength="40" ${inv.username ? 'readonly' : ''}`), { req: true, hint: inv.username ? t('inv.username_fixed') : t('users.username_hint') })}
  ${field('password', t('pw.new'), inp('password', '', 'type="password" autocomplete="new-password" dir="ltr"'), { req: true, hint: t('password.policy') })}
  ${field('password2', t('pw.confirm'), inp('password2', '', 'type="password" autocomplete="new-password" dir="ltr"'), { req: true })}
  <button class="btn pri" type="submit" id="jbtn">${t('inv.join')}</button></div></form>`);
  $('#f-password').focus();
  $('#jf').onsubmit = async e => {
    e.preventDefault(); const f = $('#jf'), b = $('#jbtn');
    if ($('#f-password').value !== $('#f-password2').value) { showErrors(f, { field: 'password2', code: 'password_mismatch' }); return; }
    const body = { token, full_name: $('#f-full_name').value, username: $('#f-username').value, password: $('#f-password').value };
    b.disabled = true; showErrors(f, null);
    try {
      const res = await api('/api/invite/accept', { method: 'POST', body });
      try {
        const r = await api('/api/auth/login', { method: 'POST', body: { username: res.username, password: body.password } });
        CSRF = r.csrf; S.user = r.user; S.license = r.license; applyLang(); applyTheme(); toast(t('inv.joined_toast'));
        history.replaceState(null, '', '#/dashboard'); render();
      } catch (le) { toast(t('inv.joined_toast')); history.replaceState(null, '', '#/login'); render(); }
    } catch (err) { b.disabled = false; if (['invite_invalid', 'invite_used', 'invite_expired'].includes(err.code)) return dead(err); if (!showErrors(f, err)) fail(err); }
  };
}
/* QR label opened on a phone by someone who is not signed in: a short, read-only summary of the asset.
   Prices, notes, documents, custom fields and personal data stay behind the sign-in. Can be switched off in Company settings. */
async function renderPublicAsset() {
  const tag = new URLSearchParams(location.hash.split('?')[1] || '').get('tag') || '';
  const back = location.hash;
  const shell = inner => { $('#root').innerHTML = `<div class="auth">${authTools()}<div class="box"><div class="head">${logoHTML()}<h1>${esc(companyName() || appName())}</h1><p>${esc(appName())}</p></div>${inner}</div></div>`; bindTools(); };
  const signin = `<button class="btn pri" id="ps-in" style="width:100%">${ic('lock', 16)}${t('pub.signin')}</button>`;
  const bindIn = () => { const b = $('#ps-in'); if (b) b.onclick = () => { S.next = back; go('#/login'); }; };
  shell(`<div class="skel">${t('common.loading')}</div>`);
  let a;
  try { a = await api('/api/public/asset?tag=' + encodeURIComponent(tag)); }
  catch (err) {
    if (err.code === 'public_scan_off') { S.next = back; return renderLogin(); }
    shell(`<div class="card done-card" role="alert">${ic('warn', 40)}<h3>${t(err.code === 'asset_not_found' ? 'scan.not_found' : 'err.generic')}</h3><p class="mono">${esc(tag)}</p>${err.code !== 'asset_not_found' ? `<p>${esc(errText(err))}</p>` : ''}${signin}</div>`);
    return bindIn();
  }
  const row = (k, v) => v ? `<div><dt>${esc(k)}</dt><dd>${v}</dd></div>` : '';
  const wr = a.warranty_until ? esc(fmtDate(a.warranty_until)) + (a.warranty_until < today() ? ` <span class="badge bad">${t('assets.warranty_expired')}</span>` : ` <span class="badge good">${t('pub.under_warranty')}</span>`) : '';
  const holder = nameOf(a, 'holder');
  shell(`<div class="card pubasset"><div style="display:flex;gap:12px;align-items:flex-start"><div style="flex:1;min-width:0"><div class="mono mut" style="font-size:13px">${esc(a.tag)}</div><h2 style="margin:2px 0 4px">${esc(a.name)}</h2><div class="mut">${esc(nameOf(a, 'cat'))}${a.brand || a.model ? ' · ' + esc([a.brand, a.model].filter(Boolean).join(' ')) : ''}</div></div>${stBadge(a.status)}</div>
    ${holder ? `<div class="holder" style="margin:14px 0 0"><div class="av">${esc(initials(holder))}</div><div style="flex:1"><small>${t('assets.held_by')}</small><b>${esc(holder)}</b>${a.dept_en || a.dept_ar ? `<small>${esc(nameOf(a, 'dept'))}</small>` : ''}${a.assigned_at ? `<small>${esc(t('asg.since', { d: fmtDate(a.assigned_at) }))}</small>` : ''}</div></div>` : ''}
    <dl class="infogrid" style="margin-top:14px">${row(t('assets.serial'), a.serial_no ? `<span class="mono">${esc(a.serial_no)}</span>` : '')}${row(t('assets.condition'), esc(t('cond.' + a.condition)))}${row(t('assets.location'), esc(a.location))}${row(t('assets.purchase_date'), a.purchase_date ? esc(fmtDate(a.purchase_date)) : '')}${row(t('assets.warranty'), wr)}</dl>
    <div style="margin-top:16px">${signin}<div class="hint" style="text-align:center;margin-top:8px">${t('pub.signin_hint')}</div></div></div>`);
  bindIn();
}
function renderSetup() {
  $('#root').innerHTML = `<div class="auth">${authTools()}<div class="box wide"><div class="head">${logoHTML()}<h1>${t('setup.title')}</h1><p>${t('setup.sub')}</p></div>
  <form class="card" id="sf" novalidate><div class="fg">
  ${field('setup_code', t('setup.code'), inp('setup_code', '', 'autocomplete="off" dir="ltr" class="mono"'), { full: true, req: true, hint: t('setup.code_hint') })}
  ${field('name_en', t('company.name_en'), inp('name_en', '', 'dir="ltr"'), { req: true })}
  ${field('name_ar', t('company.name_ar'), inp('name_ar', '', 'dir="rtl"'))}
  ${field('default_language', t('company.default_language'), `<select id="f-default_language"><option value="en">English</option><option value="ar">العربية</option></select>`)}
  <div></div>
  ${field('full_name', t('setup.admin_name'), inp('full_name'), { req: true })}
  ${field('username', t('login.username'), inp('username', '', 'dir="ltr" autocomplete="off"'), { req: true, hint: t('users.username_hint') })}
  ${field('email', t('users.email'), inp('email', '', 'type="email" dir="ltr"'))}
  ${field('access_allowed_domains', t('set.domains'), inp('access_allowed_domains', '', 'dir="ltr" autocomplete="off" autocapitalize="off" placeholder="mycompany.com"'), { hint: t('set.domains_hint') })}
  ${field('password', t('setup.password'), inp('password', '', 'type="password" autocomplete="new-password" dir="ltr"'), { req: true, hint: t('password.policy') })}
  ${field('password2', t('setup.password2'), inp('password2', '', 'type="password" autocomplete="new-password" dir="ltr"'), { req: true })}
  <div class="full"><button class="btn pri" type="submit" id="sbtn" style="width:100%">${t('setup.create')}</button></div></div></form></div></div>`;
  bindTools();
  $('#f-default_language').value = LANG;
  $('#f-default_language').onchange = e => setLang(e.target.value);
  $('#sf').onsubmit = async e => {
    e.preventDefault(); const f = $('#sf');
    if ($('#f-password').value !== $('#f-password2').value) { showErrors(f, { field: 'password2', code: 'password_mismatch' }); return; }
    const body = {}; ['setup_code', 'name_en', 'name_ar', 'default_language', 'full_name', 'username', 'email', 'access_allowed_domains', 'password'].forEach(k => body[k] = $('#f-' + k).value);
    $('#sbtn').disabled = true;
    try {
      await api('/api/setup', { method: 'POST', body });
      const r = await api('/api/auth/login', { method: 'POST', body: { username: body.username, password: body.password } });
      CSRF = r.csrf; S.user = r.user; S.license = r.license; S.brand = await api('/api/branding');
      localStorage.setItem('am_lang', body.default_language); applyBrand(); applyLang(); applyTheme(); toast(t('setup.done')); go(licOff() ? '#/dashboard' : '#/license');
    } catch (err) {
      $('#sbtn').disabled = false;
      if (!showErrors(f, err)) fail(err);
    }
  };
}
function renderForcedPassword() {
  $('#root').innerHTML = `<div class="auth">${authTools()}<div class="box"><div class="head">${logoHTML()}<h1>${t('pw.force_title')}</h1><p>${t('pw.force_sub')}</p></div>
  <form class="card" id="pf" novalidate><div class="grid" style="gap:14px">${passwordFields()}<button class="btn pri" type="submit" id="pbtn">${t('pw.change')}</button>
  <button class="btn" type="button" id="plogout">${ic('logout', 16)}${t('nav.logout')}</button></div></form></div></div>`;
  bindTools(); $('#plogout').onclick = logout;
  bindPasswordForm($('#pf'), () => { S.user.must_change_password = false; go('#/dashboard'); });
}
const passwordFields = () =>
  field('current', t('pw.current'), inp('current', '', 'type="password" autocomplete="current-password" dir="ltr"'), { req: true }) +
  field('new', t('pw.new'), inp('new', '', 'type="password" autocomplete="new-password" dir="ltr"'), { req: true, hint: t('password.policy') }) +
  field('new2', t('pw.confirm'), inp('new2', '', 'type="password" autocomplete="new-password" dir="ltr"'), { req: true });
function bindPasswordForm(form, done) {
  form.onsubmit = async e => {
    e.preventDefault();
    if ($('#f-new').value !== $('#f-new2').value) { showErrors(form, { field: 'new2', code: 'password_mismatch' }); return; }
    try {
      await api('/api/auth/password', { method: 'POST', body: { current: $('#f-current').value, new: $('#f-new').value } });
      toast(t('pw.changed')); form.reset(); done && done();
    } catch (err) { if (!showErrors(form, Object.assign({}, err, { field: err.field === 'password' ? 'new' : err.code === 'wrong_current_password' ? 'current' : err.field }))) fail(err); }
  };
}
async function logout() {
  try { await api('/api/auth/logout', { method: 'POST', body: {} }); } catch (e) { }
  S.user = null; CSRF = null; S.license = null; applyLang(); applyTheme(); go('#/login');
}

/* ============ shell & router ============ */
const NAV = [['dashboard', 'home', 'dashboard.view'], ['assets', 'box', 'assets.view'], ['assignments', 'swap', 'assets.view'], ['employees', 'idcard', 'employees.view'],
['maintenance', 'tool', 'maintenance.view'], ['requests', 'inbox', ['requests.create', 'requests.approve']],
['categories', 'folder', 'categories.manage'], ['reports', 'chart', 'reports.view'], ['users', 'users', 'users.view'], ['roles', 'shield', 'roles.view'], ['company', 'building', 'company.view'],
['license', 'key', 'license.view'], ['audit', 'list', 'audit.view'], ['backups', 'db', 'backup.view'], ['account', 'gear', null]];
const PAGES = { dashboard: pDashboard, assets: pAssets, assignments: pAssignments, employees: pEmployees, categories: pCategories, reports: pReports, maintenance: pMaintenance, requests: pRequests, users: pUsers, roles: pRoles, company: pCompany, license: pLicense, audit: pAudit, backups: pBackups, account: pAccount };
const curPage = () => { const p = location.hash.replace(/^#\//, '').split('?')[0]; return PAGES[p] ? p : (p === 'login' || p === 'setup' || p === '' ? 'dashboard' : 'dashboard'); };
const licOff = () => !!(S.license && S.license.disabled);          // AM_LICENSE=off: every licence screen and message is hidden
function licenseBanner() {
  const l = S.license; if (!l || l.disabled || !has('license.view')) return '';
  if (l.locked) return `<div class="banner bad">${ic('lock', 20)}<div class="grow"><b>${t('lic.banner_locked')}</b>${t('lic.state_' + l.state + '_hint')}</div><a class="btn sm" href="#/license">${t('lic.manage')}</a></div>`;
  if (l.state === 'grace') return `<div class="banner warn">${ic('warn', 20)}<div class="grow"><b>${t('lic.banner_grace')}</b>${t('lic.state_grace_hint')}</div><a class="btn sm" href="#/license">${t('lic.manage')}</a></div>`;
  if (l.days_left !== null && l.days_left <= 30) return `<div class="banner warn">${ic('warn', 20)}<div class="grow"><b>${t('lic.banner_soon', { n: l.days_left })}</b></div><a class="btn sm" href="#/license">${t('lic.manage')}</a></div>`;
  return '';
}
/* menu sections: a heading is shown only when at least one of its pages is visible to the user */
const NAV_GROUP = { assets: 'inventory', assignments: 'inventory', employees: 'inventory', categories: 'inventory', maintenance: 'operations', requests: 'operations',
  reports: 'insights', users: 'admin', roles: 'admin', company: 'admin', license: 'admin', audit: 'admin', backups: 'admin', account: 'me' };
const skeleton = () => `<div class="skwrap" aria-busy="true" aria-label="${esc(t('common.loading'))}"><div class="row">${'<div class="sk" style="height:132px"></div>'.repeat(4)}</div><div class="sk" style="height:340px"></div></div>`;
function renderShell(page) {
  const locked = S.license && S.license.locked;
  const order = ['dashboard', 'assets', 'assignments', 'employees', 'categories', 'maintenance', 'requests', 'reports', 'users', 'roles', 'company', 'license', 'audit', 'backups', 'account'];
  const items = NAV.filter(([k, , perm]) => canSee(perm) && !(k === 'license' && licOff()) && !(k === 'requests' && S.brand && S.brand.asset_requests === false) && (!locked || k === 'license' || k === 'account')).sort((a, b) => order.indexOf(a[0]) - order.indexOf(b[0]));
  let grp = null;
  const nav = items.map(([k, i]) => {
    const g = NAV_GROUP[k] || null, head = g !== grp && g ? (g === 'me' ? '<div class="grp sep"></div>' : `<div class="grp">${t('navg.' + g)}</div>`) : '';
    grp = g;
    return head + `<a href="#/${k}" class="${k === page ? 'on' : ''}" ${k === page ? 'aria-current="page"' : ''}>${ic(i)}<span>${t(k === 'account' ? 'nav.settings' : 'nav.' + k)}</span></a>`;
  }).join('');
  $('#root').innerHTML = `<div class="app"><aside class="side" id="side"><div class="brand">${logoHTML()}<div><b>${esc(companyName() || appName())}</b><span>${esc(appName())}</span></div></div>
  <nav class="nav" aria-label="${esc(appName())}">${nav}</nav>
  <a class="me" href="#/account" title="${esc(t('nav.settings'))}"><span class="av">${esc(initials(S.user.full_name))}</span><span class="who"><b>${esc(S.user.full_name)}</b><small>${esc(nameOf(S.user, 'role_name'))}</small></span></a>
  <div class="foot">${t('common.version')} ${esc(S.brand.version || '')}</div></aside><div class="navov" id="navov"></div>
  <main><div class="wrap"><div class="top" id="tophead"></div>${licenseBanner()}<div id="page">${skeleton()}</div></div></main></div>`;
  const app = $('.app');
  $('#navov').onclick = () => app.classList.remove('navopen');
  $$('#side .nav a').forEach(a => a.addEventListener('click', () => app.classList.remove('navopen')));
}
function pageHead(title, sub, right = '') {
  $('#tophead').innerHTML = `<button class="chip" id="t-menu" aria-label="${t('nav.menu')}" aria-controls="side">${ic('list', 17)}</button><div style="min-width:0"><h1>${esc(title)}</h1>${sub ? `<p>${esc(sub)}</p>` : ''}</div><div class="sp"></div>${right}
  ${S.installEvt ? `<button class="chip" id="t-install" title="${t('pwa.install')}">${ic('download', 17)}<span class="hide-sm">${t('pwa.install')}</span></button>` : ''}
  ${has('assets.view') ? `<button class="chip" id="t-scan" title="${t('scan.button')}" aria-label="${t('scan.button')}">${ic('qr', 17)}<span class="hide-sm">${t('scan.button')}</span></button>` : ''}
  <button class="chip" id="t-theme" title="${t('common.theme')}" aria-label="${t('common.theme')}">${ic(document.documentElement.dataset.theme === 'dark' ? 'sun' : 'moon', 17)}</button>
  <div class="menu" id="bellwrap"><button class="chip" id="t-bell" title="${t('alert.title')}" aria-label="${t('alert.title')}">${ic('bell', 17)}<span class="bdg" id="bellc" hidden></span></button></div>
`;
  $('#t-menu').onclick = () => $('.app').classList.toggle('navopen');
  $('#t-bell').onclick = openBell;
  $('#t-theme').onclick = () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark');
  const sc = $('#t-scan'); if (sc) sc.onclick = openScanner;
  const inst = $('#t-install'); if (inst) inst.onclick = installApp;
  if (S.alerts) { const c = $('#bellc'); c.textContent = S.alerts.total > 99 ? '99+' : S.alerts.total; c.hidden = !S.alerts.total; }
  refreshBell();
}
let renderSeq = 0;
async function render() {
  const seq = ++renderSeq;
  if (!S.brand) { $('#root').innerHTML = `<div class="skel">${t('common.loading')}</div>`; return; }
  const h = location.hash.replace(/^#\//, '').split('?')[0];
  if (S.brand.needs_setup) return renderSetup();
  if (!S.user && h === 'request-access') return renderRequestAccess();
  if (h === 'invite') { if (S.user) { api('/api/auth/logout', { method: 'POST', body: {} }).catch(() => { }); S.user = null; CSRF = null; } return renderInvite(); }   // someone else's link: never join while signed in as another account
  if (!S.user && h === 'scan') return renderPublicAsset();
  if (!S.user) { if (h && h !== 'login' && h !== 'setup') S.next = location.hash; return renderLogin(); }   // e.g. a scanned QR label
  if (S.user.must_change_password) return renderForcedPassword();
  if (h === 'login' || h === 'setup' || h === 'request-access' || h === '') { return go('#/dashboard'); }
  if (h === 'receipt' && !(S.license && S.license.locked)) return renderReceipt(seq);
  if (h === 'labels' && !(S.license && S.license.locked)) return renderLabels(seq);
  if (h === 'scan' && !(S.license && S.license.locked)) return openScanned();
  if (h === 'scanner' && !(S.license && S.license.locked)) { history.replaceState(null, '', '#/assets'); await render(); return openScanner(); }   // home-screen shortcut
  const page = curPage();
  const locked = S.license && S.license.locked;
  if (locked && page !== 'license' && page !== 'account') return go('#/license');
  if (page === 'license' && licOff()) return go('#/dashboard');
  if (page === 'requests' && S.brand && S.brand.asset_requests === false) return go('#/dashboard');
  if (!canSee(NAV.find(n => n[0] === page)[2])) { renderShell(page); pageHead(t('err.forbidden_title'), ''); $('#page').innerHTML = `<div class="card"><div class="empty">${ic('lock', 36)}<b>${t('err.forbidden_title')}</b>${t('err.forbidden_page')}</div></div>`; return; }
  renderShell(page);
  try { await PAGES[page]($('#page'), seq); } catch (e) { if (seq === renderSeq && $('#page')) $('#page').innerHTML = `<div class="banner bad">${ic('warn', 20)}<div class="grow">${esc(errText(e))}</div></div>`; }
}
window.addEventListener('hashchange', render);

/* ============ dashboard ============ */
async function pDashboard(el) {
  const d = await api('/api/dashboard');
  pageHead(t('dash.title'), t('dash.sub', { company: companyName() }));
  S.license = Object.assign(S.license || {}, { state: d.license.state, days_left: d.license.days_left, disabled: !!d.license.disabled });
  const lic = d.license, ok = lic.disabled || lic.state === 'valid' || lic.state === 'grace';
  const kpi = (icon, num, label, sub, cls = '') => `<div class="card kpi ${cls}"><div class="ico">${ic(icon)}</div><div class="num ${String(num).length > 6 ? 'sm' : ''}">${num}</div><div class="lbl">${label}</div><div class="d">${sub}</div></div>`;
  const steps = [[ok, t('dash.step_license'), '#/license', has('license.view') && !lic.disabled], [!!S.brand.logo, t('dash.step_brand'), '#/company', has('company.view')], [d.users.total > 1, t('dash.step_users'), '#/users', has('users.view')],
  [!!d.last_backup, t('dash.step_backup'), '#/backups', has('backup.view')]];
  const A = d.assets;
  if (A) steps.push([A.categories > 0, t('dash.step_category'), '#/categories', has('categories.manage')], [A.employees > 0, t('dash.step_employee'), '#/employees', has('employees.manage')],
    [A.total > 0, t('dash.step_asset'), '#/assets', has('assets.manage')]);
  el.innerHTML = `${A ? `<div class="grid g4" style="margin-bottom:18px">
  ${kpi('box', A.total, t('dash.assets'), t('dash.assets_sub', { n: A.categories }), 'main')}
  ${kpi('swap', A.by_status.assigned, t('dash.assigned'), A.overdue ? `<span style="color:var(--bad);font-weight:700">${esc(t('dash.overdue', { n: A.overdue }))}</span>` : esc(t('dash.none_overdue')))}
  ${kpi('check', A.by_status.in_stock, t('dash.in_stock'), esc(t('dash.maint', { n: A.by_status.maintenance })))}
  ${kpi('idcard', A.employees, t('dash.employees'), esc(t('dash.value', { v: money(A.value) })) + (A.warranty_soon ? ' · ' + esc(t('dash.warranty_soon', { n: A.warranty_soon })) : ''))}</div>
  <div class="grid g12" id="dcharts" style="margin-bottom:18px"></div>` : ''}
  <div class="grid g4">
  ${kpi('users', d.users.active, t('dash.active_users'), t('dash.of_total', { n: d.users.total }))}
  ${kpi('shield', d.roles, t('dash.roles'), t('dash.roles_sub'))}
  ${lic.disabled ? kpi('check', esc('v' + d.version), t('dash.app_version'), t('dash.no_user_limit'))
    : kpi('key', t('lic.state_' + lic.state), t('dash.license'), lic.expires_at ? t('dash.expires', { d: fmtDate(lic.expires_at) }) : t('dash.no_expiry'))}
  ${kpi('db', d.last_backup ? fmtDate(new Date(d.last_backup.ts * 1000).toISOString(), true) : '—', t('dash.last_backup'), t('dash.schema', { v: d.schema, app: d.version }), A ? '' : 'main')}</div>
  <div class="grid g12" style="margin-top:18px"><div class="card s7"><h3>${t('dash.recent')}</h3><div class="sub">${t('dash.recent_sub')}</div>${d.recent ? (d.recent.length ? `<div class="tscroll"><table class="tbl"><tbody>${d.recent.map(r => `<tr><td class="mono" style="white-space:nowrap">${esc(fmtDate(r.ts, true))}</td><td><b>${esc(r.username || '—')}</b></td><td>${esc(actionLabel(r.action))}</td></tr>`).join('')}</tbody></table></div>` : `<div class="empty">${t('common.none')}</div>`) : `<div class="empty">${t('dash.no_audit_perm')}</div>`}</div>
  <div class="card s5"><h3>${t('dash.getting_started')}</h3><div class="sub">${t('dash.getting_started_sub')}</div>${steps.map(([done, label, link, allowed]) => `<div class="chk"><div class="dotc ${done ? 'ok' : ''}">✓</div><div style="flex:1;${done ? 'color:var(--mut)' : 'font-weight:600'}">${esc(label)}</div>${!done && allowed ? `<a class="btn sm" href="${link}">${t('common.open')}</a>` : ''}</div>`).join('')}</div></div>`;
  S.dashAssets = A;
  countUp(el);
  const dc = $('#dcharts'); if (dc) dashCharts(dc).catch(e => { dc.innerHTML = `<div class="card s12 mut">${esc(errText(e))}</div>`; });
}
const actionLabel = a => (DICT[LANG]['act.' + a] || DICT.en['act.' + a]) || a;

/* ============ users ============ */
async function pUsers(el) {
  const manage = has('users.manage');
  pageHead(t('users.title'), t('users.sub'), manage ? `<button class="btn sm" id="addu">${ic('plus', 16)}${t('users.add')}</button><button class="btn pri sm" id="invu">${ic('mail', 16)}${t('inv.invite')}</button>` : '');
  const [ur, rr] = await Promise.all([api('/api/users'), api('/api/roles')]);
  const roles = rr.roles;
  const US = { name: by(u => u.full_name), username: by(u => u.username), role: by(u => nameOf(u, 'role_name')), last_login: by(u => u.last_login_at, true), newest: (a, b) => b.id - a.id };
  let usort = sortPref('users', 'name', Object.keys(US));
  el.innerHTML = `${manage ? '<div id="accq"></div><div id="invq"></div>' : ''}<div class="card"><div class="toolbar"><input class="inp" id="uq" style="max-width:340px" placeholder="${t('common.search')}">${sortSel('usort', Object.keys(US), usort)}<div class="sp"></div><span class="badge mut" id="ucount"></span></div><div id="utbl"></div></div>`;
  let list = ur.users;
  if (manage) { accessQueue($('#accq'), roles, () => reload()); inviteQueue($('#invq'), roles); }
  const draw = () => {
    const q = $('#uq').value.trim().toLowerCase();
    const rows = sortRows(list.filter(u => !q || (u.username + ' ' + u.full_name + ' ' + u.email).toLowerCase().includes(q)), US[usort]);
    $('#ucount').textContent = rows.length + ' / ' + list.length;
    $('#utbl').innerHTML = rows.length ? `<div class="tscroll"><table class="tbl"><thead><tr><th>${t('users.user')}</th><th>${t('users.role')}</th><th>${t('users.status')}</th><th>${t('users.last_login')}</th><th></th></tr></thead><tbody>${rows.map(u => `<tr>
      <td><b>${esc(u.full_name)}</b><div class="mono" style="color:var(--mut);font-size:12.5px">${esc(u.username)}${u.email ? ' · ' + esc(u.email) : ''}</div></td>
      <td><span class="badge info">${esc(nameOf(u, 'role_name'))}</span></td>
      <td>${u.locked ? `<span class="badge warn">${t('users.locked')}</span>` : u.is_active ? `<span class="badge good">${t('users.active')}</span>` : `<span class="badge bad">${t('users.disabled')}</span>`}</td>
      <td>${esc(u.last_login_at ? fmtDate(u.last_login_at, true) : t('users.never'))}</td>
      <td style="white-space:nowrap;text-align:end">${manage ? `<button class="ib" data-e="${u.id}" title="${t('common.edit')}">${ic('edit', 15)}</button> <button class="ib" data-r="${u.id}" title="${t('users.reset')}">${ic('refresh', 15)}</button> ${u.id !== S.user.id ? `<button class="ib ${u.is_active ? 'd' : ''}" data-a="${u.id}" title="${u.is_active ? t('users.deactivate') : t('users.activate')}">${ic(u.is_active ? 'lock' : 'check', 15)}</button>` : ''}` : ''}</td></tr>`).join('')}</tbody></table></div>` : `<div class="empty">${t('common.no_results')}</div>`;
    $$('[data-e]').forEach(b => b.onclick = () => userForm(list.find(u => u.id == b.dataset.e)));
    $$('[data-r]').forEach(b => b.onclick = async () => { const u = list.find(x => x.id == b.dataset.r); if (await confirmBox(t('users.reset_q', { n: u.full_name }), t('users.reset_text'), t('users.reset'), false)) { try { const r = await api(`/api/users/${u.id}/reset-password`, { method: 'POST', body: {} }); secretBox(t('users.temp_title'), t('users.temp_sub'), r.temp_password); } catch (e) { fail(e); } } });
    $$('[data-a]').forEach(b => b.onclick = async () => { const u = list.find(x => x.id == b.dataset.a), to = !u.is_active; if (to || await confirmBox(t('users.deactivate_q', { n: u.full_name }), t('users.deactivate_text'), t('users.deactivate'))) { try { await api(`/api/users/${u.id}/active`, { method: 'POST', body: { active: to } }); toast(to ? t('users.activated') : t('users.deactivated')); await reload(); } catch (e) { fail(e); } } });
  };
  const reload = async () => { list = (await api('/api/users')).users; draw(); };
  const userForm = u => {
    const edit = !!u, assignable = roles;
    const m = modal(`<h2>${edit ? t('users.edit') : t('users.add')}</h2><div class="sub">${edit ? esc(u.username) : t('users.add_sub')}</div><form id="uf" novalidate><div class="fg">
      ${edit ? '' : field('username', t('login.username'), inp('username', '', 'dir="ltr" autocomplete="off"'), { req: true, hint: t('users.username_hint') })}
      ${field('full_name', t('users.full_name'), inp('full_name', edit ? u.full_name : ''), { req: true, full: edit })}
      ${field('email', t('users.email'), inp('email', edit ? u.email : '', 'type="email" dir="ltr"'))}
      ${field('role_id', t('users.role'), `<select id="f-role_id" ${edit && u.id === S.user.id ? 'disabled' : ''}>${assignable.map(r => `<option value="${r.id}" ${edit && r.id === u.role_id ? 'selected' : ''}>${esc(nameOf(r))}</option>`).join('')}</select>`, { req: true })}
      ${edit ? '' : field('password', t('users.password'), inp('password', '', 'type="text" autocomplete="off" dir="ltr"'), { hint: t('users.password_hint'), full: true })}</div>
      <div class="foot"><button type="button" class="btn" id="ucancel">${t('common.cancel')}</button><button class="btn pri" type="submit">${t('common.save')}</button></div></form>`);
    $('#ucancel', m).onclick = () => m.close();
    $('#uf', m).onsubmit = async ev => {
      ev.preventDefault(); const f = $('#uf', m);
      const body = { full_name: $('#f-full_name', m).value, email: $('#f-email', m).value, role_id: +$('#f-role_id', m).value };
      try {
        if (edit) { await api('/api/users/' + u.id, { method: 'PUT', body }); toast(t('toast.saved')); }
        else { body.username = $('#f-username', m).value; body.password = $('#f-password', m).value; const r = await api('/api/users', { method: 'POST', body }); toast(t('users.created')); if (r.temp_password) secretBox(t('users.temp_title'), t('users.temp_sub'), r.temp_password); }
        m.close(); await reload();
      } catch (err) { if (!showErrors(f, err)) fail(err); }
    };
  };
  const add = $('#addu'); if (add) add.onclick = () => userForm(null);
  const inv = $('#invu'); if (inv) inv.onclick = () => inviteForm(roles, () => inviteQueue($('#invq'), roles));
  $('#uq').addEventListener('input', debounce(draw, 120));
  $('#usort').onchange = () => { usort = $('#usort').value; sortSave('users', usort); draw(); };
  draw();
}

/* invitations (Users page, users.manage): the administrator picks the role, the person picks the password */
const INV_DAYS = [1, 3, 7, 14, 30];
function inviteForm(roles, done) {
  const pick = roles.filter(q => S.user.is_super || !q.all_permissions);
  const def = (pick.find(q => q.key === 'viewer') || pick[pick.length - 1] || {}).id;
  const m = modal(`<h2>${t('inv.title')}</h2><div class="sub">${t('inv.sub')}</div><form id="ivf" novalidate><div class="fg">
    ${field('email', t('users.email'), inp('email', '', 'type="email" dir="ltr" autocomplete="off" maxlength="160"'), { req: true })}
    ${field('full_name', t('users.full_name'), inp('full_name', '', 'maxlength="120" autocomplete="off"'), { req: true })}
    ${field('role_id', t('users.role'), `<select id="f-role_id">${pick.map(q => `<option value="${q.id}" ${q.id === def ? 'selected' : ''}>${esc(nameOf(q))}</option>`).join('')}</select>`, { req: true, hint: t('acc.role_hint') })}
    ${field('lang', t('inv.lang'), `<select id="f-lang"><option value="en">English</option><option value="ar">العربية</option></select>`)}
    ${field('days', t('inv.days'), `<select id="f-days">${INV_DAYS.map(n => `<option value="${n}" ${n === 7 ? 'selected' : ''}>${esc(t('inv.days_n', { n }))}</option>`).join('')}</select>`)}</div>
    <div class="foot"><button type="button" class="btn" id="ivc">${t('common.cancel')}</button><button class="btn pri" type="submit" id="ivs">${ic('mail', 15)}${t('inv.send')}</button></div></form>`);
  $('#f-lang', m).value = LANG;
  $('#ivc', m).onclick = () => m.close();
  $('#f-email', m).focus();
  $('#ivf', m).onsubmit = async ev => {
    ev.preventDefault(); const f = $('#ivf', m), b = $('#ivs', m);
    const body = { email: $('#f-email', m).value, full_name: $('#f-full_name', m).value, role_id: +$('#f-role_id', m).value,
      lang: $('#f-lang', m).value, days: +$('#f-days', m).value, origin: location.origin };
    b.disabled = true; showErrors(f, null);
    try { const r = await api('/api/invites', { method: 'POST', body }); m.close(); inviteResult(r, body.email.trim()); done && done(); }
    catch (err) { b.disabled = false; if (!showErrors(f, err)) fail(err); }
  };
}
/* after sending: say whether the e-mail went out, and always offer the link (it is shown only now) */
function inviteResult(r, email) {
  const why = r.mail_error ? (r.mail_error === 'email_off' ? t('inv.mail_off') : r.mail_error === 'no_public_url' ? t('inv.mail_no_url') : t('inv.mail_failed', { why: errText({ code: r.mail_error }) })) : '';
  const m = modal(`<h2>${r.emailed ? t('inv.sent_title') : t('inv.made_title')}</h2>
    <div class="banner ${r.emailed ? 'good' : 'warn'}" style="margin:6px 0 12px">${ic(r.emailed ? 'check' : 'warn', 18)}<div>${esc(r.emailed ? t('inv.sent_text', { email }) : why + ' ' + t('inv.copy_text'))}</div></div>
    <div class="pw" style="align-items:flex-start"><span class="mono" style="font-size:12px;letter-spacing:0;word-break:break-all;flex:1" dir="ltr">${esc(r.link)}</span><button class="btn sm" id="cp">${ic('copy', 15)}${t('common.copy')}</button></div>
    <div class="hint" style="margin-top:8px">${t('inv.link_hint')}</div>
    <div class="foot"><button class="btn pri" id="ok">${t('common.done')}</button></div>`, 'sm');
  $('#cp', m).onclick = () => { navigator.clipboard && navigator.clipboard.writeText(r.link).then(() => toast(t('common.copied'))); };
  $('#ok', m).onclick = () => m.close();
}
async function inviteQueue(box, roles, view = 'open') {
  let r;
  try { r = await api('/api/invites?view=' + view); } catch (e) { box.innerHTML = ''; return; }
  if (view === 'open' && !r.invites.length) { box.innerHTML = ''; return; }
  const st = x => x.status === 'pending' ? `<span class="badge warn">${t('inv.s_pending')}</span>` : x.status === 'expired' ? `<span class="badge bad">${t('inv.s_expired')}</span>` : `<span class="badge good">${t('inv.s_accepted')}</span>`;
  const when = x => x.status === 'accepted' ? t('inv.joined', { u: x.account || '—', d: fmtDate(x.accepted_at, true) })
    : t(x.status === 'expired' ? 'inv.expired_on' : 'inv.expires', { d: fmtDate(x.expires_at, true) }) + ' · ' + (x.sent_at ? t('inv.emailed', { d: fmtDate(x.sent_at, true) }) : t('inv.not_emailed'));
  box.innerHTML = `<div class="card acccard"><div class="cardhead" style="display:flex;gap:10px;align-items:flex-start;flex-wrap:wrap"><div style="flex:1;min-width:200px"><h3>${ic('mail', 17)} ${t(view === 'open' ? 'inv.q_title' : 'inv.history')}</h3><div class="sub">${t(view === 'open' ? 'inv.q_sub' : 'inv.history_sub')}</div></div>
    <button class="btn sm" id="inv-view">${view === 'open' ? t('inv.history') : t('inv.show_open')}</button></div>
    ${r.invites.length ? `<div class="acclist">${r.invites.map(x => `<div class="accitem">
      <div class="accmain"><b>${esc(x.full_name)}</b> ${st(x)} <span class="badge info">${esc(nameOf(x, 'role_name'))}</span><div class="mono accsub">${esc(x.email)}${x.username ? ' · ' + esc(x.username) : ''}</div>
      <div class="accsub">${esc(t('inv.by', { by: x.invited_by || '—', d: fmtDate(x.created_at, true) }))} · ${esc(when(x))}</div></div>
      ${x.status !== 'accepted' ? `<div class="accbtns"><button class="btn sm" data-rs="${x.id}">${ic('refresh', 15)}${t('inv.resend')}</button><button class="btn sm" data-rv="${x.id}">${ic('x', 15)}${t('inv.cancel')}</button></div>` : ''}</div>`).join('')}</div>` : `<div class="empty">${t('common.none')}</div>`}</div>`;
  const again = () => inviteQueue(box, roles, view);
  $('#inv-view', box).onclick = () => inviteQueue(box, roles, view === 'open' ? 'all' : 'open');
  $$('[data-rs]', box).forEach(b => b.onclick = async () => {
    const x = r.invites.find(q => q.id == b.dataset.rs);
    if (!await confirmBox(t('inv.resend_q', { n: x.full_name }), t('inv.resend_text'), t('inv.resend'), false)) return;
    try { const res = await api(`/api/invites/${x.id}/resend`, { method: 'POST', body: { origin: location.origin, days: 7 } }); inviteResult(res, x.email); again(); } catch (e) { fail(e); }
  });
  $$('[data-rv]', box).forEach(b => b.onclick = async () => {
    const x = r.invites.find(q => q.id == b.dataset.rv);
    if (!await confirmBox(t('inv.cancel_q', { n: x.full_name }), t('inv.cancel_text'), t('inv.cancel'))) return;
    try { await api(`/api/invites/${x.id}/revoke`, { method: 'POST', body: {} }); toast(t('inv.cancelled')); again(); } catch (e) { fail(e); }
  });
}

/* access requests waiting for a decision (Users page, users.manage) */
async function accessQueue(box, roles, onApproved, view = 'pending') {
  let r;
  try { r = await api('/api/access-requests?status=' + view); } catch (e) { box.innerHTML = ''; return; }
  if (view === 'pending' && !r.requests.length) {
    box.innerHTML = r.pending ? '' : `<div class="accbar">${ic('inbox', 16)}<span>${t('acc.q_empty')}</span><div class="sp"></div><button class="btn sm" id="acc-hist">${t('acc.history')}</button></div>`;
    const hb = $('#acc-hist', box); if (hb) hb.onclick = () => accessQueue(box, roles, onApproved, 'all');
    return;
  }
  const st = x => x.status === 'pending' ? `<span class="badge warn">${t('acc.s_pending')}</span>` : x.status === 'approved' ? `<span class="badge good">${t('acc.s_approved')}</span>` : `<span class="badge bad">${t('acc.s_rejected')}</span>`;
  const meta = x => [x.job_title, x.department].filter(Boolean).map(esc).join(' · ');
  box.innerHTML = `<div class="card acccard"><div class="cardhead" style="display:flex;gap:10px;align-items:flex-start;flex-wrap:wrap"><div style="flex:1;min-width:200px"><h3>${ic('inbox', 17)} ${t(view === 'pending' ? 'acc.q_title' : 'acc.history')}${view === 'pending' ? ` <span class="badge warn">${r.pending}</span>` : ''}</h3><div class="sub">${t(view === 'pending' ? 'acc.q_sub' : 'acc.history_sub')}</div></div>
    <button class="btn sm" id="acc-view">${view === 'pending' ? t('acc.history') : t('acc.show_pending')}</button></div>
    ${r.requests.length ? `<div class="acclist">${r.requests.map(x => `<div class="accitem">
      <div class="accmain"><b>${esc(x.full_name)}</b> ${view !== 'pending' ? st(x) : ''}<div class="mono accsub">${esc(x.email)}${x.phone ? ' · ' + esc(x.phone) : ''}</div>
      ${meta(x) ? `<div class="accsub">${meta(x)}</div>` : ''}${x.reason ? `<div class="accreason">${esc(x.reason)}</div>` : ''}
      <div class="accsub">${esc(fmtDate(x.created_at, true))}${x.status === 'approved' && x.account ? ' · ' + esc(t('acc.account_made', { u: x.account, by: x.decided_by_name || '—' })) : ''}${x.status === 'rejected' ? ' · ' + esc(t('acc.rejected_by', { by: x.decided_by_name || '—' })) + (x.decision_note ? ' — ' + esc(x.decision_note) : '') : ''}</div></div>
      ${x.status === 'pending' ? `<div class="accbtns"><button class="btn sm pri" data-ok="${x.id}">${ic('check', 15)}${t('acc.approve')}</button><button class="btn sm" data-no="${x.id}">${ic('x', 15)}${t('acc.reject')}</button></div>` : ''}</div>`).join('')}</div>` : `<div class="empty">${t('common.none')}</div>`}</div>`;
  $('#acc-view', box).onclick = () => accessQueue(box, roles, onApproved, view === 'pending' ? 'all' : 'pending');
  const refresh = () => { accessQueue(box, roles, onApproved, view); refreshBell(); };
  $$('[data-ok]', box).forEach(b => b.onclick = () => {
    const x = r.requests.find(q => q.id == b.dataset.ok);
    const def = (roles.find(q => q.key === 'viewer') || roles[roles.length - 1] || {}).id;
    const m = modal(`<h2>${t('acc.approve_title', { n: x.full_name })}</h2><div class="sub">${t('acc.approve_sub')}</div><form id="apf" novalidate><div class="fg">
      ${field('username', t('login.username'), inp('username', x.username_taken ? '' : x.username, 'dir="ltr" autocomplete="off" autocapitalize="off"'), { req: true, hint: x.username_taken ? t('acc.username_taken', { u: x.username }) : t('users.username_hint') })}
      ${field('role_id', t('users.role'), `<select id="f-role_id">${roles.filter(q => !q.all_permissions).map(q => `<option value="${q.id}" ${q.id === def ? 'selected' : ''}>${esc(nameOf(q))}</option>`).join('')}</select>`, { req: true, hint: t('acc.role_hint') })}
      ${field('full_name', t('users.full_name'), inp('full_name', x.full_name), { req: true })}
      ${field('email', t('users.email'), inp('email', x.email, 'type="email" dir="ltr"'))}
      <div class="fld full"><label class="cb"><input type="checkbox" id="f-notify" checked> ${ic('mail', 16)} ${t('acc.notify_ok')}</label><div class="hint">${t('acc.notify_hint')}</div></div></div>
      <div class="foot"><button type="button" class="btn" id="apc">${t('common.cancel')}</button><button class="btn pri" type="submit">${ic('check', 15)}${t('acc.create_account')}</button></div></form>`);
    $('#apc', m).onclick = () => m.close();
    $('#apf', m).onsubmit = async ev => {
      ev.preventDefault(); const f = $('#apf', m);
      const body = { username: $('#f-username', m).value, role_id: +$('#f-role_id', m).value, full_name: $('#f-full_name', m).value, email: $('#f-email', m).value, notify: $('#f-notify', m).checked };
      try {
        const res = await api(`/api/access-requests/${x.id}/approve`, { method: 'POST', body });
        m.close(); toast(t('acc.approved_toast', { u: res.username }));
        if (res.temp_password) secretBox(t('users.temp_title'), res.emailed ? t('acc.temp_emailed', { email: body.email }) : t('acc.temp_give'), res.temp_password);
        refresh(); onApproved && onApproved();
      } catch (err) { if (!showErrors(f, err)) fail(err); }
    };
  });
  $$('[data-no]', box).forEach(b => b.onclick = () => {
    const x = r.requests.find(q => q.id == b.dataset.no);
    const m = modal(`<h2>${t('acc.reject_title', { n: x.full_name })}</h2><div class="sub">${t('acc.reject_sub')}</div><form id="rjf" novalidate><div class="fg">
      ${field('note', t('acc.reject_note'), inp('note', '', 'maxlength="300"'), { full: true, hint: t('acc.reject_note_hint') })}
      <div class="fld full"><label class="cb"><input type="checkbox" id="f-notify" checked> ${ic('mail', 16)} ${t('acc.notify_no')}</label></div></div>
      <div class="foot"><button type="button" class="btn" id="rjc">${t('common.cancel')}</button><button class="btn dng" type="submit">${t('acc.reject')}</button></div></form>`, 'sm');
    $('#rjc', m).onclick = () => m.close();
    $('#rjf', m).onsubmit = async ev => {
      ev.preventDefault();
      try { await api(`/api/access-requests/${x.id}/reject`, { method: 'POST', body: { note: $('#f-note', m).value, notify: $('#f-notify', m).checked } }); m.close(); toast(t('acc.rejected_toast')); refresh(); }
      catch (err) { if (!showErrors($('#rjf', m), err)) fail(err); }
    };
  });
}

/* ============ roles ============ */
async function pRoles(el) {
  const manage = has('roles.manage');
  pageHead(t('roles.title'), t('roles.sub'), manage ? `<button class="btn pri sm" id="addr">${ic('plus', 16)}${t('roles.add')}</button>` : '');
  const [rr, pr] = await Promise.all([api('/api/roles'), api('/api/permissions')]);
  let roles = rr.roles, sel = roles.find(r => r.id === (pRoles.sel || 0)) || roles[0];
  const mine = new Set(S.user.permissions), sup = S.user.is_super;
  el.innerHTML = `<div class="grid g12"><div class="card s4"><h3>${t('roles.list')}</h3><div class="sub">${t('roles.list_sub')}</div><div class="rolelist" id="rl"></div></div><div class="card s8" id="re"></div></div>`;
  const drawList = () => { $('#rl').innerHTML = roles.map(r => `<div class="role ${sel && r.id === sel.id ? 'on' : ''}" data-id="${r.id}">${ic(r.all_permissions ? 'key' : 'shield', 20)}<div style="flex:1"><b>${esc(nameOf(r))}</b><small>${r.users} ${t('roles.users')}${r.is_system ? ' · ' + t('roles.builtin') : ''}</small></div></div>`).join(''); $$('.role', el).forEach(d => d.onclick = () => { sel = roles.find(r => r.id == d.dataset.id); pRoles.sel = sel.id; drawList(); drawEditor(); }); };
  const drawEditor = () => {
    const r = sel; if (!r) return;
    const locked = r.all_permissions || (r.key === 'company_admin' && !sup) || (r.id === S.user.role_id && !sup) || !manage;
    const reason = r.all_permissions ? t('roles.locked_super') : (r.key === 'company_admin' && !sup) ? t('roles.locked_admin') : (r.id === S.user.role_id && !sup) ? t('roles.locked_own') : !manage ? t('roles.locked_view') : '';
    const have = new Set(r.permissions);
    $('#re').innerHTML = `<div class="cardhead" style="display:flex;gap:12px;align-items:flex-start"><div style="flex:1"><h3>${esc(nameOf(r))}</h3><div class="sub" style="margin-bottom:6px">${esc(r.description || '')}</div></div>${r.is_system ? `<span class="badge info">${t('roles.builtin')}</span>` : `<span class="badge mut">${t('roles.custom')}</span>`}</div>
    ${reason ? `<div class="banner warn" style="margin-top:6px">${ic('lock', 18)}<div class="grow">${esc(reason)}</div></div>` : ''}
    ${!r.is_system && !locked ? `<div class="fg" style="margin-bottom:12px">${field('name_en', t('roles.name_en'), inp('name_en', r.name_en, 'dir="ltr"'), { req: true })}${field('name_ar', t('roles.name_ar'), inp('name_ar', r.name_ar, 'dir="rtl"'))}${field('description', t('roles.desc'), inp('description', r.description), { full: true })}</div>` : ''}
    ${Object.entries(pr.modules).map(([mod, codes]) => `<h3 style="margin:18px 0 8px;font-size:13px;color:var(--mut);text-transform:uppercase;letter-spacing:.5px">${t('mod.' + mod)}</h3><div class="perm-grid">${codes.map(c => { const can = r.all_permissions ? true : (sup || (mine.has(c) && !pr.super_only.includes(c))); const dis = locked || !can; return `<label class="perm ${dis ? 'off' : ''}"><input type="checkbox" data-p="${c}" ${(r.all_permissions || have.has(c)) ? 'checked' : ''} ${dis ? 'disabled' : ''}><span>${t('perm.' + c)}</span>${pr.super_only.includes(c) ? ic('lock', 13) : ''}</label>`; }).join('')}</div>`).join('')}
    ${!locked ? `<div class="toolbar" style="margin-top:20px;margin-bottom:0"><button class="btn pri" id="rsave">${t('common.save')}</button>${!r.is_system ? `<button class="btn dng" id="rdel" ${r.users ? 'disabled title="' + esc(t('err.role_in_use')) + '"' : ''}>${ic('trash', 16)}${t('common.delete')}</button>` : ''}</div>` : ''}`;
    const sv = $('#rsave');
    if (sv) sv.onclick = async () => {
      const perms = $$('[data-p]:checked', el).map(i => i.dataset.p);
      const body = { permissions: perms }; if (!r.is_system) { body.name_en = $('#f-name_en').value; body.name_ar = $('#f-name_ar').value; body.description = $('#f-description').value; }
      try { await api('/api/roles/' + r.id, { method: 'PUT', body }); toast(t('toast.saved')); await reload(); } catch (e) { if (!showErrors($('#re'), e)) fail(e); }
    };
    const dl = $('#rdel'); if (dl && !r.users) dl.onclick = async () => { if (await confirmBox(t('roles.delete_q', { n: nameOf(r) }), t('roles.delete_text'), t('common.delete'))) { try { await api('/api/roles/' + r.id, { method: 'DELETE' }); toast(t('toast.deleted')); pRoles.sel = 0; await reload(); } catch (e) { fail(e); } } };
  };
  const reload = async () => { roles = (await api('/api/roles')).roles; sel = roles.find(r => r.id === (pRoles.sel || (sel && sel.id))) || roles[0]; drawList(); drawEditor(); };
  const add = $('#addr'); if (add) add.onclick = () => {
    const m = modal(`<h2>${t('roles.add')}</h2><div class="sub">${t('roles.add_sub')}</div><form id="rf" novalidate><div class="fg">${field('name_en', t('roles.name_en'), inp('name_en', '', 'dir="ltr"'), { req: true })}${field('name_ar', t('roles.name_ar'), inp('name_ar', '', 'dir="rtl"'))}${field('description', t('roles.desc'), inp('description'), { full: true })}</div><div class="foot"><button type="button" class="btn" id="rc">${t('common.cancel')}</button><button class="btn pri" type="submit">${t('common.create')}</button></div></form>`);
    $('#rc', m).onclick = () => m.close();
    $('#rf', m).onsubmit = async ev => { ev.preventDefault(); try { const r = await api('/api/roles', { method: 'POST', body: { name_en: $('#f-name_en', m).value, name_ar: $('#f-name_ar', m).value, description: $('#f-description', m).value, permissions: ['dashboard.view'].filter(p => mine.has(p)) } }); m.close(); pRoles.sel = r.id; toast(t('roles.created')); await reload(); } catch (e) { if (!showErrors($('#rf', m), e)) fail(e); } };
  };
  drawList(); drawEditor();
}

/* ============ company & branding ============ */
async function pCompany(el) {
  const manage = has('company.manage');
  pageHead(t('company.title'), t('company.sub'));
  const c = await api('/api/company');
  el.innerHTML = `<div class="grid g12"><form class="card s8" id="cf" novalidate><h3>${t('company.identity')}</h3><div class="sub">${t('company.identity_sub')}</div><div class="fg">
    ${field('name_en', t('company.name_en'), inp('name_en', c.name_en, 'dir="ltr"' + (manage ? '' : ' disabled')), { req: true })}${field('name_ar', t('company.name_ar'), inp('name_ar', c.name_ar, 'dir="rtl"' + (manage ? '' : ' disabled')))}
    ${field('app_name_en', t('company.app_name_en'), inp('app_name_en', c.app_name_en, 'dir="ltr"' + (manage ? '' : ' disabled')), { hint: t('company.app_name_hint') })}${field('app_name_ar', t('company.app_name_ar'), inp('app_name_ar', c.app_name_ar, 'dir="rtl"' + (manage ? '' : ' disabled')))}
    ${field('primary_color', t('company.primary'), `<div class="colorrow"><input type="color" id="pc" value="${esc(c.primary_color)}" ${manage ? '' : 'disabled'}>${inp('primary_color', c.primary_color, 'dir="ltr" class="mono" maxlength="7"' + (manage ? '' : ' disabled'))}</div>`)}
    ${field('accent_color', t('company.accent'), `<div class="colorrow"><input type="color" id="ac" value="${esc(c.accent_color)}" ${manage ? '' : 'disabled'}>${inp('accent_color', c.accent_color, 'dir="ltr" class="mono" maxlength="7"' + (manage ? '' : ' disabled'))}</div>`)}
    ${field('default_language', t('company.default_language'), `<select id="f-default_language" ${manage ? '' : 'disabled'}><option value="en" ${c.default_language === 'en' ? 'selected' : ''}>English</option><option value="ar" ${c.default_language === 'ar' ? 'selected' : ''}>العربية</option></select>`)}
    ${field('default_theme', t('company.default_theme'), `<select id="f-default_theme" ${manage ? '' : 'disabled'}>${['light', 'dark', 'system'].map(x => `<option value="${x}" ${c.default_theme === x ? 'selected' : ''}>${t('theme.' + x)}</option>`).join('')}</select>`)}
    ${field('receipt_terms_en', t('company.terms_en'), `<textarea id="f-receipt_terms_en" class="txt" dir="ltr" placeholder="${esc(DICT.en['rcpt.terms_default_handover'] || '')}" ${manage ? '' : 'disabled'}>${esc(c.receipt_terms_en || '')}</textarea>`, { full: true, hint: t('company.terms_hint') })}
    ${field('receipt_terms_ar', t('company.terms_ar'), `<textarea id="f-receipt_terms_ar" class="txt" dir="rtl" placeholder="${esc(DICT.ar['rcpt.terms_default_handover'] || '')}" ${manage ? '' : 'disabled'}>${esc(c.receipt_terms_ar || '')}</textarea>`, { full: true })}
    </div>${manage ? `<div class="toolbar" style="margin:20px 0 0"><button class="btn pri" type="submit">${t('common.save')}</button></div>` : ''}</form>
  <div class="s4" style="display:flex;flex-direction:column;gap:18px"><div class="card"><h3>${t('company.logo')}</h3><div class="sub">${t('company.logo_sub')}</div><div class="preview" id="pv" style="margin-bottom:14px">${logoHTML()}<div><b>${esc(companyName())}</b><div style="opacity:.85;font-size:12.5px">${esc(appName())}</div></div></div>
  ${manage ? `<div class="toolbar" style="margin:0"><label class="btn sm" for="logo">${ic('upload', 15)}${t('company.upload')}</label><input type="file" id="logo" accept="image/png,image/jpeg,image/webp" hidden>${c.logo ? `<button class="btn sm dng" id="rmlogo">${ic('trash', 15)}${t('common.remove')}</button>` : ''}</div>` : ''}</div></div><div class="card s12" id="setcard"></div></div>`;
  settingsCard($('#setcard'));
  const sync = (a, b) => { $('#' + a).oninput = e => { $('#f-' + b).value = e.target.value.toUpperCase(); pv(); }; $('#f-' + b).oninput = e => { if (/^#[0-9a-fA-F]{6}$/.test(e.target.value)) { $('#' + a).value = e.target.value; pv(); } }; };
  const pv = () => { $('#pv').style.background = `linear-gradient(135deg,${$('#pc').value},${$('#ac').value})`; };
  sync('pc', 'primary_color'); sync('ac', 'accent_color'); pv();
  const refresh = async () => { S.brand = await api('/api/branding'); applyBrand(); applyLang(); applyTheme(); render(); };
  const logoOnly = async () => { S.brand = await api('/api/branding'); $$('.logo').forEach(l => { l.outerHTML = logoHTML(); }); const has = !!S.brand.logo, rm = $('#rmlogo'); if (rm && !has) rm.remove(); if (!rm && has) { $('#logo').insertAdjacentHTML('afterend', `<button class="btn sm dng" id="rmlogo">${ic('trash', 15)}${t('common.remove')}</button>`); $('#rmlogo').onclick = removeLogo; } };
  const removeLogo = async () => { try { await api('/api/company/logo', { method: 'DELETE' }); await logoOnly(); } catch (err) { fail(err); } };
  if (!manage) return;
  $('#cf').onsubmit = async e => {
    e.preventDefault(); const body = {}; ['name_en', 'name_ar', 'app_name_en', 'app_name_ar', 'primary_color', 'accent_color', 'default_language', 'default_theme', 'receipt_terms_en', 'receipt_terms_ar'].forEach(k => body[k] = $('#f-' + k).value);
    try { await api('/api/company', { method: 'PUT', body }); toast(t('toast.saved')); await refresh(); } catch (err) { if (!showErrors($('#cf'), err)) fail(err); }
  };
  $('#logo').onchange = async e => { const f = e.target.files[0]; if (!f) return; try { await api('/api/company/logo', { method: 'POST', raw: f }); toast(t('toast.saved')); await logoOnly(); } catch (err) { fail(err); } e.target.value = ''; };
  const rm = $('#rmlogo'); if (rm) rm.onclick = removeLogo;
}

/* ============ licence ============ */
async function pLicense(el) {
  const manage = has('license.manage');
  pageHead(t('lic.title'), t('lic.sub'));
  const [l, ev] = await Promise.all([api('/api/license'), api('/api/license/events')]);
  S.license = { state: l.state, locked: l.locked, days_left: l.days_left };
  const info = l.license, good = l.state === 'valid', warn = l.state === 'grace';
  const row = (k, v) => `<dt>${esc(k)}</dt><dd>${v}</dd>`;
  el.innerHTML = `<div class="grid g12"><div class="card s7"><div style="display:flex;gap:12px;align-items:center;margin-bottom:6px"><h3 style="margin:0;flex:1">${t('lic.status')}</h3><span class="badge ${good ? 'good' : warn ? 'warn' : 'bad'}">${t('lic.state_' + l.state)}</span></div>
  <div class="sub">${t('lic.state_' + l.state + '_hint')}</div>
  ${info ? `<dl style="display:grid;grid-template-columns:170px 1fr;gap:10px 14px;margin:0">${row(t('lic.company'), esc(info.company))}${row(t('lic.edition'), esc(info.edition || '—'))}${row(t('lic.issued'), esc(fmtDate(info.issued_at)))}${row(t('lic.expires'), info.expires_at ? esc(fmtDate(info.expires_at)) + (l.days_left !== null ? ` <span class="badge ${l.days_left < 0 ? 'bad' : l.days_left <= 30 ? 'warn' : 'mut'}">${l.days_left >= 0 ? t('lic.days_left', { n: l.days_left }) : t('lic.days_over', { n: -l.days_left })}</span>` : '') : t('lic.never'))}${l.grace_until ? row(t('lic.grace_until'), esc(fmtDate(l.grace_until))) : ''}${row(t('lic.users'), `${l.active_users} / ${info.max_users}`)}${row(t('lic.features'), info.features.length ? info.features.map(f => `<span class="badge info">${esc(f)}</span>`).join(' ') : '—')}${row(t('lic.id'), `<span class="mono">${esc(info.license_id)}</span>`)}${row(t('lic.activated'), esc(fmtDate(info.activated_at, true)))}</dl>` : `<div class="empty" style="padding:20px">${ic('key', 34)}<b>${t('lic.none')}</b>${t('lic.none_sub')}</div>`}</div>
  <div class="card s5"><h3>${t('lic.request')}</h3><div class="sub">${t('lic.request_sub')}</div><div class="pw" style="align-items:flex-start"><span class="mono" style="font-size:11.5px;letter-spacing:0;word-break:break-all;flex:1" id="rq">${esc(l.request_code)}</span><button class="btn sm" id="cprq">${ic('copy', 15)}${t('common.copy')}</button></div>
  <div class="hint" style="margin-top:8px;color:var(--mut);font-size:12.5px">${t('lic.deployment')}: <span class="mono">${esc(l.deployment_id)}</span></div></div>
  ${manage ? `<div class="card s12"><h3>${t('lic.activate')}</h3><div class="sub">${t('lic.activate_sub')}</div><div class="fld">${'<textarea id="lt" placeholder="{ ... }" spellcheck="false"></textarea>'}<div class="em" id="lerr"></div></div>
  <div class="toolbar" style="margin:14px 0 0"><button class="btn pri" id="lact">${ic('key', 16)}${t('lic.activate_btn')}</button><label class="btn" for="lfile">${ic('upload', 16)}${t('lic.choose_file')}</label><input type="file" id="lfile" accept=".json,.lic,.txt,application/json" hidden><div class="sp"></div><button class="btn sm" id="advbtn">${t('lic.advanced')}</button></div>
  <div id="adv" style="display:none;margin-top:16px"><div class="sub">${t('lic.revocations_sub')}</div><div class="fld"><textarea id="rt" spellcheck="false" style="min-height:90px"></textarea><div class="em" id="rerr"></div></div><button class="btn sm" id="ract" style="margin-top:10px">${t('lic.revocations_btn')}</button></div></div>` : ''}
  <div class="card s12"><h3>${t('lic.events')}</h3><div class="sub">${t('lic.events_sub')}</div>${ev.events.length ? `<div class="tscroll" style="max-height:320px"><table class="tbl"><tbody>${ev.events.map(e => `<tr><td class="mono" style="white-space:nowrap">${esc(fmtDate(e.ts, true))}</td><td><b>${esc(licEvent(e.event))}</b></td><td class="mono" style="font-size:12px;color:var(--mut)">${esc(Object.entries(e.detail).map(([k, v]) => k + '=' + v).join('  '))}</td></tr>`).join('')}</tbody></table></div>` : `<div class="empty">${t('common.none')}</div>`}</div></div>`;
  $('#cprq').onclick = () => navigator.clipboard && navigator.clipboard.writeText(l.request_code).then(() => toast(t('common.copied')));
  if (!manage) return;
  $('#lfile').onchange = e => { const f = e.target.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => { $('#lt').value = r.result; }; r.readAsText(f); };
  $('#advbtn').onclick = () => { const a = $('#adv'); a.style.display = a.style.display === 'none' ? 'block' : 'none'; };
  const send = (path, body, errEl, after) => async () => { errEl.textContent = ''; try { await api(path, { method: 'POST', body }); toast(t('lic.updated')); await after(); } catch (e) { errEl.textContent = errText(e); } };
  const refreshLic = async () => { const r = await api('/api/auth/me'); S.license = r.license; render(); };
  $('#lact').onclick = () => send('/api/license/activate', { license: $('#lt').value }, $('#lerr'), refreshLic)();
  $('#ract').onclick = () => send('/api/license/revocations', { list: $('#rt').value }, $('#rerr'), refreshLic)();
}
const licEvent = e => DICT[LANG]['lev.' + e] || DICT.en['lev.' + e] || e;

/* ============ audit ============ */
let AU = { page: 1, user: '', action: '', q: '' };
async function pAudit(el) {
  pageHead(t('audit.title'), t('audit.sub'), has('audit.verify') ? `<button class="btn sm" id="verify">${ic('shield', 15)}${t('audit.verify')}</button>` : '');
  el.innerHTML = `<div class="card"><div class="toolbar"><input class="inp" id="aq" style="max-width:260px" placeholder="${t('common.search')}" value="${esc(AU.q)}"><input class="inp" id="au" style="max-width:200px" placeholder="${t('audit.user')}" value="${esc(AU.user)}" dir="ltr"><input class="inp" id="aa" style="max-width:220px" placeholder="${t('audit.action_prefix')}" value="${esc(AU.action)}" dir="ltr"><div class="sp"></div><span class="badge mut" id="acount"></span></div><div id="atbl"><div class="skel">${t('common.loading')}</div></div><div class="toolbar" style="margin:14px 0 0"><button class="btn sm" id="prev">${ic('chev', 14)}</button><span id="pg" class="badge mut"></span><button class="btn sm" id="next">${ic('chev', 14)}</button></div></div>`;
  $('#prev').firstElementChild.style.transform = LANG === 'ar' ? '' : 'scaleX(-1)'; $('#next').firstElementChild.style.transform = LANG === 'ar' ? 'scaleX(-1)' : '';
  const load = async () => {
    AU.q = $('#aq').value; AU.user = $('#au').value; AU.action = $('#aa').value;
    const qs = new URLSearchParams({ page: AU.page, per_page: 25, q: AU.q, user: AU.user, action: AU.action });
    const r = await api('/api/audit?' + qs); const pages = Math.max(1, Math.ceil(r.total / r.per_page));
    $('#acount').textContent = r.total; $('#pg').textContent = `${r.page} / ${pages}`; $('#prev').disabled = r.page <= 1; $('#next').disabled = r.page >= pages;
    $('#atbl').innerHTML = r.entries.length ? `<div class="tscroll"><table class="tbl"><thead><tr><th>${t('audit.time')}</th><th>${t('audit.user')}</th><th>${t('audit.action')}</th><th>${t('audit.target')}</th><th>${t('audit.ip')}</th></tr></thead><tbody>${r.entries.map(e => `<tr><td class="mono" style="white-space:nowrap">${esc(fmtDate(e.ts, true))}</td><td><b>${esc(e.username || '—')}</b></td><td>${esc(actionLabel(e.action))}<div class="mono" style="font-size:11.5px;color:var(--mut)">${esc(e.action)}</div></td><td class="mono" style="font-size:12px">${esc(e.entity)}${e.entity_id ? ' #' + esc(e.entity_id) : ''}${Object.keys(e.detail).length ? `<div style="color:var(--mut);max-width:340px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(JSON.stringify(e.detail))}">${esc(JSON.stringify(e.detail))}</div>` : ''}</td><td class="mono" style="color:var(--mut)">${esc(e.ip)}</td></tr>`).join('')}</tbody></table></div>` : `<div class="empty">${t('common.no_results')}</div>`;
  };
  const reset = debounce(() => { AU.page = 1; load().catch(e => fail(e)); }, 250);
  ['aq', 'au', 'aa'].forEach(i => $('#' + i).addEventListener('input', reset));
  $('#prev').onclick = () => { AU.page--; load(); }; $('#next').onclick = () => { AU.page++; load(); };
  const v = $('#verify'); if (v) v.onclick = async () => { try { const r = await api('/api/audit/verify', { method: 'POST', body: {} }); r.ok ? toast(t('audit.verify_ok'), t('audit.verify_n', { n: r.checked })) : toast(t('audit.verify_bad'), t('audit.verify_at', { n: r.broken_at }), 'err'); } catch (e) { fail(e); } };
  await load();
}

/* ============ backups ============ */
const HEALTH_CLS = { ok: 'good', warn: 'warn', fail: 'bad' };
function healthValue(c) {
  switch (c.key) {
    case 'last_backup': return c.value === null ? t('hc.never') : t('hc.hours_ago', { n: nfmt(c.value) });
    case 'disk_free': case 'database_size': return fmtSize(c.value);
    case 'schema': return c.value + (c.state !== 'ok' ? ' ≠ ' + c.expected : '');
    case 'license': return t('lic.state_' + c.value);
    case 'audit_chain': return c.state === 'ok' ? t('hc.entries', { n: nfmt(c.value) }) : t('audit.verify_at', { n: c.broken_at });
    case 'database': return c.state === 'ok' ? t('hc.intact') : String(c.value);
    default: return nfmt(c.value);
  }
}
async function healthCard(box, deep) {
  box.style.opacity = box.innerHTML ? .55 : 1;               // keep the previous result while re-checking
  let h;
  try { h = await api('/api/system/health' + (deep ? '?deep=1' : '')); } catch (e) { box.innerHTML = `<div class="mut">${esc(errText(e))}</div>`; return; }
  box.style.opacity = 1;
  box.innerHTML = `<div class="vhead"><div><h3>${ic('shield', 16)} ${t('hc.title')} <span class="badge ${HEALTH_CLS[h.state]}">${t('hc.state_' + h.state)}</span></h3><div class="sub">${t('hc.sub')} · ${esc(fmtDate(h.checked_at, true))}</div></div><button class="btn sm" id="hc-deep">${t('hc.deep')}</button></div>
    <div class="tscroll"><table class="tbl"><tbody>${h.checks.map(c => `<tr><td style="width:34px"><span class="badge ${HEALTH_CLS[c.state]}" style="padding:2px 7px">${ic(c.state === 'ok' ? 'check' : 'warn', 12)}</span></td><td><b>${esc(t('hc.k_' + c.key))}</b>${c.state !== 'ok' ? `<div class="mut" style="font-size:12.5px">${esc(t('hc.fix_' + c.key))}</div>` : ''}</td><td class="num">${esc(healthValue(c))}</td></tr>`).join('')}</tbody></table></div>
    ${deep ? '' : `<div class="mut" style="font-size:12.5px;margin-top:8px">${t('hc.quick_note')}</div>`}`;
  $('#hc-deep', box).onclick = () => healthCard(box, true);
}
async function pBackups(el) {
  const manage = has('backup.manage');
  pageHead(t('bk.title'), t('bk.sub'), manage ? `<button class="btn pri sm" id="bk">${ic('db', 15)}${t('bk.now')}</button>` : '');
  const r = await api('/api/backups');
  el.innerHTML = `<div class="grid g12"><div class="card s8"><h3>${t('bk.list')}</h3><div class="sub">${t('bk.keep', { n: r.keep })}</div>${r.backups.length ? `<div class="tscroll"><table class="tbl"><thead><tr><th>${t('bk.file')}</th><th>${t('bk.contains')}</th><th>${t('rep.date')}</th><th class="num">${t('bk.size')}</th>${manage ? '<th></th>' : ''}</tr></thead><tbody>${r.backups.map(b => `<tr>
      <td class="mono" style="font-size:12.5px">${esc(b.name)}</td>
      <td>${b.kind === 'full' ? `<span class="badge good">${t('bk.kind_full')}</span>` : `<span class="badge mut" title="${esc(t('bk.kind_db_hint'))}">${t('bk.kind_db')}</span>`}</td>
      <td style="white-space:nowrap">${esc(fmtDate(new Date(b.ts * 1000).toISOString(), true))}</td><td class="num">${esc(fmtSize(b.size))}</td>
      ${manage ? `<td style="text-align:end;white-space:nowrap"><button class="btn sm" data-v="${esc(b.name)}">${ic('check', 14)}${t('bk.verify')}</button> <a class="ib" href="/api/backups/${encodeURIComponent(b.name)}/download" title="${t('doc.download')}">${ic('download', 15)}</a></td>` : ''}</tr>`).join('')}</tbody></table></div>` : `<div class="empty">${ic('db', 34)}<b>${t('bk.none')}</b></div>`}</div>
  <div class="s4" style="display:flex;flex-direction:column;gap:18px"><div class="card"><h3>${t('bk.where')}</h3><div class="sub">${t('bk.where_sub')}</div><div class="mono" style="word-break:break-all;background:var(--surface2);border-radius:10px;padding:10px">${esc(r.dir)}</div>
  ${manage ? `<div class="sub" style="margin-top:12px">${t('bk.offsite')}</div>` : ''}
  <div class="sub" style="margin-top:14px">${t('bk.restore')}</div><div class="mono" style="background:var(--surface2);border-radius:10px;padding:10px;font-size:12px;white-space:pre-wrap">docker compose stop
docker compose run --rm assetmaster python tools/manage.py restore &lt;${t('bk.file')}&gt;
docker compose up -d</div></div></div>
  <div class="card s12" id="hcard"></div></div>`;
  healthCard($('#hcard'), false);
  $$('[data-v]', el).forEach(btn => btn.onclick = async () => {
    btn.disabled = true;
    try {
      const res = (await api(`/api/backups/${encodeURIComponent(btn.dataset.v)}/verify`, { method: 'POST', body: {} })).result;
      res.ok ? toast(t('bk.verify_ok'), t('bk.verify_detail', { files: res.files, assets: (res.counts || {}).assets ?? '—' }))
        : toast(t('bk.verify_bad'), res.problems.slice(0, 3).join(', '), 'err');
    } catch (e) { fail(e); }
    btn.disabled = false;
  });
  const b = $('#bk'); if (b) b.onclick = async () => { b.disabled = true; try { await api('/api/backups', { method: 'POST', body: {} }); toast(t('bk.done')); render(); } catch (e) { fail(e); b.disabled = false; } };
}

/* ============ my account ============ */
async function pAccount(el) {
  pageHead(t('settings.title'), t('settings.sub'));
  el.innerHTML = `<div class="grid g12"><div class="card s5"><h3>${t('acc.profile')}</h3><dl style="display:grid;grid-template-columns:130px 1fr;gap:10px 14px;margin:14px 0 0"><dt style="color:var(--mut)">${t('users.full_name')}</dt><dd style="margin:0;font-weight:600">${esc(S.user.full_name)}</dd><dt style="color:var(--mut)">${t('login.username')}</dt><dd class="mono" style="margin:0">${esc(S.user.username)}</dd><dt style="color:var(--mut)">${t('users.email')}</dt><dd class="mono" style="margin:0">${esc(S.user.email || '—')}</dd><dt style="color:var(--mut)">${t('users.role')}</dt><dd style="margin:0"><span class="badge info">${esc(nameOf(S.user, 'role_name'))}</span></dd></dl>
  <h3 style="margin-top:24px">${t('acc.prefs')}</h3><div class="toolbar" style="margin-top:10px"><div class="seg" id="sl"><button data-l="en" class="${LANG === 'en' ? 'on' : ''}">English</button><button data-l="ar" class="${LANG === 'ar' ? 'on' : ''}">العربية</button></div>
  <div class="seg" id="st">${['light', 'dark', 'system'].map(x => `<button data-t="${x}" class="${S.themePref === x ? 'on' : ''}">${t('theme.' + x)}</button>`).join('')}</div></div>
  <label class="cb" style="margin-top:14px;display:flex;gap:10px;align-items:center;font-weight:600;cursor:pointer"><input type="checkbox" id="acc-mail" ${S.user.email_alerts ? 'checked' : ''} ${S.user.email ? '' : 'disabled'} style="width:18px;height:18px;accent-color:var(--brand)"> ${ic('mail', 16)} ${t('acc.email_alerts')}</label>
  <div class="mut" style="font-size:12.5px;margin-top:4px">${S.user.email ? t('acc.email_alerts_hint') : t('acc.no_email')}</div></div>
  <form class="card s7" id="pf" novalidate><h3>${t('pw.change_title')}</h3><div class="sub">${t('pw.change_sub')}</div><div class="grid" style="gap:14px;max-width:420px">${passwordFields()}<button class="btn pri" type="submit">${t('pw.change')}</button></div></form></div>
  ${adminLinks()}
  <div class="card" style="margin-top:18px;display:flex;align-items:center;gap:14px;flex-wrap:wrap"><div class="grow" style="flex:1;min-width:200px"><h3 style="margin:0">${t('settings.signout_title')}</h3><div class="sub" style="margin:4px 0 0">${esc(t('settings.signout_sub', { name: S.user.full_name }))}</div></div><button class="btn dng" id="acc-out">${ic('logout', 16)}${t('nav.logout')}</button></div>`;
  $$('#sl button').forEach(b => b.onclick = () => setLang(b.dataset.l)); $$('#st button').forEach(b => b.onclick = () => setTheme(b.dataset.t));
  $('#acc-mail').onchange = async e => { try { await api('/api/auth/prefs', { method: 'PUT', body: { lang: LANG, theme: S.themePref, email_alerts: e.target.checked } }); S.user.email_alerts = e.target.checked; toast(t('toast.saved')); } catch (err) { fail(err); } };
  bindPasswordForm($('#pf'));
  $('#acc-out').onclick = logout;
}
/* company-wide settings, shown on the Settings page to the people allowed to open them */
function adminLinks() {
  const L = [['company', 'settings.l_company'], ['users', 'settings.l_users'], ['roles', 'settings.l_roles'], ['backups', 'settings.l_backups'], ['audit', 'settings.l_audit'], ['license', 'settings.l_license']]
    .map(([k, d]) => [NAV.find(n => n[0] === k), d]).filter(([n]) => n && canSee(n[2]) && !(n[0] === 'license' && licOff()));
  if (!L.length) return '';
  return `<div class="card" style="margin-top:18px"><h3>${t('settings.admin')}</h3><div class="sub">${t('settings.admin_sub')}</div><div class="setlinks">${L.map(([n, d]) => `<a href="#/${n[0]}">${ic(n[1], 18)}<span><b>${t('nav.' + n[0])}</b><small>${t(d)}</small></span></a>`).join('')}</div></div>`;
}

/* ============ phase 2: shared helpers ============ */
const STATUSES = ['in_stock', 'assigned', 'maintenance', 'retired', 'lost'], MANUAL_ST = ['in_stock', 'maintenance', 'retired', 'lost'];
const ST_CLS = { in_stock: 'good', assigned: 'info', maintenance: 'warn', retired: 'mut', lost: 'bad' };
const stBadge = s => `<span class="badge ${ST_CLS[s] || 'mut'}">${esc(t('st.' + s))}</span>`;
const condOpts = cur => ['new', 'good', 'fair', 'poor', 'damaged'].map(c => `<option value="${c}" ${c === cur ? 'selected' : ''}>${esc(t('cond.' + c))}</option>`).join('');
const money = n => (n === null || n === undefined || n === '') ? '—' : Number(n).toLocaleString(loc(), { maximumFractionDigits: 2 });
const dd = (id, opts, a = '') => `<select id="f-${id}" ${a}>${opts}</select>`;
const txa = (id, v = '') => `<textarea id="f-${id}" class="txt">${esc(v)}</textarea>`;
const fv = (m, id) => { const e = $('#f-' + id, m); return e ? e.value.trim() : ''; };
const today = () => new Date().toISOString().slice(0, 10);
const initials = s => (s || '?').trim().split(/\s+/).slice(0, 2).map(x => x[0]).join('').toUpperCase();
const flipPager = () => { $('#prev').firstElementChild.style.transform = LANG === 'ar' ? '' : 'scaleX(-1)'; $('#next').firstElementChild.style.transform = LANG === 'ar' ? 'scaleX(-1)' : ''; };
let CATS = null;
async function cats(force) { if (!CATS || force) CATS = (await api('/api/categories')).categories; return CATS; }
const footBtns = label => `<div class="foot"><button type="button" class="btn" data-x="cancel">${t('common.cancel')}</button><button class="btn pri" type="submit">${esc(label || t('common.save'))}</button></div>`;
const bindCancel = m => { const b = $('[data-x="cancel"]', m); if (b) b.onclick = () => m.close(); };
/* submit a modal form: collects body, sends it, shows field errors inline */
function bindSubmit(m, form, send) {
  form.onsubmit = async ev => {
    ev.preventDefault(); const btn = $('button[type=submit]', form); btn.disabled = true;
    try { await send(); } catch (err) { if (!showErrors(form, err)) fail(err); } finally { btn.disabled = false; }
  };
}

/* ============ assets ============ */
const ASSET_SORTS = ['newest', 'oldest', 'tag', 'tag_desc', 'name', 'category', 'status', 'holder', 'location', 'purchase_new', 'purchase_old', 'cost_high', 'cost_low', 'warranty'];
let AS = { q: '', status: '', category: '', page: 1, sel: new Set(), rows: [], sort: sortPref('assets', 'newest', ASSET_SORTS) };
async function pAssets(el) {
  const manage = has('assets.manage');
  pageHead(t('assets.title'), t('assets.sub'), `<button class="btn sm" id="expa">${ic('download', 15)}${t('imp.export')}</button>` +
    (manage ? `<button class="btn sm" id="impa">${ic('sheet', 15)}${t('imp.import')}</button><button class="btn pri sm" id="adda">${ic('plus', 16)}${t('assets.add')}</button>` : ''));
  const cl = await cats(true);
  el.innerHTML = `${!cl.length ? `<div class="banner warn">${ic('warn', 20)}<div class="grow"><b>${t('assets.no_categories')}</b>${t('assets.no_categories_sub')}</div>${has('categories.manage') ? `<a class="btn sm" href="#/categories">${t('nav.categories')}</a>` : ''}</div>` : ''}
  <div class="card"><div class="toolbar"><input class="inp" id="aq" style="max-width:300px" placeholder="${t('assets.search')}" value="${esc(AS.q)}">
  <select class="sel" id="ast"><option value="">${t('assets.all_status')}</option>${STATUSES.map(s => `<option value="${s}" ${AS.status === s ? 'selected' : ''}>${esc(t('st.' + s))}</option>`).join('')}</select>
  <select class="sel" id="acat"><option value="">${t('assets.all_cat')}</option>${cl.map(c => `<option value="${c.id}" ${AS.category == c.id ? 'selected' : ''}>${esc(nameOf(c))}</option>`).join('')}</select>
  ${sortSel('asort', ASSET_SORTS, AS.sort)}<div class="sp"></div><button class="btn sm" id="albl">${ic('qr', 15)}<span></span></button><span class="badge mut" id="acount"></span></div><div id="atbl"><div class="skel">${t('common.loading')}</div></div>
  <div class="toolbar" style="margin:14px 0 0"><button class="btn sm" id="prev">${ic('chev', 14)}</button><span id="pg" class="badge mut"></span><button class="btn sm" id="next">${ic('chev', 14)}</button></div></div>`;
  flipPager();
  const load = async () => {
    AS.q = $('#aq').value.trim(); AS.status = $('#ast').value; AS.category = $('#acat').value; AS.sort = $('#asort').value;
    const r = await api('/api/assets?' + new URLSearchParams({ q: AS.q, status: AS.status, category: AS.category, sort: AS.sort, page: AS.page, per_page: 25 }));
    if (!$('#atbl')) return;
    const pages = Math.max(1, Math.ceil(r.total / r.per_page));
    if (AS.page > pages) { AS.page = pages; return load(); }
    $('#acount').textContent = r.total; $('#pg').textContent = `${r.page} / ${pages}`; $('#prev').disabled = r.page <= 1; $('#next').disabled = r.page >= pages;
    const filtered = AS.q || AS.status || AS.category;
    AS.rows = r.assets;
    $('#atbl').innerHTML = r.assets.length ? `<div class="tscroll"><table class="tbl"><thead><tr><th style="width:34px"><input type="checkbox" id="asel-all" title="${t('lbl.select_page')}" ${r.assets.every(a => AS.sel.has(a.id)) ? 'checked' : ''}></th><th>${t('assets.tag')}</th><th>${t('assets.asset')}</th><th>${t('assets.category')}</th><th>${t('assets.status')}</th><th>${t('assets.holder')}</th><th>${t('assets.location')}</th></tr></thead><tbody>${r.assets.map(a => `<tr class="click" data-id="${a.id}">
      <td><input type="checkbox" class="asel" data-id="${a.id}" ${AS.sel.has(a.id) ? 'checked' : ''}></td>
      <td class="mono" style="white-space:nowrap"><b>${esc(a.tag)}</b></td>
      <td><b>${esc(a.name)}</b>${a.brand || a.model ? `<div class="mut" style="font-size:12.5px">${esc([a.brand, a.model].filter(Boolean).join(' · '))}</div>` : ''}</td>
      <td>${esc(nameOf(a, 'cat'))}</td><td>${stBadge(a.status)}</td>
      <td>${a.holder_id ? `<b>${esc(nameOf(a, 'holder'))}</b><div class="mono mut" style="font-size:12px">${esc(a.holder_no)}</div>` : '<span class="mut">—</span>'}</td>
      <td>${esc(a.location || '—')}</td></tr>`).join('')}</tbody></table></div>`
      : `<div class="empty">${ic('box', 36)}<b>${filtered ? t('common.no_results') : t('assets.none')}</b>${filtered ? '' : t('assets.none_sub')}</div>`;
    $$('#atbl tr.click').forEach(tr => tr.onclick = ev => { if (ev.target.closest('input')) return; assetDetail(+tr.dataset.id, load); });
    $$('#atbl .asel').forEach(c => c.onchange = () => { c.checked ? AS.sel.add(+c.dataset.id) : AS.sel.delete(+c.dataset.id); lblBtn(); });
    const all = $('#asel-all'); if (all) all.onchange = () => { r.assets.forEach(a => all.checked ? AS.sel.add(a.id) : AS.sel.delete(a.id)); $$('#atbl .asel').forEach(c => c.checked = all.checked); lblBtn(); };
    lblBtn();
  };
  const lblBtn = () => { const b = $('#albl'); if (!b) return; $('span', b).textContent = AS.sel.size ? t('lbl.print_n', { n: AS.sel.size }) : t('lbl.print_page'); b.disabled = !AS.sel.size && !(AS.rows || []).length; };
  $('#albl').onclick = () => { const ids = AS.sel.size ? [...AS.sel] : (AS.rows || []).map(a => a.id); if (ids.length) openLabels(ids); };
  const reset = debounce(() => { AS.page = 1; load().catch(fail); }, 250);
  $('#aq').addEventListener('input', reset); $('#ast').onchange = reset; $('#acat').onchange = reset;
  $('#asort').onchange = () => { sortSave('assets', $('#asort').value); reset(); };
  $('#prev').onclick = () => { AS.page--; load().catch(fail); }; $('#next').onclick = () => { AS.page++; load().catch(fail); };
  const add = $('#adda'); if (add) add.onclick = () => cl.length ? assetForm(null, load) : toast(t('assets.no_categories'), t('assets.no_categories_sub'), 'err');
  const imp = $('#impa'); if (imp) imp.onclick = () => cl.length ? importModal('assets', load) : toast(t('assets.no_categories'), t('assets.no_categories_sub'), 'err');
  $('#expa').onclick = () => exportFile('/api/export/assets', { q: AS.q, status: AS.status, category: AS.category, sort: AS.sort });
  await load();
}

function customInput(f, v) {
  const id = 'cf-' + f.key, lab = nameOf(f, 'label');
  let input;
  if (f.type === 'bool') input = `<label class="cb"><input type="checkbox" id="${id}" ${v ? 'checked' : ''}>${esc(lab)}</label>`;
  else if (f.type === 'select') input = `<select id="${id}"><option value="">—</option>${f.options.map(o => `<option ${o === v ? 'selected' : ''}>${esc(o)}</option>`).join('')}</select>`;
  else input = `<input id="${id}" value="${esc(v ?? '')}" ${f.type === 'number' ? 'type="number" step="any" dir="ltr"' : f.type === 'date' ? 'type="date"' : ''}>`;
  return `<div class="fld" data-f="custom.${esc(f.key)}">${f.type === 'bool' ? '<label>&nbsp;</label>' : `<label for="${id}">${esc(lab)}${f.required ? '<span class="req">*</span>' : ''}</label>`}${input}<div class="em"></div></div>`;
}

async function assetForm(a, done, preset = {}) {
  const cl = await cats(), edit = !!a;
  const cur = edit ? a.category_id : (AS.category || cl[0].id);
  const m = modal(`<h2>${edit ? t('assets.edit') : t('assets.add')}</h2><div class="sub">${edit ? `<span class="mono">${esc(a.tag)}</span>` : t('assets.add_sub')}</div><form id="af" novalidate><div class="fg">
    ${field('category_id', t('assets.category'), dd('category_id', cl.map(c => `<option value="${c.id}" ${cur == c.id ? 'selected' : ''}>${esc(nameOf(c))} (${esc(c.code)})</option>`).join('')), { req: true })}
    ${field('tag', t('assets.tag'), inp('tag', edit ? a.tag : (preset.tag || ''), `dir="ltr" class="mono" autocomplete="off" placeholder="${esc(t('assets.tag_auto'))}"`), { hint: edit ? '' : t('assets.tag_hint') })}
    ${field('name', t('assets.name'), inp('name', edit ? a.name : ''), { req: true, full: true })}
    ${field('brand', t('assets.brand'), inp('brand', edit ? a.brand : ''))}${field('model', t('assets.model'), inp('model', edit ? a.model : ''))}
    ${field('serial_no', t('assets.serial'), inp('serial_no', edit ? a.serial_no : (preset.serial_no || ''), 'dir="ltr" class="mono" autocomplete="off"'))}
    ${field('condition', t('assets.condition'), dd('condition', condOpts(edit ? a.condition : 'new')))}
    ${field('location', t('assets.location'), inp('location', edit ? a.location : ''))}${field('supplier', t('assets.supplier'), inp('supplier', edit ? a.supplier : ''))}
    ${field('purchase_date', t('assets.purchase_date'), inp('purchase_date', edit ? a.purchase_date : '', 'type="date"'))}
    ${field('purchase_cost', t('assets.cost'), inp('purchase_cost', edit && a.purchase_cost !== null ? a.purchase_cost : '', 'type="number" step="0.01" min="0" dir="ltr"'))}
    ${field('warranty_until', t('assets.warranty'), inp('warranty_until', edit ? a.warranty_until : '', 'type="date"'))}<div></div>
    <div class="full" id="cfx"></div>
    ${field('notes', t('assets.notes'), txa('notes', edit ? a.notes : ''), { full: true })}</div>${footBtns()}</form>`, 'lg');
  const catNow = () => cl.find(x => x.id == $('#f-category_id', m).value);
  const drawCustom = () => {
    const c = catNow(), vals = edit && a.category_id == c.id ? a.custom : {};
    $('#cfx', m).innerHTML = c.fields.length ? `<div class="sect" style="margin-top:0"><h4>${ic('list', 14)}${t('assets.custom')} · ${esc(nameOf(c))}</h4><div class="fg">${c.fields.map(f => customInput(f, vals[f.key])).join('')}</div></div>` : '';
  };
  $('#f-category_id', m).onchange = drawCustom; drawCustom(); bindCancel(m);
  bindSubmit(m, $('#af', m), async () => {
    const body = {}; ['category_id', 'tag', 'name', 'brand', 'model', 'serial_no', 'condition', 'location', 'supplier', 'purchase_date', 'purchase_cost', 'warranty_until', 'notes'].forEach(k => body[k] = fv(m, k));
    body.category_id = +body.category_id; body.custom = {};
    catNow().fields.forEach(f => { const e = $('#cf-' + f.key, m); body.custom[f.key] = f.type === 'bool' ? e.checked : e.value.trim(); });
    if (edit) { await api('/api/assets/' + a.id, { method: 'PUT', body }); toast(t('toast.saved')); }
    else { const r = await api('/api/assets', { method: 'POST', body }); toast(t('assets.created'), r.tag); }
    m.close(); done && done();
  });
}

function histDetail(h) {
  const d = h.detail || {}; let s = '';
  if (h.action === 'asset.status') s = t('st.' + d.from) + ' → ' + t('st.' + d.to) + (d.note ? ' — ' + d.note : '');
  else if (h.action === 'asset.assign' || h.action === 'asset.return') s = (d.employee || '') + (d.emp_no ? ' (' + d.emp_no + ')' : '') + (d.status ? ' → ' + t('st.' + d.status) : '');
  else if (h.action === 'asset.update') { const n = Object.keys(d).length; s = n ? t('assets.fields_changed', { n }) : t('assets.no_changes'); }
  return s ? `<div class="mut" style="font-size:13px">${esc(s)}</div>` : '';
}

async function assetDetail(id, onChange) {
  let a; try { a = await api('/api/assets/' + id); } catch (e) { return fail(e); }
  const mng = has('assets.manage'), asg = has('assignments.manage');
  const row = (k, v) => `<div><dt>${esc(k)}</dt><dd>${v === '' || v === null || v === undefined ? '—' : v}</dd></div>`;
  const cf = a.fields.map(f => { const v = a.custom[f.key]; const shown = v === undefined || v === '' ? '' : f.type === 'bool' ? (v ? t('common.yes') : t('common.no')) : f.type === 'date' ? fmtDate(v) : f.type === 'number' ? money(v) : v; return row(nameOf(f, 'label'), esc(shown)); }).join('');
  const wr = a.warranty_until ? esc(fmtDate(a.warranty_until)) + (a.warranty_until < today() ? ` <span class="badge bad">${t('assets.warranty_expired')}</span>` : '') : '';
  const m = modal(`<div style="display:flex;gap:14px;align-items:flex-start;flex-wrap:wrap"><div style="flex:1;min-width:240px"><div class="mono mut" style="font-size:13px">${esc(a.tag)}</div><h2>${esc(a.name)}</h2><div class="sub" style="margin-bottom:0">${esc(nameOf(a, 'cat'))}${a.brand || a.model ? ' · ' + esc([a.brand, a.model].filter(Boolean).join(' ')) : ''}</div></div>${stBadge(a.status)}</div>
  <div class="toolbar" style="margin:16px 0 0">
    ${asg && a.status === 'in_stock' ? `<button class="btn pri sm" id="d-assign">${ic('swap', 15)}${t('asg.assign')}</button>` : ''}
    ${asg && a.status === 'assigned' ? `<button class="btn pri sm" id="d-return">${ic('swap', 15)}${t('asg.return')}</button>` : ''}
    ${mng ? `<button class="btn sm" id="d-edit">${ic('edit', 15)}${t('common.edit')}</button>` : ''}
    ${mng && a.status !== 'assigned' ? `<button class="btn sm" id="d-status">${ic('refresh', 15)}${t('assets.change_status')}</button>` : ''}
    <button class="btn sm" id="d-label">${ic('qr', 15)}${t('lbl.label')}</button>
    <div class="sp"></div>${mng && !a.assignments.length ? `<button class="btn sm dng" id="d-del">${ic('trash', 15)}${t('common.delete')}</button>` : ''}<button class="btn sm" id="d-close">${t('common.close')}</button></div>
  ${a.holder_id ? `<div class="holder"><div class="av">${esc(initials(nameOf(a, 'holder')))}</div><div style="flex:1"><small>${t('assets.held_by')}</small><b>${esc(nameOf(a, 'holder'))}</b><small class="mono">${esc(a.holder_no)} · ${esc(t('asg.since', { d: fmtDate(a.assigned_at) }))}</small></div>${a.expected_return ? `<span class="badge ${a.expected_return < today() ? 'bad' : 'mut'}">${esc(t('asg.due', { d: fmtDate(a.expected_return) }))}</span>` : ''}<a class="btn sm" href="#/receipt?id=${a.assignment_id}&kind=handover" target="_blank" rel="noopener">${ic('printer', 15)}${t('rcpt.handover')}</a></div>` : ''}
  <div class="sect"><h4>${t('assets.details')}</h4><dl class="infogrid">${row(t('assets.serial'), a.serial_no ? `<span class="mono">${esc(a.serial_no)}</span>` : '')}${row(t('assets.condition'), esc(t('cond.' + a.condition)))}${row(t('assets.location'), esc(a.location))}${row(t('assets.purchase_date'), a.purchase_date ? esc(fmtDate(a.purchase_date)) : '')}${row(t('assets.cost'), a.purchase_cost !== null ? esc(money(a.purchase_cost)) : '')}${row(t('assets.supplier'), esc(a.supplier))}${row(t('assets.warranty'), wr)}${row(t('assets.added'), esc(fmtDate(a.created_at, true)))}</dl></div>
  ${cf ? `<div class="sect"><h4>${t('assets.custom')}</h4><dl class="infogrid">${cf}</dl></div>` : ''}
  ${a.notes ? `<div class="sect"><h4>${t('assets.notes')}</h4><div style="white-space:pre-wrap">${esc(a.notes)}</div></div>` : ''}
  <div class="sect"><h4>${t('assets.assign_history')}</h4>${a.assignments.length ? `<div class="tscroll"><table class="tbl"><thead><tr><th>${t('asg.employee')}</th><th>${t('asg.assigned_on')}</th><th>${t('asg.returned_on')}</th><th>${t('assets.condition')}</th><th>${t('rcpt.receipts')}</th></tr></thead><tbody>${a.assignments.map(g => `<tr><td><b>${esc(nameOf(g, 'full_name'))}</b><div class="mono mut" style="font-size:12px">${esc(g.emp_no)}</div></td><td style="white-space:nowrap">${esc(fmtDate(g.assigned_at, true))}<div class="mut" style="font-size:12px">${esc(g.assigned_by_name || '')}</div></td><td style="white-space:nowrap">${g.returned_at ? esc(fmtDate(g.returned_at, true)) + `<div class="mut" style="font-size:12px">${esc(g.returned_by_name || '')}</div>` : `<span class="badge info">${t('asg.current')}</span>`}</td><td>${esc(t('cond.' + g.condition_out))}${g.condition_in ? ' → ' + esc(t('cond.' + g.condition_in)) : ''}</td><td style="white-space:nowrap;font-size:12.5px">${receiptLink(g.id, 'handover', g.receipt_out_no)}${g.returned_at ? '<br>' + receiptLink(g.id, 'return', g.receipt_in_no) : ''}</td></tr>`).join('')}</tbody></table></div>` : `<div class="empty" style="padding:18px">${t('asg.never_assigned')}</div>`}</div>
  ${has('maintenance.view') ? `<div class="sect"><h4>${ic('tool', 14)}${t('mnt.title')}</h4><div id="d-mnt"></div></div>` : ''}
  <div class="sect"><h4>${ic('file', 14)}${t('doc.title')}</h4><div id="d-docs"><div class="skel" style="padding:10px">${t('common.loading')}</div></div></div>
  <div class="sect"><h4>${t('assets.activity')}</h4><ul class="tl">${a.history.map(h => `<li><span class="dot"></span><div><b>${esc(actionLabel(h.action))}</b>${histDetail(h)}<small>${esc(fmtDate(h.ts, true))} · ${esc(h.username || '—')}</small></div></li>`).join('')}</ul></div>`, 'lg');
  const changed = () => { m.close(); onChange && onChange(); assetDetail(id, onChange); };
  $('#d-close', m).onclick = () => m.close();
  docsSection($('#d-docs', m), 'asset', a.id, mng);
  if ($('#d-mnt', m)) maintenanceSection($('#d-mnt', m), a, changed);
  $('#d-label', m).onclick = () => openLabels([a.id]);
  const on = (sel, fn) => { const b = $(sel, m); if (b) b.onclick = fn; };
  on('#d-assign', () => assignForm(a, changed));
  on('#d-return', () => returnForm(a, changed));
  on('#d-edit', () => assetForm(a, changed));
  on('#d-status', () => statusForm(a, changed));
  on('#d-del', async () => { if (await confirmBox(t('assets.delete_q', { n: a.tag }), t('assets.delete_text'), t('common.delete'))) { try { await api('/api/assets/' + a.id, { method: 'DELETE' }); toast(t('toast.deleted')); m.close(); onChange && onChange(); } catch (e) { fail(e); } } });
}

function assignForm(a, done) {
  let chosen = null, last = [];
  const m = modal(`<h2>${t('asg.assign_title')}</h2><div class="sub"><span class="mono">${esc(a.tag)}</span> · ${esc(a.name)}</div><form id="gf" novalidate><div class="fg">
    <div class="fld full" data-f="employee_id"><label for="f-emp">${t('asg.employee')}<span class="req">*</span></label><input id="f-emp" autocomplete="off" placeholder="${t('asg.find_employee')}"><div class="pick" id="pick"></div><div class="em"></div></div>
    ${field('expected_return', t('asg.expected_return'), inp('expected_return', '', `type="date" min="${today()}"`), { hint: t('asg.expected_hint') })}
    ${field('condition', t('asg.condition_out'), dd('condition', condOpts(a.condition)))}
    ${field('notes', t('asg.notes'), txa('notes'), { full: true })}</div>${footBtns(t('asg.assign'))}</form>`);
  const draw = () => {
    $('#pick', m).innerHTML = last.length ? last.map(e => `<button type="button" data-id="${e.id}" class="${chosen && chosen.id === e.id ? 'on' : ''}"><div style="flex:1"><b>${esc(nameOf(e, 'full_name'))}</b> <small class="mono">${esc(e.emp_no)}</small>${e.dept_en ? `<div><small>${esc(nameOf(e, 'dept'))}</small></div>` : ''}</div>${chosen && chosen.id === e.id ? ic('check', 16) : ''}</button>`).join('') : `<div class="empty" style="padding:14px">${t('asg.no_employees')}</div>`;
    $$('#pick button', m).forEach(b => b.onclick = () => { chosen = last.find(e => e.id == b.dataset.id); draw(); });
  };
  const search = async () => { try { last = (await api('/api/employees/lookup?q=' + encodeURIComponent($('#f-emp', m).value.trim()))).employees; chosen = null; draw(); } catch (e) { fail(e); } };
  $('#f-emp', m).addEventListener('input', debounce(search, 200)); search(); bindCancel(m);
  bindSubmit(m, $('#gf', m), async () => {
    if (!chosen) throw { field: 'employee_id', code: 'pick_employee' };
    await api(`/api/assets/${a.id}/assign`, { method: 'POST', body: { employee_id: chosen.id, expected_return: fv(m, 'expected_return'), condition: fv(m, 'condition'), notes: fv(m, 'notes') } });
    toast(t('asg.assigned'), nameOf(chosen, 'full_name')); m.close(); done && done();
  });
}

function returnForm(a, done) {
  const m = modal(`<h2>${t('asg.return_title')}</h2><div class="sub"><span class="mono">${esc(a.tag)}</span> · ${esc(a.name)}</div><form id="rtf" novalidate><div class="fg">
    ${field('condition', t('asg.condition_in'), dd('condition', condOpts(a.condition)))}
    ${field('status_after', t('asg.status_after'), dd('status_after', MANUAL_ST.map(s => `<option value="${s}">${esc(t('st.' + s))}</option>`).join('')))}
    ${field('notes', t('asg.notes'), txa('notes'), { full: true })}</div>${footBtns(t('asg.return'))}</form>`, 'sm');
  bindCancel(m);
  bindSubmit(m, $('#rtf', m), async () => {
    await api(`/api/assets/${a.id}/return`, { method: 'POST', body: { condition: fv(m, 'condition'), status_after: fv(m, 'status_after'), notes: fv(m, 'notes') } });
    toast(t('asg.returned')); m.close(); done && done();
  });
}

function statusForm(a, done) {
  const m = modal(`<h2>${t('assets.change_status')}</h2><div class="sub"><span class="mono">${esc(a.tag)}</span> · ${t('assets.now')} ${esc(t('st.' + a.status))}</div><form id="stf" novalidate><div class="grid" style="gap:14px">
    ${field('status', t('assets.new_status'), dd('status', MANUAL_ST.filter(s => s !== a.status).map(s => `<option value="${s}">${esc(t('st.' + s))}</option>`).join('')))}
    ${field('note', t('assets.reason'), inp('note'))}</div>${footBtns()}</form>`, 'sm');
  bindCancel(m);
  bindSubmit(m, $('#stf', m), async () => {
    await api(`/api/assets/${a.id}/status`, { method: 'POST', body: { status: fv(m, 'status'), note: fv(m, 'note') } });
    toast(t('toast.saved')); m.close(); done && done();
  });
}

/* ============ assignments ============ */
async function pAssignments(el) {
  const asg = has('assignments.manage');
  pageHead(t('asg.title'), t('asg.sub'), `<button class="btn sm" id="expg">${ic('download', 15)}${t('imp.export_history')}</button><a class="btn sm" href="#/assets">${ic('box', 15)}${t('nav.assets')}</a>`);
  $('#expg').onclick = () => exportFile('/api/export/assignments');
  const GS = { overdue: null, newest: by(g => g.assigned_at, true), oldest: by(g => g.assigned_at), due: by(g => g.expected_return), employee: by(g => nameOf(g, 'full_name')),
    department: by(g => g.dept_en ? nameOf(g, 'dept') : ''), tag: by(g => g.tag) };
  let gsort = sortPref('assignments', 'overdue', Object.keys(GS));
  el.innerHTML = `<div class="card"><div class="toolbar"><input class="inp" id="gq" style="max-width:320px" placeholder="${t('asg.search')}">${sortSel('gsort', Object.keys(GS), gsort)}<div class="sp"></div><span class="badge mut" id="gcount"></span></div><div id="gtbl"><div class="skel">${t('common.loading')}</div></div></div>`;
  const load = async () => {
    const list = sortRows((await api('/api/assignments?q=' + encodeURIComponent($('#gq').value.trim()))).assignments, GS[gsort]);
    if (!$('#gtbl')) return;
    const od = list.filter(g => g.overdue).length;
    $('#gcount').textContent = list.length + (od ? ' · ' + t('asg.overdue_n', { n: od }) : '');
    $('#gtbl').innerHTML = list.length ? `<div class="tscroll"><table class="tbl"><thead><tr><th>${t('assets.asset')}</th><th>${t('asg.employee')}</th><th>${t('emp.department')}</th><th>${t('asg.assigned_on')}</th><th>${t('asg.expected_return')}</th><th></th></tr></thead><tbody>${list.map(g => `<tr class="click" data-a="${g.asset_id}">
      <td><span class="mono"><b>${esc(g.tag)}</b></span><div style="font-size:13px">${esc(g.asset_name)}</div></td>
      <td><b>${esc(nameOf(g, 'full_name'))}</b><div class="mono mut" style="font-size:12px">${esc(g.emp_no)}</div></td>
      <td>${esc(g.dept_en ? nameOf(g, 'dept') : '—')}</td><td style="white-space:nowrap">${esc(fmtDate(g.assigned_at))}</td>
      <td>${g.expected_return ? `<span class="badge ${g.overdue ? 'bad' : 'mut'}">${esc(fmtDate(g.expected_return))}${g.overdue ? ' · ' + t('asg.overdue') : ''}</span>` : '<span class="mut">—</span>'}</td>
      <td style="text-align:end;white-space:nowrap">${receiptLink(g.id, 'handover', g.receipt_out_no)} ${asg ? `<button class="btn sm" data-r="${g.asset_id}">${t('asg.return')}</button>` : ''}</td></tr>`).join('')}</tbody></table></div>`
      : `<div class="empty">${ic('swap', 36)}<b>${t('asg.none')}</b>${t('asg.none_sub')}</div>`;
    $$('#gtbl tr.click').forEach(tr => tr.onclick = ev => { if (ev.target.closest('[data-r],a')) return; assetDetail(+tr.dataset.a, load); });
    $$('#gtbl [data-r]').forEach(b => b.onclick = () => { const g = list.find(x => x.asset_id == b.dataset.r); returnForm({ id: g.asset_id, tag: g.tag, name: g.asset_name, condition: g.condition_out }, load); });
  };
  $('#gq').addEventListener('input', debounce(() => load().catch(fail), 250));
  $('#gsort').onchange = () => { gsort = $('#gsort').value; sortSave('assignments', gsort); load().catch(fail); };
  await load();
}

/* ============ employees ============ */
let EM = { q: '', status: 'active', dept: '' };
async function pEmployees(el) {
  const manage = has('employees.manage');
  pageHead(t('emp.title'), t('emp.sub'), `<button class="btn sm" id="expe">${ic('download', 15)}${t('imp.export')}</button>` +
    (manage ? `<button class="btn sm" id="impe">${ic('sheet', 15)}${t('imp.import')}</button><button class="btn sm" id="depts">${ic('building', 15)}${t('emp.departments')}</button><button class="btn pri sm" id="adde">${ic('plus', 16)}${t('emp.add')}</button>` : ''));
  let depts = (await api('/api/departments')).departments;
  const ES = { name: by(e => nameOf(e, 'full_name')), name_desc: by(e => nameOf(e, 'full_name'), true), emp_no: by(e => e.emp_no), department: by(e => e.dept_en ? nameOf(e, 'dept') : ''),
    holding: (a, b) => (b.holding || 0) - (a.holding || 0) || cmpText(nameOf(a, 'full_name'), nameOf(b, 'full_name')), newest: (a, b) => b.id - a.id };
  let esort = sortPref('employees', 'name', Object.keys(ES));
  el.innerHTML = `<div class="card"><div class="toolbar"><input class="inp" id="eq" style="max-width:300px" placeholder="${t('emp.search')}" value="${esc(EM.q)}">
  <select class="sel" id="est"><option value="active">${t('emp.st_active')}</option><option value="left">${t('emp.st_left')}</option><option value="">${t('emp.st_all')}</option></select>
  <select class="sel" id="edp"></select>${sortSel('esort', Object.keys(ES), esort)}<div class="sp"></div><span class="badge mut" id="ecount"></span></div><div id="etbl"><div class="skel">${t('common.loading')}</div></div></div>`;
  $('#est').value = EM.status;
  const drawDepts = () => { $('#edp').innerHTML = `<option value="">${t('emp.all_depts')}</option>` + depts.map(d => `<option value="${d.id}">${esc(nameOf(d))}</option>`).join(''); $('#edp').value = EM.dept; };
  drawDepts();
  const load = async () => {
    EM.q = $('#eq').value.trim(); EM.status = $('#est').value; EM.dept = $('#edp').value;
    const list = sortRows((await api('/api/employees?' + new URLSearchParams({ q: EM.q, status: EM.status, department: EM.dept }))).employees, ES[esort]);
    if (!$('#etbl')) return;
    $('#ecount').textContent = list.length;
    $('#etbl').innerHTML = list.length ? `<div class="tscroll"><table class="tbl"><thead><tr><th>${t('emp.no')}</th><th>${t('emp.name')}</th><th>${t('emp.department')}</th><th>${t('emp.job')}</th><th>${t('emp.holding')}</th><th>${t('users.status')}</th></tr></thead><tbody>${list.map(e => `<tr class="click" data-id="${e.id}">
      <td class="mono"><b>${esc(e.emp_no)}</b></td><td><b>${esc(nameOf(e, 'full_name'))}</b>${e.email ? `<div class="mono mut" style="font-size:12px">${esc(e.email)}</div>` : ''}</td>
      <td>${esc(e.dept_en ? nameOf(e, 'dept') : '—')}</td><td>${esc(e.job_title || '—')}</td>
      <td>${e.holding ? `<span class="badge info">${ic('box', 12)}${e.holding}</span>` : '<span class="mut">0</span>'}</td>
      <td>${e.status === 'active' ? `<span class="badge good">${t('emp.active')}</span>` : `<span class="badge mut">${t('emp.left')}</span>`}</td></tr>`).join('')}</tbody></table></div>`
      : `<div class="empty">${ic('idcard', 36)}<b>${EM.q || EM.dept ? t('common.no_results') : t('emp.none')}</b>${EM.q || EM.dept ? '' : t('emp.none_sub')}</div>`;
    $$('#etbl tr.click').forEach(tr => tr.onclick = () => employeeDetail(+tr.dataset.id, load));
  };
  pEmployees.reloadDepts = async () => { depts = (await api('/api/departments')).departments; drawDepts(); };
  $('#eq').addEventListener('input', debounce(() => load().catch(fail), 250)); $('#est').onchange = () => load().catch(fail); $('#edp').onchange = () => load().catch(fail);
  $('#esort').onchange = () => { esort = $('#esort').value; sortSave('employees', esort); load().catch(fail); };
  const add = $('#adde'); if (add) add.onclick = () => employeeForm(null, depts, load);
  const dp = $('#depts'); if (dp) dp.onclick = () => departmentsModal(async () => { await pEmployees.reloadDepts(); await load(); });
  const imp = $('#impe'); if (imp) imp.onclick = () => importModal('employees', async () => { await pEmployees.reloadDepts(); await load(); });
  $('#expe').onclick = () => exportFile('/api/export/employees', { q: EM.q, status: EM.status, department: EM.dept });
  await load();
}

function employeeForm(e, depts, done) {
  const edit = !!e;
  const m = modal(`<h2>${edit ? t('emp.edit') : t('emp.add')}</h2><div class="sub">${edit ? `<span class="mono">${esc(e.emp_no)}</span>` : t('emp.add_sub')}</div><form id="ef" novalidate><div class="fg">
    ${field('emp_no', t('emp.no'), inp('emp_no', edit ? e.emp_no : '', 'dir="ltr" class="mono" autocomplete="off"'), { req: true })}
    ${field('department_id', t('emp.department'), dd('department_id', `<option value="">—</option>` + depts.map(d => `<option value="${d.id}" ${edit && e.department_id === d.id ? 'selected' : ''}>${esc(nameOf(d))}</option>`).join('')))}
    ${field('full_name_en', t('emp.name_en'), inp('full_name_en', edit ? e.full_name_en : '', 'dir="ltr"'), { req: true })}
    ${field('full_name_ar', t('emp.name_ar'), inp('full_name_ar', edit ? e.full_name_ar : '', 'dir="rtl"'))}
    ${field('job_title', t('emp.job'), inp('job_title', edit ? e.job_title : ''))}
    ${field('status', t('users.status'), dd('status', ['active', 'left'].map(s => `<option value="${s}" ${(edit ? e.status : 'active') === s ? 'selected' : ''}>${t('emp.' + s)}</option>`).join('')))}
    ${field('email', t('users.email'), inp('email', edit ? e.email : '', 'type="email" dir="ltr"'))}
    ${field('phone', t('emp.phone'), inp('phone', edit ? e.phone : '', 'dir="ltr"'))}
    ${edit && e.national_id_masked ? '' : field('national_id', t('emp.national_id'), inp('national_id', edit ? e.national_id : '', 'dir="ltr" class="mono" inputmode="numeric" autocomplete="off" maxlength="40" placeholder="29901011234567"'), { full: true, hint: t('emp.national_id_hint') })}
    ${field('notes', t('assets.notes'), txa('notes', edit ? e.notes : ''), { full: true })}</div>${footBtns()}</form>`);
  bindCancel(m);
  bindSubmit(m, $('#ef', m), async () => {
    const body = {}; ['emp_no', 'full_name_en', 'full_name_ar', 'job_title', 'status', 'email', 'phone', 'notes'].forEach(k => body[k] = fv(m, k));
    if ($('#f-national_id', m)) body.national_id = fv(m, 'national_id');
    body.department_id = +fv(m, 'department_id') || null;
    if (edit) { await api('/api/employees/' + e.id, { method: 'PUT', body }); toast(t('toast.saved')); }
    else { await api('/api/employees', { method: 'POST', body }); toast(t('emp.created')); }
    m.close(); done && done();
  });
}

async function employeeDetail(id, onChange) {
  let e; try { e = await api('/api/employees/' + id); } catch (err) { return fail(err); }
  const manage = has('employees.manage'), seeAssets = has('assets.view');
  const open = e.assignments.filter(g => !g.returned_at), past = e.assignments.filter(g => g.returned_at);
  const row = (k, v) => `<div><dt>${esc(k)}</dt><dd>${v || '—'}</dd></div>`;
  const gtable = (list, cur) => `<div class="tscroll"><table class="tbl"><thead><tr><th>${t('assets.asset')}</th><th>${t('assets.category')}</th><th>${t('asg.assigned_on')}</th><th>${cur ? t('asg.expected_return') : t('asg.returned_on')}</th><th>${t('rcpt.receipts')}</th></tr></thead><tbody>${list.map(g => `<tr class="${seeAssets ? 'click' : ''}" data-a="${g.asset_id}"><td><span class="mono"><b>${esc(g.tag)}</b></span><div style="font-size:13px">${esc(g.asset_name)}</div></td><td>${esc(nameOf(g, 'cat'))}</td><td style="white-space:nowrap">${esc(fmtDate(g.assigned_at))}</td><td style="white-space:nowrap">${cur ? (g.expected_return ? `<span class="badge ${g.expected_return < today() ? 'bad' : 'mut'}">${esc(fmtDate(g.expected_return))}</span>` : '—') : esc(fmtDate(g.returned_at))}</td><td style="white-space:nowrap;font-size:12.5px">${receiptLink(g.id, 'handover', g.receipt_out_no)}${g.returned_at ? '<br>' + receiptLink(g.id, 'return', g.receipt_in_no) : ''}</td></tr>`).join('')}</tbody></table></div>`;
  const m = modal(`<div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap"><div class="holder" style="margin:0;flex:1;background:none;border:0;padding:0"><div class="av">${esc(initials(nameOf(e, 'full_name')))}</div><div><h2 style="margin:0">${esc(nameOf(e, 'full_name'))}</h2><small class="mono">${esc(e.emp_no)}</small>${e.job_title ? `<small> · ${esc(e.job_title)}</small>` : ''}</div></div>${e.status === 'active' ? `<span class="badge good">${t('emp.active')}</span>` : `<span class="badge mut">${t('emp.left')}</span>`}</div>
  <div class="toolbar" style="margin:16px 0 0">${manage ? `<button class="btn sm" id="e-edit">${ic('edit', 15)}${t('common.edit')}</button>` : ''}<div class="sp"></div>${manage && !e.assignments.length ? `<button class="btn sm dng" id="e-del">${ic('trash', 15)}${t('common.delete')}</button>` : ''}<button class="btn sm" id="e-close">${t('common.close')}</button></div>
  <div class="sect"><h4>${t('assets.details')}</h4><dl class="infogrid">${row(t('emp.department'), e.dept_en ? esc(nameOf(e, 'dept')) : '')}${row(t('users.email'), e.email ? `<span class="mono">${esc(e.email)}</span>` : '')}${row(t('emp.phone'), e.phone ? `<span class="mono">${esc(e.phone)}</span>` : '')}${row(t('emp.national_id'), e.national_id ? `<span class="mono" dir="ltr">${esc(e.national_id)}</span>` : '')}${row(LANG === 'ar' ? t('emp.name_en') : t('emp.name_ar'), esc(LANG === 'ar' ? e.full_name_en : e.full_name_ar))}</dl></div>
  ${e.notes ? `<div class="sect"><h4>${t('assets.notes')}</h4><div style="white-space:pre-wrap">${esc(e.notes)}</div></div>` : ''}
  <div class="sect"><h4>${t('emp.current_assets')} <span class="badge info">${open.length}</span></h4>${open.length ? gtable(open, true) : `<div class="empty" style="padding:18px">${t('emp.no_assets')}</div>`}</div>
  ${past.length ? `<div class="sect"><h4>${t('emp.past_assets')}</h4>${gtable(past, false)}</div>` : ''}
  <div class="sect"><h4>${ic('file', 14)}${t('doc.title')}</h4><div id="e-docs"></div></div>`, 'lg');
  $('#e-close', m).onclick = () => m.close();
  docsSection($('#e-docs', m), 'employee', e.id, manage);
  if (seeAssets) $$('tr.click', m).forEach(tr => tr.onclick = ev => { if (ev.target.closest('a')) return; m.close(); assetDetail(+tr.dataset.a, onChange); });
  const ed = $('#e-edit', m); if (ed) ed.onclick = async () => { const depts = (await api('/api/departments')).departments; employeeForm(e, depts, () => { m.close(); onChange && onChange(); employeeDetail(id, onChange); }); };
  const dl = $('#e-del', m); if (dl) dl.onclick = async () => { if (await confirmBox(t('emp.delete_q', { n: nameOf(e, 'full_name') }), t('emp.delete_text'), t('common.delete'))) { try { await api('/api/employees/' + id, { method: 'DELETE' }); toast(t('toast.deleted')); m.close(); onChange && onChange(); } catch (err) { fail(err); } } };
}

function departmentsModal(done) {
  let editing = null;
  const m = modal(`<h2>${t('emp.departments')}</h2><div class="sub">${t('dept.sub')}</div><div id="dl"><div class="skel">${t('common.loading')}</div></div>
  <form id="dfm" class="toolbar" style="margin:14px 0 0" novalidate><input class="inp" id="dn_en" placeholder="${t('dept.name_en')}" dir="ltr" style="flex:1;min-width:150px"><input class="inp" id="dn_ar" placeholder="${t('dept.name_ar')}" dir="rtl" style="flex:1;min-width:150px"><button class="btn pri sm" type="submit" id="dsub">${ic('plus', 15)}${t('common.add')}</button></form>
  <div class="foot"><button class="btn" id="dclose">${t('common.done')}</button></div>`);
  const close = m.close; m.close = () => { close(); done && done(); };
  const draw = async () => {
    const list = (await api('/api/departments')).departments;
    $('#dl', m).innerHTML = list.length ? `<div class="tscroll" style="max-height:320px"><table class="tbl"><tbody>${list.map(d => `<tr><td><b>${esc(d.name_en)}</b></td><td dir="rtl">${esc(d.name_ar)}</td><td class="mut" style="white-space:nowrap">${t('dept.employees', { n: d.employees })}</td><td style="text-align:end;white-space:nowrap"><button class="ib" data-e="${d.id}" title="${t('common.edit')}">${ic('edit', 15)}</button> <button class="ib d" data-d="${d.id}" title="${t('common.delete')}" ${d.employees ? 'disabled' : ''}>${ic('trash', 15)}</button></td></tr>`).join('')}</tbody></table></div>` : `<div class="empty" style="padding:18px">${t('dept.none')}</div>`;
    $$('[data-e]', m).forEach(b => b.onclick = () => { const d = list.find(x => x.id == b.dataset.e); editing = d.id; $('#dn_en', m).value = d.name_en; $('#dn_ar', m).value = d.name_ar; $('#dsub', m).innerHTML = ic('check', 15) + t('common.save'); $('#dn_en', m).focus(); });
    $$('[data-d]', m).forEach(b => b.onclick = async () => { try { await api('/api/departments/' + b.dataset.d, { method: 'DELETE' }); toast(t('toast.deleted')); draw(); } catch (e) { fail(e); } });
  };
  $('#dfm', m).onsubmit = async ev => {
    ev.preventDefault(); const body = { name_en: $('#dn_en', m).value, name_ar: $('#dn_ar', m).value };
    try {
      if (editing) await api('/api/departments/' + editing, { method: 'PUT', body }); else await api('/api/departments', { method: 'POST', body });
      editing = null; $('#dn_en', m).value = ''; $('#dn_ar', m).value = ''; $('#dsub', m).innerHTML = ic('plus', 15) + t('common.add'); toast(t('toast.saved')); draw();
    } catch (e) { fail(e); }
  };
  $('#dclose', m).onclick = () => m.close();
  draw().catch(fail);
}

/* ============ categories ============ */
async function pCategories(el) {
  pageHead(t('cat.title'), t('cat.sub'), `<button class="btn pri sm" id="addc">${ic('plus', 16)}${t('cat.add')}</button>`);
  const load = async () => {
    const list = await cats(true);
    el.innerHTML = list.length ? `<div class="card"><div class="tscroll"><table class="tbl"><thead><tr><th>${t('cat.code')}</th><th>${t('cat.name')}</th><th>${t('cat.fields')}</th><th>${t('rep.life')}</th><th>${t('nav.assets')}</th><th></th></tr></thead><tbody>${list.map(c => `<tr>
      <td class="mono"><b>${esc(c.code)}</b></td><td><b>${esc(nameOf(c))}</b>${c.description ? `<div class="mut" style="font-size:12.5px">${esc(c.description)}</div>` : ''}</td>
      <td>${c.fields.length ? c.fields.map(f => `<span class="badge mut" style="margin:2px">${esc(nameOf(f, 'label'))}</span>`).join('') : '<span class="mut">—</span>'}</td>
      <td>${c.useful_life_years ? esc(t('cat.years', { n: c.useful_life_years })) : '<span class="mut">—</span>'}</td><td>${c.assets}</td><td style="text-align:end;white-space:nowrap"><button class="ib" data-e="${c.id}" title="${t('common.edit')}">${ic('edit', 15)}</button> <button class="ib d" data-d="${c.id}" title="${c.assets ? esc(t('err.category_in_use')) : t('common.delete')}" ${c.assets ? 'disabled' : ''}>${ic('trash', 15)}</button></td></tr>`).join('')}</tbody></table></div></div>`
      : `<div class="card"><div class="empty">${ic('folder', 36)}<b>${t('cat.none')}</b>${t('cat.none_sub')}</div></div>`;
    $$('[data-e]', el).forEach(b => b.onclick = () => categoryForm(list.find(c => c.id == b.dataset.e), load));
    $$('[data-d]', el).forEach(b => b.onclick = async () => { const c = list.find(x => x.id == b.dataset.d); if (await confirmBox(t('cat.delete_q', { n: nameOf(c) }), t('roles.delete_text'), t('common.delete'))) { try { await api('/api/categories/' + c.id, { method: 'DELETE' }); toast(t('toast.deleted')); load(); } catch (e) { fail(e); } } });
  };
  $('#addc').onclick = () => categoryForm(null, load);
  await load();
}

function categoryForm(c, done) {
  const edit = !!c;
  const frow = (f = {}) => `<div class="frow" data-key="${esc(f.key || '')}">
    <input class="fl-en" placeholder="${t('cat.label_en')}" value="${esc(f.label_en || '')}" dir="ltr"><input class="fl-ar" placeholder="${t('cat.label_ar')}" value="${esc(f.label_ar || '')}" dir="rtl">
    <select class="fl-type">${['text', 'number', 'date', 'select', 'bool'].map(x => `<option value="${x}" ${(f.type || 'text') === x ? 'selected' : ''}>${t('ft.' + x)}</option>`).join('')}</select>
    <input class="fl-opts" placeholder="${t('cat.options_ph')}" value="${esc((f.options || []).join(', '))}" style="${f.type === 'select' ? '' : 'visibility:hidden'}">
    <label><input type="checkbox" class="fl-req" ${f.required ? 'checked' : ''}>${t('cat.required')}</label>
    <label class="fl-uq-l" title="${t('cat.unique_hint')}" style="${['text', 'number'].includes(f.type || 'text') ? '' : 'visibility:hidden'}"><input type="checkbox" class="fl-uq" ${f.unique ? 'checked' : ''}>${t('cat.unique')}</label>
    <button type="button" class="ib d fl-del" title="${t('common.remove')}">${ic('trash', 15)}</button></div>`;
  const m = modal(`<h2>${edit ? t('cat.edit') : t('cat.add')}</h2><div class="sub">${t('cat.add_sub')}</div><form id="ctf" novalidate><div class="fg">
    ${field('name_en', t('cat.name_en'), inp('name_en', edit ? c.name_en : '', 'dir="ltr"'), { req: true })}${field('name_ar', t('cat.name_ar'), inp('name_ar', edit ? c.name_ar : '', 'dir="rtl"'))}
    ${field('code', t('cat.code'), inp('code', edit ? c.code : '', 'dir="ltr" class="mono" maxlength="8" autocomplete="off" style="text-transform:uppercase"'), { req: true, hint: t('cat.code_hint') })}
    ${field('description', t('cat.desc'), inp('description', edit ? c.description : ''))}
    ${field('useful_life_years', t('cat.life'), inp('useful_life_years', edit && c.useful_life_years ? c.useful_life_years : '', 'type="number" min="0" max="100" step="1" dir="ltr"'), { hint: t('cat.life_hint') })}</div>
    <div class="sect"><h4>${ic('list', 14)}${t('cat.fields')}</h4><div class="mut" style="font-size:13px;margin:-4px 0 10px">${t('cat.fields_sub')}</div>
    <div class="fld" data-f="fields"><div id="frows">${(edit ? c.fields : []).map(frow).join('')}</div><div class="em"></div></div>
    <button type="button" class="btn sm" id="addf">${ic('plus', 15)}${t('cat.add_field')}</button></div>${footBtns()}</form>`, 'lg');
  const bindRows = () => $$('.frow', m).forEach(r => { $('.fl-type', r).onchange = e => { $('.fl-opts', r).style.visibility = e.target.value === 'select' ? '' : 'hidden'; $('.fl-uq-l', r).style.visibility = ['text', 'number'].includes(e.target.value) ? '' : 'hidden'; }; $('.fl-del', r).onclick = () => r.remove(); });
  bindRows();
  $('#addf', m).onclick = () => { $('#frows', m).insertAdjacentHTML('beforeend', frow()); bindRows(); $$('.frow .fl-en', m).pop().focus(); };
  let codeTouched = edit;
  $('#f-code', m).addEventListener('input', () => codeTouched = true);
  $('#f-name_en', m).addEventListener('input', e => { if (!codeTouched) $('#f-code', m).value = e.target.value.replace(/[^A-Za-z0-9]/g, '').slice(0, 3).toUpperCase(); });
  bindCancel(m);
  bindSubmit(m, $('#ctf', m), async () => {
    const body = { name_en: fv(m, 'name_en'), name_ar: fv(m, 'name_ar'), code: fv(m, 'code').toUpperCase(), description: fv(m, 'description'), useful_life_years: fv(m, 'useful_life_years') };
    body.fields = $$('.frow', m).map(r => ({ key: r.dataset.key || undefined, label_en: $('.fl-en', r).value.trim(), label_ar: $('.fl-ar', r).value.trim(), type: $('.fl-type', r).value, options: $('.fl-opts', r).value.split(/[,،]/).map(s => s.trim()).filter(Boolean), required: $('.fl-req', r).checked, unique: ['text', 'number'].includes($('.fl-type', r).value) && $('.fl-uq', r).checked }));
    if (edit) await api('/api/categories/' + c.id, { method: 'PUT', body }); else await api('/api/categories', { method: 'POST', body });
    toast(edit ? t('toast.saved') : t('cat.created')); m.close(); done && done();
  });
}

/* ============ phase 3: documents ============ */
const INLINE_MIME = ['application/pdf', 'image/png', 'image/jpeg', 'image/webp', 'image/gif'];
const fmtSize = n => n < 1024 ? n + ' B' : n < 1048576 ? (n / 1024).toFixed(0) + ' KB' : (n / 1048576).toFixed(1) + ' MB';
async function uploadFiles(entity, id, files) {
  let ok = 0;
  for (const f of files) {
    try { await api(`/api/documents?entity=${entity}&id=${id}`, { method: 'POST', raw: f, headers: { 'X-Filename': encodeURIComponent(f.name) } }); ok++; }
    catch (e) { fail(e, f.name); }
  }
  if (ok) toast(t('doc.uploaded', { n: ok }));
  return ok;
}
async function docsSection(box, entity, id, canManage) {
  const draw = async () => {
    const list = (await api(`/api/documents?entity=${entity}&id=${id}`)).documents;
    box.innerHTML = (list.length ? `<div class="docs">${list.map(d => `<div class="doc">${ic(d.mime.startsWith('image/') ? 'image' : 'file', 20)}<div class="grow"><a href="/api/documents/${d.id}/file${INLINE_MIME.includes(d.mime) ? '?inline=1' : ''}" target="_blank" rel="noopener">${esc(d.filename)}</a><small>${fmtSize(d.size)} · ${esc(fmtDate(d.created_at, true))}${d.uploaded_by_name ? ' · ' + esc(d.uploaded_by_name) : ''}</small></div><a class="ib" href="/api/documents/${d.id}/file" title="${t('doc.download')}">${ic('download', 15)}</a>${canManage ? `<button class="ib d" data-del="${d.id}" title="${t('common.delete')}">${ic('trash', 15)}</button>` : ''}</div>`).join('')}</div>` : `<div class="mut" style="padding:2px 0 10px">${t('doc.none')}</div>`)
      + (canManage ? `<div class="toolbar" style="margin:10px 0 0"><label class="btn sm">${ic('upload', 15)}${t('doc.upload')}<input type="file" hidden multiple accept=".pdf,.png,.jpg,.jpeg,.webp,.gif,.docx,.xlsx"></label><span class="mut" style="font-size:12.5px">${t('doc.types')}</span></div>` : '');
    $$('[data-del]', box).forEach(b => b.onclick = async () => { const d = list.find(x => x.id == b.dataset.del); if (await confirmBox(t('doc.delete_q', { n: d.filename }), t('roles.delete_text'), t('common.delete'))) { try { await api('/api/documents/' + d.id, { method: 'DELETE' }); toast(t('toast.deleted')); draw(); } catch (e) { fail(e); } } });
    const fi = $('input[type=file]', box); if (fi) fi.onchange = async () => { await uploadFiles(entity, id, [...fi.files]); draw().catch(fail); };
  };
  await draw().catch(e => { box.innerHTML = `<div class="mut">${esc(errText(e))}</div>`; });
}
const receiptLink = (gid, kind, label) => `<a href="#/receipt?id=${gid}&kind=${kind}" target="_blank" rel="noopener" class="mono" title="${t('rcpt.open')}">${ic('printer', 13)} ${esc(label || t('rcpt.' + kind))}</a>`;

/* ============ phase 3: Excel import / export ============ */
function exportFile(path, params = {}) { location.href = path + '?' + new URLSearchParams(Object.assign({ lang: LANG }, params)); }
/* Excel import. Any layout works: the app finds the header row, suggests which field each column holds (from common
   English/Arabic names and from earlier imports) and the person confirms or corrects it in the Match columns table. */
function importModal(kind, done) {
  let file = null, info = null, map = {}, sheet = 0, defCat = '', addPeople = true;
  const keyCol = kind === 'employees' ? 'emp_no' : 'tag';
  const m = modal(`<h2>${t('imp.title_' + kind)}</h2><div class="sub">${t('imp.sub')}</div>
    <div class="steps"><div class="step"><b>1</b><div class="grow">${t('imp.step1_any')}</div><a class="btn sm" href="/api/import/template?type=${kind}&lang=${LANG}">${ic('download', 15)}${t('imp.template')}</a></div>
    <div class="step"><b>2</b><div class="grow">${t('imp.step2')}<div class="mut mono" id="imp-fn" style="font-size:12.5px"></div></div><label class="btn sm pri">${ic('sheet', 15)}${t('imp.choose')}<input type="file" id="imp-file" hidden accept=".xlsx,.csv"></label></div>
    <div id="imp-map"></div>
    <div class="step"><b id="imp-n3">3</b><div class="grow"><label class="cb" style="min-height:0"><input type="checkbox" id="imp-upd"> ${t('imp.update_' + kind)}</label><div class="mut" style="font-size:12.5px">${t('imp.update_hint', { col: keyCol })}</div></div></div></div>
    <div id="imp-res"></div>
    <div class="foot"><button class="btn" data-x="cancel">${t('common.cancel')}</button><button class="btn" id="imp-check" disabled>${t('imp.check')}</button><button class="btn pri" id="imp-go" disabled>${t('imp.go')}</button></div>`, 'lg');
  const res = $('#imp-res', m), go = $('#imp-go', m), chk = $('#imp-check', m), box = $('#imp-map', m);
  const label = k => { const f = info && info.fields.find(x => x.key === k); return f ? nameOf(f, 'label') : k; };
  const missing = () => !info ? [] : info.fields.filter(f => f.required && !(f.key === 'category_code' && defCat) && !Object.values(map).includes(f.key)).map(f => f.key);
  const reset = () => { go.disabled = true; go.textContent = t('imp.go'); res.innerHTML = ''; chk.disabled = !file || !info || missing().length > 0; };
  const send = dry => api(`/api/import/${kind}?` + new URLSearchParams({ dry_run: dry ? 1 : 0, update: $('#imp-upd', m).checked ? 1 : 0, sheet, category: defCat, add_people: addPeople ? 1 : 0 }),
    { method: 'POST', raw: file, headers: { 'X-Filename': encodeURIComponent(file.name), 'X-Mapping': encodeURIComponent(JSON.stringify(map)) } });
  const banner = (cls, html) => `<div class="banner ${cls}" style="margin:16px 0 0">${ic(cls === 'good' ? 'check' : 'warn', 20)}<div class="grow">${html}</div></div>`;
  const show = r => {
    const ok = !r.error_count;
    res.innerHTML = banner(ok ? 'good' : 'bad', `<b>${ok ? t('imp.ready', { n: r.total }) : t('imp.has_errors', { n: r.error_count, total: r.total })}</b>${t('imp.summary', { c: r.created, u: r.updated })}`) + `
      ${r.departments_created && r.departments_created.length ? `<div class="mut" style="margin-top:10px">${t('imp.new_depts')}: <b>${esc(r.departments_created.join('، '))}</b></div>` : ''}
      ${r.employees_created && r.employees_created.length ? `<div class="mut" style="margin-top:10px">${esc(t('imp.new_people', { n: r.employees_created.length }))}: <b>${esc(r.employees_created.join('، '))}</b></div>` : ''}
      ${r.errors.length ? `<div class="tscroll" style="max-height:280px;margin-top:12px"><table class="tbl"><thead><tr><th>${t('imp.row')}</th><th>${t('imp.col')}</th><th>${t('imp.problem')}</th></tr></thead><tbody>${r.errors.map(e => `<tr><td class="mono">${e.row}</td><td>${esc(e.column ? label(e.column) : '—')}</td><td>${esc(errText(e))}</td></tr>`).join('')}</tbody></table></div>${r.error_count > r.errors.length ? `<div class="mut" style="margin-top:6px">${t('imp.more_errors', { n: r.error_count - r.errors.length })}</div>` : ''}` : ''}`;
  };
  const opts = cur => `<option value="">${esc(t('imp.skip'))}</option>` + info.fields.map(f => `<option value="${esc(f.key)}" ${f.key === cur ? 'selected' : ''}>${esc(nameOf(f, 'label'))}${f.required ? ' *' : ''}</option>`).join('');
  const drawMap = async () => {
    const cl = kind === 'assets' ? await cats() : [];
    const need = missing();
    box.innerHTML = `<div class="step mapstep"><b>${ic('list', 14)}</b><div class="grow">
      <div style="display:flex;gap:10px;align-items:flex-start;flex-wrap:wrap"><div style="flex:1;min-width:220px"><div><b>${t('imp.match_title')}</b></div><div class="mut" style="font-size:12.5px">${t('imp.match_sub')}</div></div>
      ${info.sheets.length > 1 ? `<label class="sortsel">${esc(t('imp.sheet'))}<select class="sel" id="imp-sheet">${info.sheets.map((n, i) => `<option value="${i}" ${i === sheet ? 'selected' : ''}>${esc(n || '#' + (i + 1))}</option>`).join('')}</select></label>` : ''}</div>
      <div class="mut" style="font-size:12.5px;margin:6px 0 8px">${esc(t('imp.header_at', { r: info.header_row, n: info.rows }))}</div>
      ${kind === 'assets' ? `<div class="fld" style="margin:0 0 10px;max-width:420px"><label for="imp-cat">${t('imp.cat_all')}</label><select id="imp-cat"><option value="">${esc(t('imp.cat_from_col'))}</option>${cl.map(c => `<option value="${esc(c.code)}" ${c.code === defCat ? 'selected' : ''}>${esc(nameOf(c))} (${esc(c.code)})</option>`).join('')}</select><div class="hint">${t('imp.cat_all_hint')}</div></div>` : ''}
      ${kind === 'assets' && (Object.values(map).includes('assigned_to') || Object.values(map).includes('holder_national_id')) ? `<div class="fld full" style="margin:0 0 10px"><label class="cb" style="min-height:0"><input type="checkbox" id="imp-people" ${addPeople ? 'checked' : ''}> ${t('imp.add_people')}</label><div class="hint">${t('imp.add_people_hint')}</div></div>` : ''}
      <div class="tscroll" style="max-height:340px"><table class="tbl maptbl"><thead><tr><th>${t('imp.col_file')}</th><th>${t('imp.examples')}</th><th>${t('imp.goes_to')}</th></tr></thead><tbody>
      ${info.columns.map(c => `<tr class="${map[c.index] ? '' : 'skipped'}"><td><b>${esc(c.header || '(' + t('imp.no_heading') + ')')}</b></td><td class="mut ex">${c.samples.length ? c.samples.map(esc).join(' · ') : '—'}</td>
        <td><select class="sel" data-col="${c.index}">${opts(map[c.index] || '')}</select></td></tr>`).join('')}</tbody></table></div>
      ${need.length ? `<div class="banner warn" style="margin:10px 0 0">${ic('warn', 18)}<div>${esc(t('imp.need', { f: need.map(label).join('، ') }))}</div></div>` : ''}</div></div>`;
    $('#imp-n3', m).textContent = '4';
    $$('select[data-col]', box).forEach(sel => sel.onchange = () => {
      const col = sel.dataset.col, v = sel.value;
      if (v) for (const k in map) if (k !== col && map[k] === v) map[k] = '';      // one column per field: the earlier one is skipped
      map[col] = v; drawMap().then(reset);
    });
    const cs = $('#imp-cat', box); if (cs) cs.onchange = () => { defCat = cs.value; drawMap().then(reset); };
    const ap = $('#imp-people', box); if (ap) ap.onchange = () => { addPeople = ap.checked; reset(); };
    const sh = $('#imp-sheet', box); if (sh) sh.onchange = () => { sheet = +sh.value; load(); };
  };
  const load = async () => {
    info = null; reset(); box.innerHTML = `<div class="skel" style="padding:12px">${t('common.loading')}</div>`;
    try {
      info = await api(`/api/import/${kind}/columns?sheet=${sheet}`, { method: 'POST', raw: file, headers: { 'X-Filename': encodeURIComponent(file.name) } });
      map = {}; info.columns.forEach(c => map[c.index] = c.suggested || '');
      await drawMap(); reset();
      if (!missing().length) chk.click();
    } catch (e) { box.innerHTML = banner('bad', esc(errText(e))); }
  };
  $('#imp-file', m).onchange = e => { file = e.target.files[0] || null; $('#imp-fn', m).textContent = file ? file.name : ''; sheet = 0; defCat = ''; if (file) load(); else { info = null; box.innerHTML = ''; reset(); } };
  $('#imp-upd', m).onchange = reset;
  chk.onclick = async () => {
    chk.disabled = true;
    try { const r = await send(true); show(r); go.disabled = !!r.error_count; if (!r.error_count) go.textContent = t('imp.go_n', { n: r.total }); }
    catch (e) { res.innerHTML = banner('bad', esc(errText(e)) + (e.columns ? ' <b>' + esc(e.columns.map(label).join('، ')) + '</b>' : '')); }
    chk.disabled = false;
  };
  go.onclick = async () => {
    go.disabled = true;
    try { const r = await send(false); if (r.committed) { toast(t('imp.done'), t('imp.summary', { c: r.created, u: r.updated })); m.close(); done && done(); } else { show(r); } }
    catch (e) { fail(e); go.disabled = false; }
  };
  bindCancel(m);
}

/* ============ phase 3: printable receipts ============ */
async function renderReceipt(seq) {
  const q = new URLSearchParams(location.hash.split('?')[1] || ''), kind = q.get('kind') === 'return' ? 'return' : 'handover';
  $('#root').innerHTML = `<div class="skel">${t('common.loading')}</div>`;
  let r;
  try { r = await api(`/api/assignments/${+q.get('id')}/receipt?kind=${kind}`); }
  catch (e) { $('#root').innerHTML = `<div class="wrap"><div class="banner bad">${ic('warn', 20)}<div class="grow">${esc(errText(e))}</div></div></div>`; return; }
  if (seq !== renderSeq) return;
  let RL = renderReceipt.lang || LANG, FREE = false;
  const draw = () => {
    const tr = (k, v) => { let s = DICT[RL][k] ?? DICT.en[k] ?? k; if (v) for (const x in v) s = s.split('{' + x + '}').join(v[x]); return s; };
    const nm = (o, b = 'name') => (RL === 'ar' ? (o[b + '_ar'] || o[b + '_en']) : (o[b + '_en'] || o[b + '_ar'])) || '';
    const dt = (iso, time) => { if (!iso) return '—'; const d = new Date(iso.length === 10 ? iso + 'T00:00:00Z' : iso); return d.toLocaleString(RL === 'ar' ? 'ar-u-nu-latn' : 'en-GB', time ? { dateStyle: 'long', timeStyle: 'short' } : { dateStyle: 'long', timeZone: 'UTC' }); };
    const a = r.asset, e = r.employee, g = r.assignment, c = r.company, ho = kind === 'handover';
    const row = (k, v) => v === '' || v === null || v === undefined ? '' : `<tr><th>${esc(k)}</th><td>${v}</td></tr>`;
    const cf = a.fields.map(f => { const v = a.custom[f.key]; if (v === undefined || v === '' || v === false) return ''; return row(nm(f, 'label'), esc(f.type === 'bool' ? tr('common.yes') : f.type === 'date' ? dt(v) : v)); }).join('');
    const terms = (RL === 'ar' ? c.terms_ar || c.terms_en : c.terms_en || c.terms_ar) || tr('rcpt.terms_default_' + kind);
    const nid = e.national_id ? `<span class="mono" dir="ltr">${esc(e.national_id)}</span>` : '<span class="rblank"></span>';
    const brand = S.brand && S.brand.logo ? `<img src="${esc(S.brand.logo)}" alt="">` : `<div class="rl">${esc((nm(c) || 'A').charAt(0))}</div>`;
    $('#root').innerHTML = `<div class="rbar noprint"><button class="btn pri sm" id="r-print">${ic('printer', 15)}${t('rcpt.print')}</button>
      <div class="seg" id="r-lang"><button data-l="ar" class="${RL === 'ar' ? 'on' : ''}">العربية</button><button data-l="en" class="${RL === 'en' ? 'on' : ''}">English</button></div>
      <button class="btn sm ${FREE ? 'pri' : ''}" id="r-free" aria-pressed="${FREE}">${ic('edit', 15)}${t(FREE ? 'rcpt.free_done' : 'rcpt.free')}</button>
      ${has('assignments.manage') ? `<label class="btn sm">${ic('upload', 15)}${t('rcpt.attach')}<input type="file" id="r-file" hidden accept=".pdf,.png,.jpg,.jpeg,.webp"></label>` : ''}
      <div class="sp"></div><span class="mut" style="font-size:12.5px">${t('rcpt.print_hint')}</span></div>
      ${FREE ? `<div class="rbar noprint" style="padding-top:0"><div class="banner info" style="margin:0;flex:1">${ic('edit', 18)}<div class="grow">${esc(t('rcpt.free_hint'))}</div></div></div>` : ''}
      ${r.signed_copies.length ? `<div class="rbar noprint" style="padding-top:0">${ic('check', 16)} ${t('rcpt.signed')}: ${r.signed_copies.map(d => `<a href="/api/documents/${d.id}/file?inline=1" target="_blank" rel="noopener">${esc(d.filename)}</a>`).join(' · ')}</div>` : ''}
      <div class="rcpt${FREE ? ' editing' : ''}" dir="${RL === 'ar' ? 'rtl' : 'ltr'}" lang="${RL}" ${FREE ? 'contenteditable="true" spellcheck="false"' : ''}>
        <div class="rhead"><div class="rbrand">${brand}<div><b>${esc(nm(c))}</b></div></div><div class="rtitle"><h1>${tr('rcpt.title_' + kind)}</h1><div class="mono">${esc(r.number || '—')}</div><div>${esc(dt(ho ? g.assigned_at : g.returned_at, true))}</div></div></div>
        <h3>${tr('rcpt.employee')}</h3><table class="rt">${row(tr('emp.name'), esc(nm(e, 'full_name')))}${row(tr('emp.no'), `<span class="mono">${esc(e.emp_no)}</span>`)}${row(tr('emp.national_id'), nid)}${row(tr('emp.department'), e.dept_en ? esc(nm(e, 'dept')) : '')}${row(tr('emp.job'), esc(e.job_title))}</table>
        <h3>${tr('rcpt.asset')}</h3><table class="rt">${row(tr('assets.tag'), `<span class="mono">${esc(a.tag)}</span>`)}${row(tr('assets.name'), esc(a.name))}${row(tr('assets.category'), esc(nm(a, 'cat')))}${row(tr('assets.brand') + ' / ' + tr('assets.model'), esc([a.brand, a.model].filter(Boolean).join(' / ')))}${row(tr('assets.serial'), a.serial_no ? `<span class="mono">${esc(a.serial_no)}</span>` : '')}${cf}
          ${row(tr(ho ? 'asg.condition_out' : 'asg.condition_in'), esc(tr('cond.' + (ho ? g.condition_out : g.condition_in))))}${ho ? row(tr('asg.expected_return'), g.expected_return ? esc(dt(g.expected_return)) : '') : row(tr('asg.assigned_on'), esc(dt(g.assigned_at)))}${row(tr('asg.notes'), esc(ho ? g.notes_out : g.notes_in))}</table>
        <h3>${tr('rcpt.terms')}</h3><div class="rterms">${esc(terms)}</div>
        <div class="rsig"><div><div class="lbl">${tr(ho ? 'rcpt.sig_received_emp' : 'rcpt.sig_returned_emp')}</div><b>${esc(nm(e, 'full_name'))}</b><div class="lbl rnid">${tr('emp.national_id')}: ${nid}</div><div class="line"></div><div class="lbl">${tr('rcpt.signature')} / ${tr('rcpt.date')}</div></div>
          <div><div class="lbl">${tr(ho ? 'rcpt.sig_handed_by' : 'rcpt.sig_received_by')}</div><b class="rname">${tr('rcpt.name')}: <span class="rblank"></span></b><div class="lbl rnid" aria-hidden="true" style="visibility:hidden">&nbsp;</div><div class="line"></div><div class="lbl">${tr('rcpt.signature')} / ${tr('rcpt.date')}</div></div></div>
        <div class="rfoot"><span class="mono">${esc(r.number || '')}</span><span>${esc(tr('rcpt.printed', { d: dt(new Date().toISOString(), true) }))}</span></div>
      </div>`;
    document.title = (r.number || '') + ' — ' + appName();
    $('#r-print').onclick = () => window.print();
    $$('#r-lang button').forEach(b => b.onclick = () => { RL = renderReceipt.lang = b.dataset.l; draw(); });
    // "Edit before printing": any text can be changed for this one print; nothing is saved
    $('#r-free').onclick = () => { FREE = !FREE; draw(); if (FREE) { const h = $('.rcpt h1'); if (h) h.focus(); } };
    const fi = $('#r-file'); if (fi) fi.onchange = async () => { if (await uploadFiles('assignment', g.id, [...fi.files])) { r = await api(`/api/assignments/${g.id}/receipt?kind=${kind}`); draw(); } };
  };
  draw();
}

/* ============ phase 4: charts ============ */
const ST_SLOT = { in_stock: 1, assigned: 2, maintenance: 3, retired: 4, lost: 5 };     // colour follows the status, never its rank
const nfmt = n => Number(n || 0).toLocaleString(loc(), { maximumFractionDigits: 1 });
let VTIP = null;
function tipShow(ev, title, rows) {           // rows: [[value, label, slot|null]] - built with textContent (labels are data)
  if (!VTIP) { VTIP = document.createElement('div'); VTIP.className = 'vtip viz'; document.body.appendChild(VTIP); }
  VTIP.replaceChildren();
  const tt = document.createElement('div'); tt.className = 't'; tt.textContent = title; VTIP.appendChild(tt);
  rows.forEach(([v, lbl, slot]) => {
    const r = document.createElement('div'); r.className = 'r';
    if (slot) { const k = document.createElement('i'); k.style.background = `var(--s${slot})`; r.appendChild(k); }
    const b = document.createElement('b'); b.textContent = v; const s = document.createElement('span'); s.textContent = lbl;
    r.append(b, s); VTIP.appendChild(r);
  });
  VTIP.style.display = 'block';
  let x, y;
  if (ev.type === 'focus' || ev.clientX === undefined) { const rc = ev.target.getBoundingClientRect(); x = rc.left + rc.width / 2; y = rc.top; }
  else { x = ev.clientX; y = ev.clientY; }
  const w = VTIP.offsetWidth, h = VTIP.offsetHeight;
  VTIP.style.left = Math.max(8, Math.min(innerWidth - w - 8, x + 14)) + 'px';
  VTIP.style.top = Math.max(8, y - h - 12) + 'px';
}
const tipHide = () => { if (VTIP) VTIP.style.display = 'none'; };
function hoverable(el, fn) { el.addEventListener('pointermove', ev => fn(ev)); el.addEventListener('focus', ev => fn(ev)); el.addEventListener('pointerleave', tipHide); el.addEventListener('blur', tipHide); }

/* a chart card with a Chart / Table toggle; the table is the accessible twin of every chart */
function vizCard(box, title, sub, drawChart, tableHTML) {
  let asTable = false;
  const paint = () => {
    box.innerHTML = `<div class="vhead"><div><h3>${esc(title)}</h3><div class="sub">${esc(sub)}</div></div><button class="vtoggle noprint">${asTable ? t('viz.chart') : t('viz.table')}</button></div><div class="vbody viz"></div>`;
    const body = $('.vbody', box);
    if (asTable) body.innerHTML = tableHTML(); else drawChart(body);
    $('.vtoggle', box).onclick = () => { asTable = !asTable; tipHide(); paint(); };
  };
  paint();
}
const miniTable = (heads, rows) => `<div class="tscroll"><table class="tbl"><thead><tr>${heads.map((h, i) => `<th class="${i ? 'num' : ''}">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${r.map((c, i) => `<td class="${i ? 'num' : ''}">${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;

/* tall segmented bar: one whole split into <= 6 parts; share printed inside only where it fits */
function segBar(body, parts) {
  const total = parts.reduce((s, p) => s + p.value, 0);
  if (!total) { body.innerHTML = `<div class="vempty">${t('viz.no_data')}</div>`; return; }
  const pct = v => Math.round(v / total * 100) + '%';
  body.innerHTML = `<div class="segbar" role="img" aria-label="${esc(parts.filter(p => p.value).map(p => `${p.label}: ${p.value} (${pct(p.value)})`).join(', '))}">${parts.filter(p => p.value).map((p, i) => `<div class="sb s${p.slot}" tabindex="0" data-i="${i}" style="flex:${p.value} 1 0;background:var(--s${p.slot})"><span>${pct(p.value)}</span></div>`).join('')}</div>
    <div class="legend">${parts.filter(p => p.value).map(p => `<span><i style="background:var(--s${p.slot})"></i>${esc(p.label)} · ${nfmt(p.value)}</span>`).join('')}</div>`;
  const shown = parts.filter(p => p.value);
  $$('.sb', body).forEach(b => {
    const p = shown[+b.dataset.i];
    hoverable(b, ev => tipShow(ev, p.label, [[nfmt(p.value), pct(p.value), p.slot]]));
  });
  requestAnimationFrame(() => $$('.sb', body).forEach(b => { const s = b.firstElementChild; if (s.offsetWidth + 14 > b.clientWidth) s.classList.add('hide'); }));
}

/* ranked horizontal bars, one hue; the tail past 8 folds into "Other" */
function hBars(body, items, fmt = nfmt) {
  if (!items.length) { body.innerHTML = `<div class="vempty">${t('viz.no_data')}</div>`; return; }
  let list = items.slice().sort((a, b) => b.value - a.value);
  if (list.length > 8) { const rest = list.slice(7); list = list.slice(0, 7).concat([{ label: t('viz.other'), value: rest.reduce((s, x) => s + x.value, 0), n: rest.length }]); }
  const max = Math.max(...list.map(x => x.value)) || 1;
  body.innerHTML = `<div class="hb">${list.map((x, i) => `<div class="nm" title="${esc(x.label)}">${esc(x.label)}</div><div class="tr" tabindex="0" data-i="${i}"><div class="bar" style="width:${(x.value / max * 100).toFixed(2)}%"></div><span class="v">${esc(fmt(x.value))}</span></div>`).join('')}</div>`;
  $$('.tr', body).forEach(tr => { const x = list[+tr.dataset.i]; hoverable(tr, ev => tipShow(ev, x.label, [[fmt(x.value), x.n ? t('viz.n_more', { n: x.n }) : '', 1]])); });
}

/* line chart over months: 2px lines, ringed end dots, crosshair snapping to the nearest month, one tooltip for every series */
function lineChart(body, labels, series) {
  // drawn at the card's real pixel width (1 unit = 1px) so text stays 11px and the height stays fixed; redrawn on resize
  const W = Math.max(300, Math.round(body.clientWidth || 640)), H = 240, L = 40, R = 14, T = 14, B = 30, pw = W - L - R, ph = H - T - B;
  if (!body._ro && window.ResizeObserver) {
    let lastW = W;
    body._ro = new ResizeObserver(debounce(() => { const w = Math.round(body.clientWidth); if (body.isConnected && $('svg.lc', body) && Math.abs(w - lastW) > 8) { lastW = w; lineChart(body, labels, series); } }, 150));
    body._ro.observe(body);
  }
  const maxV = Math.max(1, ...series.flatMap(s => s.values));
  const step = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000].find(s => maxV / s <= 4) || Math.ceil(maxV / 4);
  const top = Math.ceil(maxV / step) * step, ticks = [];
  for (let v = 0; v <= top; v += step) ticks.push(v);
  const X = i => L + (labels.length === 1 ? pw / 2 : i * pw / (labels.length - 1)), Y = v => T + ph - v / top * ph;
  const path = vals => vals.map((v, i) => (i ? 'L' : 'M') + X(i).toFixed(1) + ' ' + Y(v).toFixed(1)).join(' ');
  const last = labels.length - 1;
  body.innerHTML = `<div class="legend" style="margin:0 0 8px">${series.map(s => `<span><i class="ln" style="background:var(--s${s.slot})"></i>${esc(s.name)}</span>`).join('')}</div>
  <svg class="lc" viewBox="0 0 ${W} ${H}" dir="ltr" tabindex="0" role="img" aria-label="${esc(series.map(s => s.name + ': ' + s.values.reduce((a, b) => a + b, 0)).join(', '))}">
    ${ticks.map(v => `<line class="${v ? 'grid' : 'base'}" x1="${L}" x2="${W - R}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${L - 8}" y="${Y(v) + 4}" text-anchor="end">${nfmt(v)}</text>`).join('')}
    ${labels.map((lb, i) => (pw / labels.length >= 44 || i % 2 === last % 2) ? `<text x="${X(i)}" y="${H - 9}" text-anchor="middle">${esc(lb)}</text>` : '').join('')}
    <line class="xh" y1="${T}" y2="${T + ph}" x1="-10" x2="-10" visibility="hidden"/>
    ${series.map(s => `<path class="ln" d="${path(s.values)}" style="stroke:var(--s${s.slot})"/><circle class="dot" r="4" cx="${X(last)}" cy="${Y(s.values[last])}" style="fill:var(--s${s.slot})"/>`).join('')}
    ${series.map((s, k) => `<circle class="dot hd" data-k="${k}" r="4" visibility="hidden" style="fill:var(--s${s.slot})"/>`).join('')}
    <rect x="${L}" y="${T}" width="${pw}" height="${ph}" fill="transparent"/></svg>`;
  const svg = $('svg', body), xh = $('.xh', svg), hd = $$('.hd', svg);
  let cur = last;
  const show = (i, ev) => {
    cur = i; xh.setAttribute('x1', X(i)); xh.setAttribute('x2', X(i)); xh.setAttribute('visibility', 'visible');
    hd.forEach((c, k) => { c.setAttribute('cx', X(i)); c.setAttribute('cy', Y(series[k].values[i])); c.setAttribute('visibility', 'visible'); });
    const rc = svg.getBoundingClientRect();
    tipShow(ev && ev.clientX !== undefined ? ev : { clientX: rc.left + X(i) / W * rc.width, clientY: rc.top + Y(Math.max(...series.map(s => s.values[i]))) / H * rc.height, type: 'pointermove' },
      labels[i], series.map(s => [nfmt(s.values[i]), s.name, s.slot]));
  };
  const hide = () => { xh.setAttribute('visibility', 'hidden'); hd.forEach(c => c.setAttribute('visibility', 'hidden')); tipHide(); };
  svg.addEventListener('pointermove', ev => { const rc = svg.getBoundingClientRect(); const x = (ev.clientX - rc.left) / rc.width * W; show(Math.max(0, Math.min(last, Math.round((x - L) / pw * last))), ev); });
  svg.addEventListener('pointerleave', hide); svg.addEventListener('blur', hide);
  svg.addEventListener('focus', () => show(cur));
  svg.addEventListener('keydown', ev => { if (ev.key === 'ArrowLeft' || ev.key === 'ArrowRight') { ev.preventDefault(); show(Math.max(0, Math.min(last, cur + (ev.key === 'ArrowRight' ? 1 : -1)))); } });
}

async function dashCharts(el) {
  const a = await api('/api/analytics');
  const st = (S.dashAssets || {}).by_status || {};
  const parts = STATUSES.map(s => ({ label: t('st.' + s), value: st[s] || 0, slot: ST_SLOT[s] }));
  const months = a.monthly.map(m => new Date(m.month + '-01T00:00:00Z').toLocaleDateString(loc(), { month: 'short', timeZone: 'UTC' }));
  const monthsLong = a.monthly.map(m => new Date(m.month + '-01T00:00:00Z').toLocaleDateString(loc(), { month: 'long', year: 'numeric', timeZone: 'UTC' }));
  el.innerHTML = `<div class="card s12" id="v-st"></div><div class="card s6" id="v-cat"></div><div class="card s6" id="v-dep"></div><div class="card s12" id="v-mo"></div>`;
  vizCard($('#v-st', el), t('viz.status_title'), t('viz.status_sub'), b => segBar(b, parts),
    () => miniTable([t('assets.status'), t('rep.count'), '%'], parts.map(p => [p.label, nfmt(p.value), (parts.reduce((s, x) => s + x.value, 0) ? Math.round(p.value / parts.reduce((s, x) => s + x.value, 0) * 100) : 0) + '%'])));
  const cats = a.by_category.map(c => ({ label: nameOf(c), value: c.count, cost: c.value }));
  vizCard($('#v-cat', el), t('viz.cat_title'), t('viz.cat_sub'), b => hBars(b, cats),
    () => miniTable([t('assets.category'), t('rep.count'), t('rep.cost')], cats.map(c => [c.label, nfmt(c.value), money(c.cost)])));
  const deps = a.by_department.map(d => ({ label: d.id ? nameOf(d) : t('viz.no_dept'), value: d.count }));
  vizCard($('#v-dep', el), t('viz.dep_title'), t('viz.dep_sub'), b => hBars(b, deps),
    () => miniTable([t('emp.department'), t('rep.assets_held')], deps.map(d => [d.label, nfmt(d.value)])));
  const series = [{ name: t('viz.handovers'), slot: 1, values: a.monthly.map(m => m.handovers) }, { name: t('viz.returns'), slot: 2, values: a.monthly.map(m => m.returns) }];
  vizCard($('#v-mo', el), t('viz.mo_title'), t('viz.mo_sub'), b => lineChart(b, months, series),
    () => miniTable([t('rep.month'), t('viz.handovers'), t('viz.returns')], a.monthly.map((m, i) => [monthsLong[i], nfmt(m.handovers), nfmt(m.returns)])));
}

/* ============ phase 4: reports ============ */
const REPORTS = ['holdings', 'overdue', 'warranty', 'activity', 'value', 'maintenance'];
let RP = { name: 'holdings', p: {} };
function repCell(c, r) {
  const v = r[c.key];
  switch (c.type) {
    case 'name': { const s = nameOf(r, c.key); return s ? esc(s) : '<span class="mut">—</span>'; }
    case 'mono': return v ? `<span class="mono">${esc(v)}</span>` : '<span class="mut">—</span>';
    case 'date': return v ? esc(fmtDate(v.slice(0, 10))) : '<span class="mut">—</span>';
    case 'datetime': return v ? esc(fmtDate(v, true)) : '—';
    case 'money': return v === null || v === undefined ? '<span class="mut">—</span>' : esc(money(v));
    case 'int': case 'num': return v === null || v === undefined ? '<span class="mut">—</span>' : esc(nfmt(v));
    case 'status': return stBadge(v);
    case 'condition': return v ? esc(t('cond.' + v)) : '—';
    case 'event': return `<span class="badge ${v === 'return' ? 'good' : 'info'}">${esc(t('rcpt.' + v))}</span>`;
    case 'mkind': return esc(t('mnt.k_' + v));
    case 'mstatus': return `<span class="badge ${M_CLS[v] || 'mut'}">${esc(t('mnt.s_' + v))}</span>`;
    default: return v === '' || v === null || v === undefined ? '<span class="mut">—</span>' : esc(v);
  }
}
const isNum = c => ['money', 'int', 'num'].includes(c.type);
function repTable(rep, clickable) {
  if (!rep.rows.length) return `<div class="empty">${ic('check', 30)}<b>${t('rep.empty')}</b></div>`;
  const tot = rep.totals || {}, hasTot = rep.columns.some(c => c.key in tot);
  return `<div class="tscroll"><table class="tbl"><thead><tr>${rep.columns.map(c => `<th class="${isNum(c) ? 'num' : ''}">${esc(t(c.label))}</th>`).join('')}</tr></thead>
    <tbody>${rep.rows.map((r, i) => `<tr class="${clickable && r.asset_id ? 'click' : ''}" data-i="${i}">${rep.columns.map(c => `<td class="${isNum(c) ? 'num' : ''}">${repCell(c, r)}</td>`).join('')}</tr>`).join('')}</tbody>
    ${hasTot ? `<tfoot><tr>${rep.columns.map((c, i) => `<td class="${isNum(c) ? 'num' : ''}">${i === 0 ? esc(t('rep.total')) + (c.key in tot ? ': ' + esc(nfmt(tot[c.key])) : '') : c.key in tot ? (c.type === 'money' ? esc(money(tot[c.key])) : esc(nfmt(tot[c.key]))) : ''}</td>`).join('')}</tr></tfoot>` : ''}</table></div>`;
}
async function pReports(el) {
  pageHead(t('rep.title'), t('rep.sub'));
  const [cl, dl] = await Promise.all([has('assets.view') ? cats(true) : [], has('employees.view') ? api('/api/departments').then(r => r.departments) : []]);
  el.innerHTML = `<div class="grid g12"><div class="card s4 rplist"><h3>${t('rep.list')}</h3><div class="sub">${t('rep.list_sub')}</div><div class="rolelist" id="rl"></div></div><div class="card s8" id="rv"></div></div>`;
  const REPS = REPORTS.filter(n => n !== 'maintenance' || has('maintenance.view'));
  const drawList = () => { $('#rl').innerHTML = REPS.map(n => `<div class="role ${n === RP.name ? 'on' : ''}" data-n="${n}">${ic({ holdings: 'idcard', overdue: 'warn', warranty: 'shield', activity: 'swap', value: 'chart', maintenance: 'tool' }[n], 20)}<div style="flex:1"><b>${t('rep.' + n)}</b><small>${t('rep.' + n + '_sub')}</small></div></div>`).join(''); $$('#rl .role').forEach(d => d.onclick = () => { RP = { name: d.dataset.n, p: {} }; drawList(); drawReport(); }); };
  const filters = () => {
    const p = RP.p;
    switch (RP.name) {
      case 'holdings': return dl.length ? `<select class="sel" data-p="department"><option value="">${t('emp.all_depts')}</option>${dl.map(d => `<option value="${d.id}" ${p.department == d.id ? 'selected' : ''}>${esc(nameOf(d))}</option>`).join('')}</select>` : '';
      case 'warranty': return `<select class="sel" data-p="days">${[30, 60, 90, 180, 365].map(n => `<option value="${n}" ${(p.days || '60') == n ? 'selected' : ''}>${t('rep.next_days', { n })}</option>`).join('')}</select><label class="cb" style="min-height:0;display:flex;gap:8px;align-items:center;font-weight:600"><input type="checkbox" data-p="expired" ${p.expired === '1' ? 'checked' : ''}>${t('rep.include_expired')}</label>`;
      case 'activity': case 'maintenance': return (RP.name === 'maintenance' ? `<select class="sel" data-p="status"><option value="">${t('mnt.f_all')}</option>${['scheduled', 'open', 'done', 'cancelled'].map(s => `<option value="${s}" ${p.status === s ? 'selected' : ''}>${esc(t('mnt.s_' + s))}</option>`).join('')}</select>` : '') + `<select class="sel" data-x="preset">${[['7', t('rep.last_n', { n: 7 })], ['30', t('rep.last_n', { n: 30 })], ['90', t('rep.last_n', { n: 90 })], ['month', t('rep.this_month')], ['year', t('rep.this_year')], ['custom', t('rep.custom')]].map(([v, l]) => `<option value="${v}" ${(p.preset || '30') === v ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select><input class="inp" type="date" data-p="from" value="${esc(p.from || '')}" style="max-width:170px"><input class="inp" type="date" data-p="to" value="${esc(p.to || '')}" style="max-width:170px">`;
      case 'value': return `${cl.length ? `<select class="sel" data-p="category"><option value="">${t('assets.all_cat')}</option>${cl.map(c => `<option value="${c.id}" ${p.category == c.id ? 'selected' : ''}>${esc(nameOf(c))}</option>`).join('')}</select>` : ''}<label class="cb" style="min-height:0;display:flex;gap:8px;align-items:center;font-weight:600"><input type="checkbox" data-p="disposed" ${p.disposed === '1' ? 'checked' : ''}>${t('rep.include_disposed')}</label>`;
      default: return '';
    }
  };
  const params = () => { const o = {}; for (const k in RP.p) if (k !== 'preset' && RP.p[k] !== '' && RP.p[k] !== undefined) o[k] = RP.p[k]; return o; };
  const drawReport = async () => {
    const box = $('#rv');
    if ((RP.name === 'activity' || RP.name === 'maintenance') && !RP.p.from) setPreset(RP.p.preset || (RP.name === 'maintenance' ? '90' : '30'));
    box.innerHTML = `<div class="vhead"><div><h3>${t('rep.' + RP.name)}</h3><div class="sub">${t('rep.' + RP.name + '_sub')}</div></div></div>
      <div class="toolbar noprint">${filters()}<div class="sp"></div><button class="btn sm" id="rx">${ic('download', 15)}${t('imp.export')}</button><button class="btn sm" id="rpr">${ic('printer', 15)}${t('rep.print')}</button></div><div id="rbody"><div class="skel">${t('common.loading')}</div></div>`;
    $$('[data-p]', box).forEach(i => i.onchange = () => { RP.p[i.dataset.p] = i.type === 'checkbox' ? (i.checked ? '1' : '') : i.value; if ((RP.name === 'activity' || RP.name === 'maintenance') && (i.dataset.p === 'from' || i.dataset.p === 'to')) RP.p.preset = 'custom'; drawReport(); });
    const pr = $('[data-x="preset"]', box); if (pr) pr.onchange = () => { setPreset(pr.value); drawReport(); };
    $('#rx').onclick = () => exportFile('/api/reports/' + RP.name, Object.assign({ format: 'xlsx' }, params()));
    $('#rpr').onclick = () => window.print();
    const body = $('#rbody');
    let rep;
    try { rep = await api('/api/reports/' + RP.name + '?' + new URLSearchParams(params())); } catch (e) { body.innerHTML = `<div class="banner bad">${ic('warn', 20)}<div class="grow">${esc(errText(e))}</div></div>`; return; }
    if (!$('#rbody') || body !== $('#rbody')) return;
    const chips = [];
    if (RP.name === 'maintenance') chips.push(`<span class="badge info">${t('mnt.total_cost')}: ${esc(money(rep.totals.cost))}</span>`);
    if (RP.name === 'activity') chips.push(`<span class="badge info">${t('viz.handovers')}: ${nfmt(rep.totals.handover)}</span>`, `<span class="badge good">${t('viz.returns')}: ${nfmt(rep.totals.return)}</span>`);
    if (RP.name === 'value') chips.push(`<span class="badge mut">${t('rep.as_of', { d: fmtDate(rep.as_of) })}</span>`, `<span class="badge info">${t('rep.cost')}: ${esc(money(rep.totals.cost))}</span>`, `<span class="badge good">${t('rep.book')}: ${esc(money(rep.totals.book))}</span>`);
    body.innerHTML = (rep.truncated ? `<div class="banner warn">${ic('warn', 18)}<div class="grow">${t('rep.truncated', { n: nfmt(rep.rows.length), total: nfmt(rep.truncated) })}</div></div>` : '')
      + (chips.length ? `<div class="rtot">${chips.join('')}</div>` : '')
      + (rep.summary && rep.summary.rows.length ? `<h4 class="mut" style="margin:6px 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.5px">${t('rep.summary')}</h4>${repTable(rep.summary, false)}<h4 class="mut" style="margin:18px 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.5px">${t('rep.details')}</h4>` : '')
      + repTable(rep, has('assets.view'))
      + (RP.name === 'value' ? `<div class="mut" style="font-size:12.5px;margin-top:10px">${t('rep.value_note')}</div>` : '');
    $$('#rbody tbody tr.click').forEach(tr => tr.onclick = () => assetDetail(rep.rows[+tr.dataset.i].asset_id, drawReport));
  };
  const setPreset = v => {
    const d = new Date(), iso = x => x.toISOString().slice(0, 10), p = RP.p;
    p.preset = v;
    if (v === 'custom') return;
    p.to = iso(d);
    if (v === 'month') p.from = iso(new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), 1)));
    else if (v === 'year') p.from = iso(new Date(Date.UTC(d.getUTCFullYear(), 0, 1)));
    else p.from = iso(new Date(d.getTime() - (+v) * 86400000));
  };
  drawList(); drawReport();
}

/* ============ phase 6: alerts bell ============ */
const ALERT_SEV = { critical: 'bad', warning: 'warn', info: 'info' };
function alertLine(it) {
  const who = nameOf(it, 'who');
  switch (it.kind) {
    case 'overdue': return t('alert.overdue', { tag: it.tag, name: it.name, who, days: it.days });
    case 'warranty': return t('alert.warranty', { tag: it.tag, name: it.name, days: it.days });
    case 'maintenance': return t(it.days < 0 ? 'alert.maintenance_late' : 'alert.maintenance', { tag: it.tag, title: it.title, days: Math.abs(it.days) });
    case 'request': return t('alert.request', { who });
    case 'access': return t('alert.access', { who });
    default: return t('alert.decided_' + it.status, { who });
  }
}
async function refreshBell() {
  const c = $('#bellc'); if (!c || !S.user) return;
  try { const a = await api('/api/alerts'); S.alerts = a; c.textContent = a.total > 99 ? '99+' : a.total; c.hidden = !a.total; c.className = 'bdg ' + (a.items.some(i => i.severity === 'critical') ? 'crit' : ''); } catch (e) { }
}
function openBell(ev) {
  ev.stopPropagation();
  const wrap = $('#bellwrap'), ex = $('.pop', wrap); if (ex) { ex.remove(); return; }
  const a = S.alerts || { items: [], total: 0 };
  wrap.insertAdjacentHTML('beforeend', `<div class="pop alerts"><div class="who alhead"><div style="flex:1"><b>${t('alert.title')}</b><small>${a.total ? t('alert.count', { n: a.total }) : t('alert.none')}</small></div>${a.items.length ? `<button class="btn sm" id="al-clear">${ic('check', 14)}${t('alert.clear_all')}</button>` : ''}</div>
    ${a.items.map((it, i) => `<div class="alrow"><button class="algo" data-i="${i}"><span class="badge ${ALERT_SEV[it.severity]}" style="padding:2px 8px">${esc(t('alert.k_' + it.kind))}</span><span class="al">${esc(alertLine(it))}</span></button><button class="alx" data-x="${i}" title="${esc(t('alert.dismiss'))}" aria-label="${esc(t('alert.dismiss'))}">${ic('x', 15)}</button></div>`).join('')}
    ${a.total > a.items.length ? `<div class="mut" style="padding:8px 12px;font-size:12px">${t('alert.more', { n: a.total - a.items.length })}</div>` : ''}
    ${a.hidden ? `<div class="alfoot"><span class="mut">${esc(t('alert.hidden', { n: a.hidden }))}</span><button class="lnk" id="al-restore">${t('alert.restore')}</button></div>` : ''}</div>`);
  const pop = $('.pop.alerts', wrap);
  const apply = r => { S.alerts = r; const c = $('#bellc'); if (c) { c.textContent = r.total > 99 ? '99+' : r.total; c.hidden = !r.total; c.className = 'bdg ' + (r.items.some(i => i.severity === 'critical') ? 'crit' : ''); } pop.remove(); openBell({ stopPropagation() { } }); };
  const send = async (url, body) => { try { apply(await api(url, { method: 'POST', body })); } catch (e) { fail(e); } };
  $$('.alx', pop).forEach(b => b.onclick = ev => { ev.stopPropagation(); send('/api/alerts/dismiss', { keys: [a.items[+b.dataset.x].key] }); });
  const clr = $('#al-clear', pop); if (clr) clr.onclick = ev => { ev.stopPropagation(); send('/api/alerts/dismiss', { keys: a.items.map(i => i.key) }); };
  const rst = $('#al-restore', pop); if (rst) rst.onclick = ev => { ev.stopPropagation(); send('/api/alerts/restore', {}); };
  $$('.pop.alerts .algo', wrap).forEach(b => b.onclick = () => {
    const it = a.items[+b.dataset.i]; $('.pop', wrap).remove();
    if (it.kind === 'request' || it.kind === 'decided') go('#/requests');
    else if (it.kind === 'access') go('#/users');
    else if (it.kind === 'maintenance') go('#/maintenance');
    else assetDetail(it.asset_id, () => { refreshBell(); if (curPage() === 'assets' || curPage() === 'assignments') render(); });
  });
  if (!openBell.outside) { openBell.outside = true; document.addEventListener('click', e => { const p = $('.pop.alerts'); if (p && !p.contains(e.target) && !e.target.closest('#t-bell')) p.remove(); }); }
}

/* ============ phase 6: QR labels & scanning ============ */
async function openScanned() {
  const tag = new URLSearchParams(location.hash.split('?')[1] || '').get('tag') || '';
  try { const r = await api('/api/assets/by-tag?tag=' + encodeURIComponent(tag)); history.replaceState(null, '', '#/assets'); await render(); assetDetail(r.id, () => render()); }
  catch (e) { history.replaceState(null, '', '#/assets'); await render(); toast(t('scan.not_found'), tag, 'err'); }
}
/* camera QR scanner (phones): reads an asset label and opens that asset. Uses the browser's built-in BarcodeDetector
   (Android Chrome/Edge); elsewhere the person can type the tag, or scan with the phone's own camera app. */
function tagFromScan(raw) {
  const s = String(raw || '').trim();
  const m = s.match(/#\/scan\?(?:.*&)?tag=([^&#]+)/);
  if (m) { try { return decodeURIComponent(m[1]).toUpperCase(); } catch (e) { return ''; } }
  return /^[A-Za-z0-9][A-Za-z0-9\-_/.]{0,39}$/.test(s) ? s.toUpperCase() : '';
}
async function openAssetByTag(tag) {
  try { const r = await api('/api/assets/by-tag?tag=' + encodeURIComponent(tag)); if (curPage() !== 'assets') { history.replaceState(null, '', '#/assets'); await render(); } assetDetail(r.id, () => render()); return true; }
  catch (e) { toast(t('scan.not_found'), tag, 'err'); return false; }
}
function openScanner() {
  const m = modal(`<h2>${ic('qr', 20)} ${t('scan.title')}</h2><div class="sub">${t('scan.sub')}</div>
    <div class="scanbox" id="scbox" hidden><video id="scv" playsinline muted autoplay></video><div class="scanframe" aria-hidden="true"></div></div>
    <div id="scmsg" class="banner warn" style="margin:12px 0 0" hidden></div>
    <form id="scf" novalidate style="margin-top:14px"><div class="fld" data-f="tag"><label for="f-sctag">${t('scan.type_tag')}</label>
    <div style="display:flex;gap:8px"><input id="f-sctag" dir="ltr" class="mono" autocomplete="off" autocapitalize="characters" placeholder="LAP-00001" style="flex:1"><button class="btn pri" type="submit">${t('scan.open')}</button></div><div class="em"></div></div></form>
    <div class="foot"><button class="btn" type="button" id="scclose">${t('common.close')}</button></div>`, 'sm');
  let stream = null, timer = null, busy = false;
  const stop = () => { if (timer) clearInterval(timer); timer = null; if (stream) stream.getTracks().forEach(tr => tr.stop()); stream = null; };
  const close = m.close; m.close = () => { stop(); close(); };
  const msg = (text, kind = 'warn') => { const b = $('#scmsg', m); b.className = 'banner ' + kind; b.innerHTML = `${ic('warn', 18)}<div>${esc(text)}</div>`; b.hidden = false; };
  $('#scclose', m).onclick = () => m.close();
  const openFound = async id => { m.close(); if (curPage() !== 'assets') { history.replaceState(null, '', '#/assets'); await render(); } assetDetail(id, () => render()); };
  // a code nobody has: offer to add the asset with it (as serial number, or as the asset tag if it looks like one)
  const unknown = code => {
    $('#scbox', m).hidden = true;
    const asTag = /^[A-Za-z0-9][A-Za-z0-9\-_/.]{0,39}$/.test(code), canAdd = has('assets.manage');
    const b = $('#scmsg', m); b.className = 'banner info'; b.hidden = false;
    b.innerHTML = `${ic('qr', 18)}<div class="grow"><b>${esc(t('scan.unknown'))}</b><div class="mono" dir="ltr" style="word-break:break-all;margin:4px 0 10px">${esc(code)}</div>
      ${canAdd ? `<div style="display:flex;gap:8px;flex-wrap:wrap"><button type="button" class="btn pri sm" id="sc-add-sn">${ic('plus', 15)}${t('scan.add_serial')}</button>${asTag ? `<button type="button" class="btn sm" id="sc-add-tag">${t('scan.add_tag')}</button>` : ''}</div>` : `<div>${esc(t('scan.ask_admin'))}</div>`}
      <button type="button" class="btn sm" id="sc-again" style="margin-top:8px">${ic('qr', 15)}${t('scan.again')}</button></div>`;
    const add = preset => { m.close(); if (curPage() !== 'assets') go('#/assets'); assetForm(null, () => render(), preset); };
    const sn = $('#sc-add-sn', m); if (sn) sn.onclick = () => add({ serial_no: code.slice(0, 80) });
    const tg = $('#sc-add-tag', m); if (tg) tg.onclick = () => add({ tag: code.toUpperCase() });
    $('#sc-again', m).onclick = () => { b.hidden = true; busy = false; startCam(); };
  };
  const found = async raw => {
    const s = String(raw || '').trim();
    if (busy || !s) return;
    busy = true; stop(); if (navigator.vibrate) navigator.vibrate(60);
    const ours = /#\/scan\?/.test(s) ? tagFromScan(s) : '';                     // a label printed by this system
    if (ours) { m.close(); await openAssetByTag(ours); return; }
    try { const r = await api('/api/assets/by-code?code=' + encodeURIComponent(s)); await openFound(r.id); }  // tag, serial, IMEI...
    catch (e) { if (e && e.status === 404) unknown(s); else { busy = false; fail(e); } }
  };
  $('#scf', m).onsubmit = e => { e.preventDefault(); const v = $('#f-sctag', m).value; busy = false; if (v.trim()) found(v); };
  const startCam = async () => {
    if (!window.isSecureContext || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { msg(t('scan.need_https')); return; }
    if (!('BarcodeDetector' in window)) { msg(t('scan.no_detector')); return; }
    try {
      const want = ['qr_code', 'code_128', 'code_39', 'data_matrix', 'ean_13', 'ean_8', 'upc_a', 'itf'];   // QR labels + serial/IMEI barcodes
      const have = window.BarcodeDetector.getSupportedFormats ? await window.BarcodeDetector.getSupportedFormats() : ['qr_code'];
      const det = new window.BarcodeDetector({ formats: want.filter(f => have.includes(f)) });
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false });
      if (!m.isConnected) { stop(); return; }
      const v = $('#scv', m); v.srcObject = stream; $('#scbox', m).hidden = false; await v.play().catch(() => { });
      $('#f-sctag', m).blur();
      timer = setInterval(async () => {
        if (busy || v.readyState < 2) return;
        try { const codes = await det.detect(v); if (codes && codes.length) found(codes[0].rawValue); } catch (e) { }
      }, 250);
    } catch (e) { msg(e && e.name === 'NotAllowedError' ? t('scan.denied') : t('scan.no_camera')); }
  };
  startCam();
}
/* "Install app" (Android Chrome/Edge offer it once the site qualifies; iPhone: Share -> Add to Home Screen) */
window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault(); S.installEvt = e;
  const anchor = $('#t-scan') || $('#bellwrap');
  if (anchor && !$('#t-install')) {
    anchor.insertAdjacentHTML('beforebegin', `<button class="chip" id="t-install" title="${t('pwa.install')}">${ic('download', 17)}<span class="hide-sm">${t('pwa.install')}</span></button>`);
    $('#t-install').onclick = installApp;
  }
});
window.addEventListener('appinstalled', () => { S.installEvt = null; const b = $('#t-install'); if (b) b.remove(); toast(t('pwa.installed')); });
async function installApp() {
  const e = S.installEvt; if (!e) return;
  S.installEvt = null; e.prompt();
  try { await e.userChoice; } catch (x) { }
  const b = $('#t-install'); if (b) b.remove();
}
const labelUrl = (base, tag) => base.replace(/\/+$/, '') + '/#/scan?tag=' + encodeURIComponent(tag);
async function renderLabels(seq) {
  const ids = new URLSearchParams(location.hash.split('?')[1] || '').get('ids') || '';
  $('#root').innerHTML = `<div class="skel">${t('common.loading')}</div>`;
  let r;
  try { r = await api('/api/labels?ids=' + encodeURIComponent(ids)); } catch (e) { $('#root').innerHTML = `<div class="wrap"><div class="banner bad">${ic('warn', 20)}<div class="grow">${esc(errText(e))}</div></div></div>`; return; }
  if (seq !== renderSeq) return;
  let base = (() => { try { return localStorage.getItem('am_label_base'); } catch (e) { return null; } })() || r.public_url || location.origin;
  let size = (() => { try { return localStorage.getItem('am_label_size'); } catch (e) { return null; } })() || 'm';
  const draw = () => {
    const local = /\/\/(localhost|127\.|\[::1\])/.test(base);
    $('#root').innerHTML = `<div class="rbar noprint" style="max-width:1000px"><button class="btn pri sm" id="l-print">${ic('printer', 15)}${t('rcpt.print')}</button>
      <div class="seg" id="l-size">${['s', 'm', 'l'].map(s => `<button data-s="${s}" class="${size === s ? 'on' : ''}">${t('lbl.size_' + s)}</button>`).join('')}</div>
      <label class="mut" style="font-size:12.5px;display:flex;gap:8px;align-items:center">${t('lbl.base')} <input class="inp" id="l-base" value="${esc(base)}" dir="ltr" style="max-width:300px;min-height:36px"></label>
      <div class="sp"></div><span class="mut" style="font-size:12.5px">${t('lbl.count', { n: r.assets.length })}</span></div>
      ${local ? `<div class="rbar noprint" style="max-width:1000px;padding-top:0"><div class="banner warn" style="margin:0;flex:1">${ic('warn', 18)}<div class="grow">${t('lbl.local_warn')}</div></div></div>` : ''}
      <div class="labels sz-${size}">${r.assets.map(a => `<div class="lbl">${QR.svg(labelUrl(base, a.tag))}<div class="lt"><small>${esc(companyName())}</small><b class="mono">${esc(a.tag)}</b><span>${esc(a.name)}</span>${a.serial_no ? `<small class="mono">S/N ${esc(a.serial_no)}</small>` : ''}</div></div>`).join('')}</div>`;
    document.title = t('lbl.title') + ' — ' + appName();
    $('#l-print').onclick = () => window.print();
    $$('#l-size button').forEach(b => b.onclick = () => { size = b.dataset.s; try { localStorage.setItem('am_label_size', size); } catch (e) { } draw(); });
    $('#l-base').onchange = e => { base = e.target.value.trim() || location.origin; try { localStorage.setItem('am_label_base', base); } catch (x) { } draw(); };
  };
  draw();
}
const openLabels = ids => window.open('#/labels?ids=' + ids.join(','), '_blank', 'noopener');

/* ============ phase 6: pickers ============ */
function assetPicker(m, fieldId, onPick, filter = '') {
  let last = [], chosen = null;
  const box = $(`[data-f="${fieldId}"]`, m), input = $('input', box), list = $('.pick', box);
  const draw = () => {
    list.innerHTML = last.length ? last.map(a => `<button type="button" data-id="${a.id}" class="${chosen && chosen.id === a.id ? 'on' : ''}"><div style="flex:1"><b class="mono">${esc(a.tag)}</b> ${esc(a.name)}<div><small>${esc(nameOf(a, 'cat'))} · ${esc(t('st.' + a.status))}</small></div></div>${chosen && chosen.id === a.id ? ic('check', 16) : ''}</button>`).join('') : `<div class="empty" style="padding:14px">${t('common.no_results')}</div>`;
    $$('button', list).forEach(b => b.onclick = () => { chosen = last.find(x => x.id == b.dataset.id); draw(); onPick(chosen); });
  };
  const search = async () => { try { last = (await api('/api/assets?' + new URLSearchParams({ q: input.value.trim(), per_page: 8, status: filter }))).assets; draw(); } catch (e) { fail(e); } };
  input.addEventListener('input', debounce(search, 200)); search();
  return () => chosen;
}

/* ============ phase 6: maintenance ============ */
const M_CLS = { scheduled: 'warn', open: 'info', done: 'good', cancelled: 'mut' };
const mBadge = r => r.overdue ? `<span class="badge bad">${t('mnt.overdue')}</span>` : `<span class="badge ${M_CLS[r.status]}">${esc(t('mnt.s_' + r.status))}</span>`;
let MN = { status: 'active', q: '' };
async function pMaintenance(el) {
  const manage = has('maintenance.manage');
  pageHead(t('mnt.title'), t('mnt.sub'), manage ? `<button class="btn pri sm" id="addm">${ic('plus', 16)}${t('mnt.add')}</button>` : '');
  const mDate = r => r.status === 'scheduled' ? r.scheduled_for : (r.completed_at || r.started_at || r.created_at);
  const MS = { urgent: null, date_new: by(mDate, true), date_old: by(mDate), cost_high: by(r => r.cost, true), tag: by(r => r.tag) };
  let msort = sortPref('maintenance', 'urgent', Object.keys(MS));
  el.innerHTML = `<div class="card"><div class="toolbar"><input class="inp" id="mq" style="max-width:300px" placeholder="${t('mnt.search')}" value="${esc(MN.q)}">
    <select class="sel" id="mst">${['active', 'scheduled', 'open', 'done', 'cancelled', ''].map(s => `<option value="${s}" ${MN.status === s ? 'selected' : ''}>${t(s ? 'mnt.f_' + s : 'mnt.f_all')}</option>`).join('')}</select>
    ${sortSel('msort', Object.keys(MS), msort)}<div class="sp"></div><span class="badge mut" id="mcount"></span></div><div id="mtbl"><div class="skel">${t('common.loading')}</div></div></div>`;
  const load = async () => {
    MN.q = $('#mq').value.trim(); MN.status = $('#mst').value;
    const list = sortRows((await api('/api/maintenance?' + new URLSearchParams({ status: MN.status, q: MN.q }))).maintenance, MS[msort]);
    if (!$('#mtbl')) return;
    $('#mcount').textContent = list.length;
    $('#mtbl').innerHTML = list.length ? `<div class="tscroll"><table class="tbl"><thead><tr><th>${t('assets.status')}</th><th>${t('assets.asset')}</th><th>${t('mnt.kind')}</th><th>${t('mnt.title_f')}</th><th>${t('rep.date')}</th><th class="num">${t('mnt.cost')}</th><th></th></tr></thead><tbody>${list.map(r => `<tr class="click" data-a="${r.asset_id}">
      <td>${mBadge(r)}</td><td><span class="mono"><b>${esc(r.tag)}</b></span><div style="font-size:13px">${esc(r.asset_name)}</div></td><td>${esc(t('mnt.k_' + r.kind))}</td>
      <td><b>${esc(r.title)}</b>${r.vendor ? `<div class="mut" style="font-size:12.5px">${esc(r.vendor)}</div>` : ''}</td>
      <td style="white-space:nowrap">${esc(fmtDate(r.status === 'scheduled' ? r.scheduled_for : (r.completed_at || r.started_at || r.created_at)))}</td>
      <td class="num">${r.cost !== null ? esc(money(r.cost)) : '<span class="mut">—</span>'}</td>
      <td style="text-align:end;white-space:nowrap">${manage ? mActions(r) : ''}</td></tr>`).join('')}</tbody></table></div>`
      : `<div class="empty">${ic('tool', 36)}<b>${t('mnt.none')}</b>${t('mnt.none_sub')}</div>`;
    bindMActions($('#mtbl'), list, load);
    $$('#mtbl tr.click').forEach(tr => tr.onclick = ev => { if (ev.target.closest('button')) return; assetDetail(+tr.dataset.a, load); });
  };
  $('#mq').addEventListener('input', debounce(() => load().catch(fail), 250)); $('#mst').onchange = () => load().catch(fail);
  $('#msort').onchange = () => { msort = $('#msort').value; sortSave('maintenance', msort); load().catch(fail); };
  const add = $('#addm'); if (add) add.onclick = () => maintenanceForm(null, null, load);
  await load();
}
const mActions = r => r.status === 'scheduled' ? `<button class="btn sm" data-ma="start" data-id="${r.id}">${t('mnt.start')}</button> <button class="ib" data-ma="edit" data-id="${r.id}" title="${t('common.edit')}">${ic('edit', 15)}</button> <button class="ib d" data-ma="cancel" data-id="${r.id}" title="${t('mnt.cancel')}">${ic('x', 15)}</button>`
  : r.status === 'open' ? `<button class="btn sm pri" data-ma="complete" data-id="${r.id}">${t('mnt.complete')}</button> <button class="ib" data-ma="edit" data-id="${r.id}" title="${t('common.edit')}">${ic('edit', 15)}</button> <button class="ib d" data-ma="cancel" data-id="${r.id}" title="${t('mnt.cancel')}">${ic('x', 15)}</button>`
  : `<button class="ib" data-ma="edit" data-id="${r.id}" title="${t('common.edit')}">${ic('edit', 15)}</button>`;
function bindMActions(root, list, done) {
  $$('[data-ma]', root).forEach(b => b.onclick = async ev => {
    ev.stopPropagation(); const r = list.find(x => x.id == b.dataset.id);
    if (b.dataset.ma === 'edit') return maintenanceForm(r, null, done);
    if (b.dataset.ma === 'complete') return completeForm(r, done);
    if (b.dataset.ma === 'start') return startForm(r, done);
    if (await confirmBox(t('mnt.cancel_q'), r.title, t('mnt.cancel'))) { try { await api(`/api/maintenance/${r.id}/cancel`, { method: 'POST', body: {} }); toast(t('toast.saved')); done(); refreshBell(); } catch (e) { fail(e); } }
  });
}
function maintenanceForm(r, asset, done) {
  const edit = !!r;
  const m = modal(`<h2>${edit ? t('mnt.edit') : t('mnt.add')}</h2><div class="sub">${edit ? `<span class="mono">${esc(r.tag)}</span> · ${esc(r.asset_name)}` : asset ? `<span class="mono">${esc(asset.tag)}</span> · ${esc(asset.name)}` : t('mnt.add_sub')}</div><form id="mf" novalidate><div class="fg">
    ${!edit && !asset ? `<div class="fld full" data-f="asset_id"><label>${t('assets.asset')}<span class="req">*</span></label><input autocomplete="off" placeholder="${t('assets.search')}"><div class="pick"></div><div class="em"></div></div>` : ''}
    ${field('kind', t('mnt.kind'), dd('kind', ['repair', 'service', 'inspection', 'upgrade', 'other'].map(k => `<option value="${k}" ${(edit ? r.kind : 'repair') === k ? 'selected' : ''}>${esc(t('mnt.k_' + k))}</option>`).join('')))}
    ${field('title', t('mnt.title_f'), inp('title', edit ? r.title : ''), { req: true })}
    ${!edit || r.status === 'scheduled' ? field('scheduled_for', t('mnt.when'), inp('scheduled_for', edit ? r.scheduled_for : '', `type="date"`), { hint: t('mnt.when_hint') }) : ''}
    ${field('vendor', t('mnt.vendor'), inp('vendor', edit ? r.vendor : ''))}
    ${field('cost', t('mnt.cost'), inp('cost', edit && r.cost !== null ? r.cost : '', 'type="number" step="0.01" min="0" dir="ltr"'))}
    ${!edit ? `<div class="fld" id="oos-wrap"><label>&nbsp;</label><label class="cb"><input type="checkbox" id="f-oos" checked> ${t('mnt.out_of_service')}</label><div class="hint">${t('mnt.oos_hint')}</div></div>` : ''}
    ${field('description', t('mnt.description'), txa('description', edit ? r.description : ''), { full: true })}
    ${edit && r.status === 'done' ? field('resolution', t('mnt.resolution'), txa('resolution', r.resolution), { full: true }) : ''}</div>${footBtns()}</form>`, 'lg');
  const picked = !edit && !asset ? assetPicker(m, 'asset_id', () => { }) : null;
  bindCancel(m);
  bindSubmit(m, $('#mf', m), async () => {
    const body = { kind: fv(m, 'kind'), title: fv(m, 'title'), vendor: fv(m, 'vendor'), cost: fv(m, 'cost'), description: fv(m, 'description') };
    if ($('#f-scheduled_for', m)) body.scheduled_for = fv(m, 'scheduled_for');
    if ($('#f-resolution', m)) body.resolution = fv(m, 'resolution');
    if (edit) { await api('/api/maintenance/' + r.id, { method: 'PUT', body }); }
    else {
      const a = asset || (picked && picked());
      if (!a) throw { field: 'asset_id', code: 'pick_asset' };
      body.asset_id = a.id; body.out_of_service = $('#f-oos', m).checked;
      await api('/api/maintenance', { method: 'POST', body });
    }
    toast(t('toast.saved')); m.close(); done && done(); refreshBell();
  });
}
function startForm(r, done) {
  const m = modal(`<h2>${t('mnt.start')}</h2><div class="sub"><span class="mono">${esc(r.tag)}</span> · ${esc(r.title)}</div><form id="sf2" novalidate>
    <label class="cb"><input type="checkbox" id="f-oos" ${r.asset_status === 'in_stock' ? 'checked' : 'disabled'}> ${t('mnt.out_of_service')}</label><div class="hint mut" style="font-size:12.5px">${t('mnt.oos_hint')}</div>${footBtns(t('mnt.start'))}</form>`, 'sm');
  bindCancel(m);
  bindSubmit(m, $('#sf2', m), async () => { await api(`/api/maintenance/${r.id}/start`, { method: 'POST', body: { out_of_service: $('#f-oos', m).checked } }); toast(t('toast.saved')); m.close(); done && done(); refreshBell(); });
}
function completeForm(r, done) {
  const m = modal(`<h2>${t('mnt.complete')}</h2><div class="sub"><span class="mono">${esc(r.tag)}</span> · ${esc(r.title)}</div><form id="cf3" novalidate><div class="fg">
    ${field('cost', t('mnt.cost'), inp('cost', r.cost !== null ? r.cost : '', 'type="number" step="0.01" min="0" dir="ltr"'))}
    ${r.took_out_of_service ? field('condition', t('mnt.condition_after'), dd('condition', condOpts('good'))) : '<div></div>'}
    ${field('resolution', t('mnt.resolution'), txa('resolution'), { full: true })}</div>
    ${r.took_out_of_service ? `<div class="mut" style="font-size:12.5px;margin-top:10px">${t('mnt.back_hint')}</div>` : ''}${footBtns(t('mnt.complete'))}</form>`);
  bindCancel(m);
  bindSubmit(m, $('#cf3', m), async () => {
    const body = { cost: fv(m, 'cost'), resolution: fv(m, 'resolution') }; if ($('#f-condition', m)) body.condition = fv(m, 'condition');
    await api(`/api/maintenance/${r.id}/complete`, { method: 'POST', body }); toast(t('mnt.completed')); m.close(); done && done(); refreshBell();
  });
}
async function maintenanceSection(box, a, onChange) {
  const manage = has('maintenance.manage');
  const draw = async () => {
    const list = (await api('/api/maintenance?asset=' + a.id)).maintenance;
    box.innerHTML = (list.length ? `<div class="tscroll"><table class="tbl"><tbody>${list.map(r => `<tr><td>${mBadge(r)}</td><td><b>${esc(r.title)}</b><div class="mut" style="font-size:12.5px">${esc(t('mnt.k_' + r.kind))}${r.vendor ? ' · ' + esc(r.vendor) : ''}</div></td><td style="white-space:nowrap">${esc(fmtDate(r.status === 'scheduled' ? r.scheduled_for : (r.completed_at || r.started_at || r.created_at)))}</td><td class="num">${r.cost !== null ? esc(money(r.cost)) : ''}</td><td style="text-align:end;white-space:nowrap">${manage ? mActions(r) : ''}</td></tr>`).join('')}</tbody></table></div>` : `<div class="mut" style="padding:2px 0 10px">${t('mnt.none_asset')}</div>`)
      + (manage && !['retired', 'lost'].includes(a.status) ? `<div class="toolbar" style="margin:10px 0 0"><button class="btn sm" id="m-add">${ic('tool', 15)}${t('mnt.add')}</button></div>` : '');
    bindMActions(box, list, onChange);
    const b = $('#m-add', box); if (b) b.onclick = () => maintenanceForm(null, a, onChange);
  };
  await draw().catch(e => { box.innerHTML = `<div class="mut">${esc(errText(e))}</div>`; });
}

/* ============ phase 6: asset requests ============ */
const R_CLS = { pending: 'warn', fulfilled: 'good', rejected: 'bad', cancelled: 'mut' };
let RQ = { status: 'pending' };
async function pRequests(el) {
  const approve = has('requests.approve'), create = has('requests.create');
  pageHead(t('req.title'), approve ? t('req.sub_approver') : t('req.sub_requester'), create ? `<button class="btn pri sm" id="addq">${ic('plus', 16)}${t('req.add')}</button>` : '');
  el.innerHTML = `<div class="card"><div class="toolbar"><div class="seg" id="qst">${['pending', 'fulfilled', 'rejected', ''].map(s => `<button data-s="${s}" class="${RQ.status === s ? 'on' : ''}">${t(s ? 'req.s_' + s : 'req.all')}</button>`).join('')}</div><div class="sp"></div><span class="badge mut" id="qcount"></span></div><div id="qtbl"><div class="skel">${t('common.loading')}</div></div></div>`;
  const load = async () => {
    const list = (await api('/api/requests?status=' + RQ.status)).requests;
    if (!$('#qtbl')) return;
    $('#qcount').textContent = list.length;
    $('#qtbl').innerHTML = list.length ? `<div class="tscroll"><table class="tbl"><thead><tr><th>${t('req.employee')}</th><th>${t('assets.category')}</th><th>${t('req.reason')}</th><th>${t('req.needed_by')}</th><th>${t('assets.status')}</th><th>${t('req.requested_by')}</th><th></th></tr></thead><tbody>${list.map(r => `<tr>
      <td><b>${esc(nameOf(r, 'full_name'))}</b><div class="mut mono" style="font-size:12px">${esc(r.emp_no)}${r.dept_en ? ' · ' + esc(nameOf(r, 'dept')) : ''}</div></td>
      <td>${r.category_id ? esc(nameOf(r, 'cat')) : `<span class="mut">${t('req.any')}</span>`}${r.status === 'pending' ? `<div class="mut" style="font-size:12px">${t('req.available', { n: r.available })}</div>` : ''}</td>
      <td style="max-width:260px">${esc(r.reason)}${r.decision_note ? `<div class="mut" style="font-size:12.5px">↳ ${esc(r.decision_note)}</div>` : ''}</td>
      <td style="white-space:nowrap">${r.needed_by ? esc(fmtDate(r.needed_by)) : '—'}</td>
      <td><span class="badge ${R_CLS[r.status]}">${esc(t('req.s_' + r.status))}</span>${r.asset_tag ? `<div class="mono" style="font-size:12px;margin-top:4px">${esc(r.asset_tag)}</div>` : ''}</td>
      <td><span class="mono" style="font-size:12.5px">${esc(r.requested_by_name || '')}</span><div class="mut" style="font-size:12px">${esc(fmtDate(r.requested_at))}</div></td>
      <td style="text-align:end;white-space:nowrap">${r.status === 'pending' ? `${approve ? `<button class="btn sm pri" data-qa="approve" data-id="${r.id}">${t('req.approve')}</button> <button class="btn sm" data-qa="reject" data-id="${r.id}">${t('req.reject')}</button>` : ''} ${approve || r.requested_by === S.user.id ? `<button class="ib d" data-qa="cancel" data-id="${r.id}" title="${t('req.cancel')}">${ic('x', 15)}</button>` : ''}` : ''}</td></tr>`).join('')}</tbody></table></div>`
      : `<div class="empty">${ic('inbox', 36)}<b>${t('req.none')}</b>${create ? t('req.none_sub') : ''}</div>`;
    $$('[data-qa]', $('#qtbl')).forEach(b => b.onclick = async () => {
      const r = list.find(x => x.id == b.dataset.id);
      if (b.dataset.qa === 'approve') return approveForm(r, load);
      if (b.dataset.qa === 'reject') return rejectForm(r, load);
      if (await confirmBox(t('req.cancel_q'), nameOf(r, 'full_name'), t('req.cancel'))) { try { await api(`/api/requests/${r.id}/cancel`, { method: 'POST', body: {} }); toast(t('toast.saved')); load(); refreshBell(); } catch (e) { fail(e); } }
    });
  };
  $$('#qst button').forEach(b => b.onclick = () => { RQ.status = b.dataset.s; $$('#qst button').forEach(x => x.classList.toggle('on', x === b)); load().catch(fail); });
  const add = $('#addq'); if (add) add.onclick = () => requestForm(load);
  await load();
}
async function requestForm(done) {
  const cl = await cats(true);
  let chosen = null, last = [];
  const m = modal(`<h2>${t('req.add')}</h2><div class="sub">${t('req.add_sub')}</div><form id="qf" novalidate><div class="fg">
    <div class="fld full" data-f="employee_id"><label for="f-emp">${t('req.employee')}<span class="req">*</span></label><input id="f-emp" autocomplete="off" placeholder="${t('asg.find_employee')}"><div class="pick" id="pick"></div><div class="em"></div></div>
    ${field('category_id', t('assets.category'), dd('category_id', `<option value="">${t('req.any')}</option>` + cl.map(c => `<option value="${c.id}">${esc(nameOf(c))}</option>`).join('')))}
    ${field('needed_by', t('req.needed_by'), inp('needed_by', '', `type="date" min="${today()}"`))}
    ${field('reason', t('req.reason'), txa('reason'), { full: true, req: true })}</div>${footBtns(t('req.send'))}</form>`);
  const draw = () => { $('#pick', m).innerHTML = last.length ? last.map(e => `<button type="button" data-id="${e.id}" class="${chosen && chosen.id === e.id ? 'on' : ''}"><div style="flex:1"><b>${esc(nameOf(e, 'full_name'))}</b> <small class="mono">${esc(e.emp_no)}</small></div>${chosen && chosen.id === e.id ? ic('check', 16) : ''}</button>`).join('') : `<div class="empty" style="padding:14px">${t('asg.no_employees')}</div>`; $$('#pick button', m).forEach(b => b.onclick = () => { chosen = last.find(e => e.id == b.dataset.id); draw(); }); };
  const search = async () => { try { last = (await api('/api/employees/lookup?q=' + encodeURIComponent($('#f-emp', m).value.trim()))).employees; chosen = null; draw(); } catch (e) { fail(e); } };
  $('#f-emp', m).addEventListener('input', debounce(search, 200)); search(); bindCancel(m);
  bindSubmit(m, $('#qf', m), async () => {
    if (!chosen) throw { field: 'employee_id', code: 'pick_employee' };
    await api('/api/requests', { method: 'POST', body: { employee_id: chosen.id, category_id: +fv(m, 'category_id') || null, needed_by: fv(m, 'needed_by'), reason: fv(m, 'reason') } });
    toast(t('req.sent')); m.close(); done && done(); refreshBell();
  });
}
async function approveForm(r, done) {
  let cands;
  try { cands = (await api(`/api/requests/${r.id}/candidates`)).assets; } catch (e) { return fail(e); }
  let chosen = null;
  const m = modal(`<h2>${t('req.approve_title')}</h2><div class="sub">${esc(nameOf(r, 'full_name'))} · ${r.category_id ? esc(nameOf(r, 'cat')) : t('req.any')}</div><form id="af2" novalidate>
    <div class="fld" data-f="asset_id"><label>${t('req.pick_asset')}<span class="req">*</span></label><div class="pick" id="cands" style="max-height:280px">${cands.length ? cands.map(a => `<button type="button" data-id="${a.id}"><div style="flex:1"><b class="mono">${esc(a.tag)}</b> ${esc(a.name)}<div><small>${esc([a.brand, a.model].filter(Boolean).join(' '))}${a.location ? ' · ' + esc(a.location) : ''} · ${esc(t('cond.' + a.condition))}</small></div></div></button>`).join('') : `<div class="empty" style="padding:14px">${t('req.no_stock')}</div>`}</div><div class="em"></div></div>
    <div class="fg" style="margin-top:14px">${field('expected_return', t('asg.expected_return'), inp('expected_return', '', `type="date" min="${today()}"`))}${field('note', t('req.note'), inp('note'))}</div>${footBtns(t('req.approve_assign'))}</form>`);
  $$('#cands button', m).forEach(b => b.onclick = () => { chosen = cands.find(a => a.id == b.dataset.id); $$('#cands button', m).forEach(x => x.classList.toggle('on', x === b)); });
  bindCancel(m);
  bindSubmit(m, $('#af2', m), async () => {
    if (!chosen) throw { field: 'asset_id', code: 'pick_asset' };
    await api(`/api/requests/${r.id}/approve`, { method: 'POST', body: { asset_id: chosen.id, expected_return: fv(m, 'expected_return'), note: fv(m, 'note') } });
    toast(t('req.approved'), chosen.tag); m.close(); done && done(); refreshBell();
  });
}
function rejectForm(r, done) {
  const m = modal(`<h2>${t('req.reject_title')}</h2><div class="sub">${esc(nameOf(r, 'full_name'))}</div><form id="rf2" novalidate>${field('note', t('req.reject_reason'), txa('note'), { req: true })}${footBtns(t('req.reject'))}</form>`, 'sm');
  bindCancel(m);
  bindSubmit(m, $('#rf2', m), async () => { await api(`/api/requests/${r.id}/reject`, { method: 'POST', body: { note: fv(m, 'note') } }); toast(t('req.rejected')); m.close(); done && done(); refreshBell(); });
}

/* ============ phase 6: alert & e-mail settings (Company page) ============ */
async function settingsCard(box) {
  const manage = has('company.manage');
  let s;
  try { s = await api('/api/settings'); } catch (e) { box.remove(); return; }
  const dis = manage ? '' : ' disabled';
  box.innerHTML = `<h3>${ic('bell', 16)} ${t('set.title')}</h3><div class="sub">${t('set.sub')}</div><form id="setf" novalidate><div class="fg">
    ${field('public_url', t('set.public_url'), inp('public_url', s.public_url, 'dir="ltr" placeholder="https://assets.mycompany.com"' + dis), { full: true, hint: t('set.public_url_hint') })}
    ${field('alert_warranty_days', t('set.warranty_days'), inp('alert_warranty_days', s.alert_warranty_days, 'type="number" min="1" max="365" dir="ltr"' + dis))}
    ${field('alert_maintenance_days', t('set.maintenance_days'), inp('alert_maintenance_days', s.alert_maintenance_days, 'type="number" min="0" max="90" dir="ltr"' + dis))}
    <div class="fld full"><label class="cb"><input type="checkbox" id="f-access_requests_enabled" ${s.access_requests_enabled ? 'checked' : ''}${dis}> ${ic('user', 16)} ${t('set.access_requests')}</label><div class="hint">${t('set.access_requests_hint')}</div></div>
    ${field('access_allowed_domains', t('set.domains'), inp('access_allowed_domains', (s.access_allowed_domains || []).join(', '), 'dir="ltr" autocomplete="off" autocapitalize="off" placeholder="mycompany.com, mycompany.com.eg"' + dis), { full: true, hint: t('set.domains_hint') })}
    <div class="fld full"><label class="cb"><input type="checkbox" id="f-asset_requests_enabled" ${s.asset_requests_enabled ? 'checked' : ''}${dis}> ${ic('inbox', 16)} ${t('set.asset_requests')}</label><div class="hint">${t('set.asset_requests_hint')}</div></div>
    <div class="fld full"><label class="cb"><input type="checkbox" id="f-public_scan_enabled" ${s.public_scan_enabled ? 'checked' : ''}${dis}> ${ic('qr', 16)} ${t('set.public_scan')}</label><div class="hint">${t('set.public_scan_hint')}</div></div>
    <div class="fld full"><label class="cb"><input type="checkbox" id="f-email_enabled" ${s.email_enabled ? 'checked' : ''}${dis}> ${ic('mail', 16)} ${t('set.email_enabled')}</label><div class="hint">${t('set.email_hint')}</div></div>
    ${field('smtp_host', t('set.smtp_host'), inp('smtp_host', s.smtp_host, 'dir="ltr" placeholder="smtp.office365.com"' + dis))}
    ${field('smtp_port', t('set.smtp_port'), inp('smtp_port', s.smtp_port, 'type="number" dir="ltr"' + dis))}
    ${field('smtp_security', t('set.smtp_security'), `<select id="f-smtp_security"${dis}>${['starttls', 'ssl', 'none'].map(x => `<option value="${x}" ${s.smtp_security === x ? 'selected' : ''}>${t('set.sec_' + x)}</option>`).join('')}</select>`)}
    ${field('digest_hour', t('set.digest_hour'), `<select id="f-digest_hour"${dis}>${[...Array(24).keys()].map(h => `<option value="${h}" ${s.digest_hour === h ? 'selected' : ''}>${String(h).padStart(2, '0')}:00</option>`).join('')}</select>`)}
    ${field('smtp_user', t('set.smtp_user'), inp('smtp_user', s.smtp_user, 'dir="ltr" autocomplete="off"' + dis))}
    ${field('smtp_password', t('set.smtp_password'), inp('smtp_password', '', `type="password" dir="ltr" autocomplete="new-password" placeholder="${s.smtp_password_set ? '••••••••' : ''}"` + dis), { hint: s.smtp_password_set ? t('set.pw_saved') : '' })}
    ${field('smtp_from', t('set.smtp_from'), inp('smtp_from', s.smtp_from, 'dir="ltr" placeholder="assets@mycompany.com"' + dis), { full: true })}
    </div>${manage ? `<div class="toolbar" style="margin:20px 0 0"><button class="btn pri" type="submit">${t('common.save')}</button><div class="sp"></div><button class="btn sm" type="button" id="set-test">${ic('mail', 15)}${t('set.test')}</button><button class="btn sm" type="button" id="set-digest">${t('set.digest_now')}</button></div><div id="set-status" role="status" aria-live="polite"></div>` : ''}</form>`;
  if (!manage) return;
  const body = () => { const b = {}; ['public_url', 'alert_warranty_days', 'alert_maintenance_days', 'smtp_host', 'smtp_port', 'smtp_security', 'digest_hour', 'smtp_user', 'smtp_password', 'smtp_from', 'access_allowed_domains'].forEach(k => b[k] = fv(box, k)); b.email_enabled = $('#f-email_enabled', box).checked; b.access_requests_enabled = $('#f-access_requests_enabled', box).checked; b.asset_requests_enabled = $('#f-asset_requests_enabled', box).checked; b.public_scan_enabled = $('#f-public_scan_enabled', box).checked; return b; };
  $('#setf', box).onsubmit = async e => { e.preventDefault(); try { await api('/api/settings', { method: 'PUT', body: body() }); toast(t('toast.saved')); settingsCard(box); api('/api/branding').then(b => { const re = S.brand && S.brand.asset_requests !== b.asset_requests; S.brand = b; if (re) render(); }).catch(() => { }); } catch (err) { if (!showErrors(box, err)) fail(err); } };
  // the test can take up to ~20 s when the server does not answer, so the result stays on screen (not only a toast)
  const status = (kind, icon, html) => { $('#set-status', box).innerHTML = kind ? `<div class="banner ${kind}" style="margin:14px 0 0">${ic(icon, 18)}<div>${html}</div></div>` : ''; };
  $('#set-test', box).onclick = async () => {
    const btn = $('#set-test', box), to = (S.user.email || '').trim();
    if (!to) { status('warn', 'warn', esc(t('set.test_no_email'))); return; }
    btn.disabled = true; status('', '', ''); showErrors(box, null);
    try {
      await api('/api/settings', { method: 'PUT', body: body() });
      status('warn', 'mail', esc(t('set.test_sending', { email: to })));
      await api('/api/settings/test-email', { method: 'POST', body: { to } });
      status('good', 'check', esc(t('set.test_sent_long', { email: to })));
      toast(t('set.test_sent'), to);
    } catch (err) {
      if (showErrors(box, err)) status('', '', '');
      else status('bad', 'warn', `<b>${esc(t('set.test_failed'))}</b><br>${esc(errText(err))}`);
    } finally { btn.disabled = false; }
  };
  $('#set-digest', box).onclick = async () => {
    const btn = $('#set-digest', box); btn.disabled = true; status('', '', ''); showErrors(box, null);
    try {
      await api('/api/settings', { method: 'PUT', body: body() });
      status('warn', 'mail', esc(t('set.digest_running')));
      const r = await api('/api/settings/send-digest', { method: 'POST', body: {} });
      const extra = [r.no_email ? t('set.digest_x_no_email', { n: r.no_email }) : '', r.opted_out ? t('set.digest_x_opted_out', { n: r.opted_out }) : ''].filter(Boolean).map(esc).join('<br>');
      const more = extra ? '<br><span style="font-size:12.5px">' + extra + '</span>' : '';
      if (r.status === 'email_off') status('warn', 'warn', esc(t('set.digest_email_off')));
      else if (r.failed) status('bad', 'warn', `<b>${esc(t('set.digest_failed', { n: r.failed, sent: r.sent }))}</b><br>${esc(errText({ code: r.error }))}`);
      else if (r.sent) { status('good', 'check', esc(t('set.digest_sent_n', { n: r.sent })) + (r.nothing ? '<br>' + esc(t('set.digest_x_nothing', { n: r.nothing })) : '') + more); toast(t('set.digest_sent', { n: r.sent })); }
      else if (!r.checked) status('warn', 'warn', esc(t('set.digest_no_recipients')) + more);
      else status('warn', 'bell', esc(t('set.digest_nothing', { n: r.checked })) + more);
    } catch (err) { if (showErrors(box, err)) status('', '', ''); else status('bad', 'warn', esc(errText(err))); }
    finally { btn.disabled = false; }
  };
}

/* ============ boot ============ */
(async function boot() {
  try {
    await loadDicts();
    if ('serviceWorker' in navigator && window.isSecureContext) navigator.serviceWorker.register('/sw.js').catch(() => { });   // installable app
    S.brand = await api('/api/branding');
    try { const r = await api('/api/auth/me'); S.user = r.user; CSRF = r.csrf; S.license = r.license; } catch (e) { }
    applyBrand(); applyLang(); applyTheme();
    if (!location.hash) location.hash = S.user ? '#/dashboard' : '#/login';
    render();
  } catch (e) {
    $('#root').innerHTML = `<div class="skel">Cannot reach the server. Please try again.</div>`;
  }
})();
setInterval(() => { if (S.user) fetch('/api/auth/me', { credentials: 'same-origin' }).then(r => { if (r.status === 401 && S.user) { S.user = null; CSRF = null; render(); } else refreshBell(); }).catch(() => { }); }, 60000);
