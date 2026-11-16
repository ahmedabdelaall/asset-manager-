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
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  lock: '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
  refresh: '<polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>',
  chev: '<polyline points="9 18 15 12 9 6"/>'
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
  const el = document.createElement('div'); el.className = 'toast ' + (kind === 'err' ? 'err' : '');
  el.innerHTML = `${ic(kind === 'err' ? 'warn' : 'check', 20)}<div><b>${esc(title)}</b>${msg ? `<span>${esc(msg)}</span>` : ''}</div>`;
  $('#toasts').appendChild(el); setTimeout(() => el.remove(), kind === 'err' ? 7000 : 4000);
}
const fail = (e, title) => toast(title || t('toast.failed'), errText(e), 'err');
function modal(html, cls = '') {
  const ov = document.createElement('div'); ov.className = 'ov'; ov.innerHTML = `<div class="md ${cls}" role="dialog" aria-modal="true">${html}</div>`;
  const close = () => { ov.remove(); document.removeEventListener('keydown', kd); };
  const kd = e => { if (e.key === 'Escape') close(); };
  document.addEventListener('keydown', kd);
  ov.addEventListener('mousedown', e => { if (e.target === ov) close(); });
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
  if (e && e.field) { const f = $(`[data-f="${e.field}"]`, root); if (f) { f.classList.add('err'); $('.em', f).textContent = errText(e); const i = $('input,select', f); i && i.focus(); return true; } }
  return false;
}
const go = h => { if (location.hash === h) render(); else location.hash = h; };

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
  $('#root').innerHTML = `<div class="auth">${authTools()}<div class="box"><div class="head">${logoHTML()}<h1>${esc(companyName() || appName())}</h1><p>${esc(appName())}</p></div>
  <form class="card" id="lf" novalidate><h3>${t('login.title')}</h3><div class="sub">${t('login.sub')}</div><div class="grid" style="gap:14px">
  ${field('username', t('login.username'), inp('username', '', 'autocomplete="username" autocapitalize="off" dir="ltr"'))}
  ${field('password', t('login.password'), inp('password', '', 'type="password" autocomplete="current-password" dir="ltr"'))}
  <div id="lerr" class="banner bad" style="display:none;margin:0"></div>
  <button class="btn pri" type="submit" id="lbtn">${t('login.signin')}</button></div></form></div></div>`;
  bindTools();
  $('#f-username').focus();
  $('#lf').onsubmit = async e => {
    e.preventDefault(); const b = $('#lbtn'); b.disabled = true; $('#lerr').style.display = 'none';
    try {
      const r = await api('/api/auth/login', { method: 'POST', body: { username: $('#f-username').value, password: $('#f-password').value } });
      CSRF = r.csrf; S.user = r.user; S.license = r.license;
      applyLang(); applyTheme(); go(S.user.is_super && S.license.locked ? '#/license' : '#/dashboard');
    } catch (err) {
      const box = $('#lerr'); box.style.display = 'flex'; box.innerHTML = `${ic('warn', 18)}<div>${esc(errText(err))}</div>`; b.disabled = false;
    }
  };
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
  <div></div>
  ${field('password', t('setup.password'), inp('password', '', 'type="password" autocomplete="new-password" dir="ltr"'), { req: true, hint: t('password.policy') })}
  ${field('password2', t('setup.password2'), inp('password2', '', 'type="password" autocomplete="new-password" dir="ltr"'), { req: true })}
  <div class="full"><button class="btn pri" type="submit" id="sbtn" style="width:100%">${t('setup.create')}</button></div></div></form></div></div>`;
  bindTools();
  $('#f-default_language').value = LANG;
  $('#f-default_language').onchange = e => setLang(e.target.value);
  $('#sf').onsubmit = async e => {
    e.preventDefault(); const f = $('#sf');
    if ($('#f-password').value !== $('#f-password2').value) { showErrors(f, { field: 'password2', code: 'password_mismatch' }); return; }
    const body = {}; ['setup_code', 'name_en', 'name_ar', 'default_language', 'full_name', 'username', 'email', 'password'].forEach(k => body[k] = $('#f-' + k).value);
    $('#sbtn').disabled = true;
    try {
      await api('/api/setup', { method: 'POST', body });
      const r = await api('/api/auth/login', { method: 'POST', body: { username: body.username, password: body.password } });
      CSRF = r.csrf; S.user = r.user; S.license = r.license; S.brand = await api('/api/branding');
      localStorage.setItem('am_lang', body.default_language); applyBrand(); applyLang(); applyTheme(); toast(t('setup.done')); go('#/license');
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
const NAV = [['dashboard', 'home', 'dashboard.view'], ['users', 'users', 'users.view'], ['roles', 'shield', 'roles.view'], ['company', 'building', 'company.view'],
['license', 'key', 'license.view'], ['audit', 'list', 'audit.view'], ['backups', 'db', 'backup.view'], ['account', 'user', null]];
const PAGES = { dashboard: pDashboard, users: pUsers, roles: pRoles, company: pCompany, license: pLicense, audit: pAudit, backups: pBackups, account: pAccount };
const curPage = () => { const p = location.hash.replace(/^#\//, '').split('?')[0]; return PAGES[p] ? p : (p === 'login' || p === 'setup' || p === '' ? 'dashboard' : 'dashboard'); };
function licenseBanner() {
  const l = S.license; if (!l || !has('license.view')) return '';
  if (l.locked) return `<div class="banner bad">${ic('lock', 20)}<div class="grow"><b>${t('lic.banner_locked')}</b>${t('lic.state_' + l.state + '_hint')}</div><a class="btn sm" href="#/license">${t('lic.manage')}</a></div>`;
  if (l.state === 'grace') return `<div class="banner warn">${ic('warn', 20)}<div class="grow"><b>${t('lic.banner_grace')}</b>${t('lic.state_grace_hint')}</div><a class="btn sm" href="#/license">${t('lic.manage')}</a></div>`;
  if (l.days_left !== null && l.days_left <= 30) return `<div class="banner warn">${ic('warn', 20)}<div class="grow"><b>${t('lic.banner_soon', { n: l.days_left })}</b></div><a class="btn sm" href="#/license">${t('lic.manage')}</a></div>`;
  return '';
}
function renderShell(page) {
  const locked = S.license && S.license.locked;
  const items = NAV.filter(([k, , perm]) => (!perm || has(perm)) && (!locked || k === 'license' || k === 'account'));
  $('#root').innerHTML = `<div class="app"><aside class="side"><div class="brand">${logoHTML()}<div><b>${esc(companyName() || appName())}</b><span>${esc(appName())}</span></div></div>
  <nav class="nav">${items.map(([k, i]) => `<a href="#/${k}" class="${k === page ? 'on' : ''}">${ic(i)}<span>${t('nav.' + k)}</span></a>`).join('')}</nav>
  <div class="foot">${t('common.version')} ${esc(S.brand.version || '')}</div></aside>
  <main><div class="wrap"><div class="top" id="tophead"></div>${licenseBanner()}<div id="page"><div class="skel">${t('common.loading')}</div></div></div></main></div>`;
}
function pageHead(title, sub, right = '') {
  $('#tophead').innerHTML = `<div><h1>${esc(title)}</h1>${sub ? `<p>${esc(sub)}</p>` : ''}</div><div class="sp"></div>${right}
  <button class="chip" id="t-lang">${ic('globe', 17)}${LANG === 'ar' ? 'English' : 'العربية'}</button>
  <button class="chip" id="t-theme" title="${t('common.theme')}">${ic(document.documentElement.dataset.theme === 'dark' ? 'sun' : 'moon', 17)}</button>
  <div class="menu"><button class="chip" id="t-user">${ic('user', 17)}${esc(S.user.full_name)}</button></div>`;
  bindTools();
  $('#t-user').onclick = e => {
    e.stopPropagation(); const menu = $('.menu'); const ex = $('.pop', menu); if (ex) { ex.remove(); return; }
    menu.insertAdjacentHTML('beforeend', `<div class="pop"><div class="who"><b>${esc(S.user.full_name)}</b><small>${esc(nameOf(S.user, 'role_name'))}</small><small class="mono">${esc(S.user.username)}</small></div>
    <button id="m-acc">${ic('user', 16)}${t('nav.account')}</button><button id="m-out">${ic('logout', 16)}${t('nav.logout')}</button></div>`);
    $('#m-acc').onclick = () => go('#/account'); $('#m-out').onclick = logout;
    setTimeout(() => document.addEventListener('click', () => $('.menu .pop') && $('.menu .pop').remove(), { once: true }), 0);
  };
}
let renderSeq = 0;
async function render() {
  const seq = ++renderSeq;
  if (!S.brand) { $('#root').innerHTML = `<div class="skel">${t('common.loading')}</div>`; return; }
  const h = location.hash.replace(/^#\//, '').split('?')[0];
  if (S.brand.needs_setup) return renderSetup();
  if (!S.user) return renderLogin();
  if (S.user.must_change_password) return renderForcedPassword();
  if (h === 'login' || h === 'setup' || h === '') { return go('#/dashboard'); }
  const page = curPage();
  const locked = S.license && S.license.locked;
  if (locked && page !== 'license' && page !== 'account') return go('#/license');
  if (NAV.find(n => n[0] === page)[2] && !has(NAV.find(n => n[0] === page)[2])) { renderShell(page); pageHead(t('err.forbidden_title'), ''); $('#page').innerHTML = `<div class="card"><div class="empty">${ic('lock', 36)}<b>${t('err.forbidden_title')}</b>${t('err.forbidden_page')}</div></div>`; return; }
  renderShell(page);
  try { await PAGES[page]($('#page'), seq); } catch (e) { if (seq === renderSeq && $('#page')) $('#page').innerHTML = `<div class="banner bad">${ic('warn', 20)}<div class="grow">${esc(errText(e))}</div></div>`; }
}
window.addEventListener('hashchange', render);

/* ============ dashboard ============ */
async function pDashboard(el) {
  const d = await api('/api/dashboard');
  pageHead(t('dash.title'), t('dash.sub', { company: companyName() }));
  S.license = Object.assign(S.license || {}, { state: d.license.state, days_left: d.license.days_left });
  const lic = d.license, ok = lic.state === 'valid' || lic.state === 'grace';
  const kpi = (icon, num, label, sub, cls = '') => `<div class="card kpi ${cls}"><div class="ico">${ic(icon)}</div><div class="num ${String(num).length > 6 ? 'sm' : ''}">${num}</div><div class="lbl">${label}</div><div class="d">${sub}</div></div>`;
  const steps = [[ok, t('dash.step_license'), '#/license', has('license.view')], [!!S.brand.logo, t('dash.step_brand'), '#/company', has('company.view')], [d.users.total > 1, t('dash.step_users'), '#/users', has('users.view')],
  [!!d.last_backup, t('dash.step_backup'), '#/backups', has('backup.view')]];
  el.innerHTML = `<div class="grid g4">
  ${kpi('users', d.users.active, t('dash.active_users'), t('dash.of_total', { n: d.users.total }))}
  ${kpi('shield', d.roles, t('dash.roles'), t('dash.roles_sub'))}
  ${kpi('key', t('lic.state_' + lic.state), t('dash.license'), lic.expires_at ? t('dash.expires', { d: fmtDate(lic.expires_at) }) : t('dash.no_expiry'))}
  ${kpi('db', d.last_backup ? fmtDate(new Date(d.last_backup.ts * 1000).toISOString(), true) : '—', t('dash.last_backup'), t('dash.schema', { v: d.schema, app: d.version }), 'main')}</div>
  <div class="grid g12" style="margin-top:18px"><div class="card s7"><h3>${t('dash.recent')}</h3><div class="sub">${t('dash.recent_sub')}</div>${d.recent ? (d.recent.length ? `<div class="tscroll"><table class="tbl"><tbody>${d.recent.map(r => `<tr><td class="mono" style="white-space:nowrap">${esc(fmtDate(r.ts, true))}</td><td><b>${esc(r.username || '—')}</b></td><td>${esc(actionLabel(r.action))}</td></tr>`).join('')}</tbody></table></div>` : `<div class="empty">${t('common.none')}</div>`) : `<div class="empty">${t('dash.no_audit_perm')}</div>`}</div>
  <div class="card s5"><h3>${t('dash.getting_started')}</h3><div class="sub">${t('dash.getting_started_sub')}</div>${steps.map(([done, label, link, allowed]) => `<div class="chk"><div class="dotc ${done ? 'ok' : ''}">✓</div><div style="flex:1;${done ? 'color:var(--mut)' : 'font-weight:600'}">${esc(label)}</div>${!done && allowed ? `<a class="btn sm" href="${link}">${t('common.open')}</a>` : ''}</div>`).join('')}</div></div>`;
}
const actionLabel = a => (DICT[LANG]['act.' + a] || DICT.en['act.' + a]) || a;

/* ============ users ============ */
async function pUsers(el) {
  const manage = has('users.manage');
  pageHead(t('users.title'), t('users.sub'), manage ? `<button class="btn pri sm" id="addu">${ic('plus', 16)}${t('users.add')}</button>` : '');
  const [ur, rr] = await Promise.all([api('/api/users'), api('/api/roles')]);
  const roles = rr.roles;
  el.innerHTML = `<div class="card"><div class="toolbar"><input class="inp" id="uq" style="max-width:340px" placeholder="${t('common.search')}"><div class="sp"></div><span class="badge mut" id="ucount"></span></div><div id="utbl"></div></div>`;
  let list = ur.users;
  const draw = () => {
    const q = $('#uq').value.trim().toLowerCase();
    const rows = list.filter(u => !q || (u.username + ' ' + u.full_name + ' ' + u.email).toLowerCase().includes(q));
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
  $('#uq').addEventListener('input', debounce(draw, 120));
  draw();
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
    </div>${manage ? `<div class="toolbar" style="margin:20px 0 0"><button class="btn pri" type="submit">${t('common.save')}</button></div>` : ''}</form>
  <div class="s4" style="display:flex;flex-direction:column;gap:18px"><div class="card"><h3>${t('company.logo')}</h3><div class="sub">${t('company.logo_sub')}</div><div class="preview" id="pv" style="margin-bottom:14px">${logoHTML()}<div><b>${esc(companyName())}</b><div style="opacity:.85;font-size:12.5px">${esc(appName())}</div></div></div>
  ${manage ? `<div class="toolbar" style="margin:0"><label class="btn sm" for="logo">${ic('upload', 15)}${t('company.upload')}</label><input type="file" id="logo" accept="image/png,image/jpeg,image/webp" hidden>${c.logo ? `<button class="btn sm dng" id="rmlogo">${ic('trash', 15)}${t('common.remove')}</button>` : ''}</div>` : ''}</div></div></div>`;
  const sync = (a, b) => { $('#' + a).oninput = e => { $('#f-' + b).value = e.target.value.toUpperCase(); pv(); }; $('#f-' + b).oninput = e => { if (/^#[0-9a-fA-F]{6}$/.test(e.target.value)) { $('#' + a).value = e.target.value; pv(); } }; };
  const pv = () => { $('#pv').style.background = `linear-gradient(135deg,${$('#pc').value},${$('#ac').value})`; };
  sync('pc', 'primary_color'); sync('ac', 'accent_color'); pv();
  const refresh = async () => { S.brand = await api('/api/branding'); applyBrand(); applyLang(); applyTheme(); render(); };
  const logoOnly = async () => { S.brand = await api('/api/branding'); $$('.logo').forEach(l => { l.outerHTML = logoHTML(); }); const has = !!S.brand.logo, rm = $('#rmlogo'); if (rm && !has) rm.remove(); if (!rm && has) { $('#logo').insertAdjacentHTML('afterend', `<button class="btn sm dng" id="rmlogo">${ic('trash', 15)}${t('common.remove')}</button>`); $('#rmlogo').onclick = removeLogo; } };
  const removeLogo = async () => { try { await api('/api/company/logo', { method: 'DELETE' }); await logoOnly(); } catch (err) { fail(err); } };
  if (!manage) return;
  $('#cf').onsubmit = async e => {
    e.preventDefault(); const body = {}; ['name_en', 'name_ar', 'app_name_en', 'app_name_ar', 'primary_color', 'accent_color', 'default_language', 'default_theme'].forEach(k => body[k] = $('#f-' + k).value);
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
async function pBackups(el) {
  const manage = has('backup.manage');
  pageHead(t('bk.title'), t('bk.sub'), manage ? `<button class="btn pri sm" id="bk">${ic('db', 15)}${t('bk.now')}</button>` : '');
  const r = await api('/api/backups');
  el.innerHTML = `<div class="grid g12"><div class="card s8"><h3>${t('bk.list')}</h3><div class="sub">${t('bk.keep', { n: r.keep })}</div>${r.backups.length ? `<div class="tscroll"><table class="tbl"><tbody>${r.backups.map(b => `<tr><td class="mono">${esc(b.name)}</td><td style="white-space:nowrap">${esc(fmtDate(new Date(b.ts * 1000).toISOString(), true))}</td><td class="mono">${(b.size / 1024).toFixed(0)} KB</td></tr>`).join('')}</tbody></table></div>` : `<div class="empty">${ic('db', 34)}<b>${t('bk.none')}</b></div>`}</div>
  <div class="card s4"><h3>${t('bk.where')}</h3><div class="sub">${t('bk.where_sub')}</div><div class="mono" style="word-break:break-all;background:var(--surface2);border-radius:10px;padding:10px">${esc(r.dir)}</div><div class="sub" style="margin-top:14px">${t('bk.restore')}</div><div class="mono" style="background:var(--surface2);border-radius:10px;padding:10px;font-size:12px">python tools/manage.py restore &lt;file&gt;</div></div></div>`;
  const b = $('#bk'); if (b) b.onclick = async () => { b.disabled = true; try { await api('/api/backups', { method: 'POST', body: {} }); toast(t('bk.done')); render(); } catch (e) { fail(e); b.disabled = false; } };
}

/* ============ my account ============ */
async function pAccount(el) {
  pageHead(t('acc.title'), t('acc.sub'));
  el.innerHTML = `<div class="grid g12"><div class="card s5"><h3>${t('acc.profile')}</h3><dl style="display:grid;grid-template-columns:130px 1fr;gap:10px 14px;margin:14px 0 0"><dt style="color:var(--mut)">${t('users.full_name')}</dt><dd style="margin:0;font-weight:600">${esc(S.user.full_name)}</dd><dt style="color:var(--mut)">${t('login.username')}</dt><dd class="mono" style="margin:0">${esc(S.user.username)}</dd><dt style="color:var(--mut)">${t('users.email')}</dt><dd class="mono" style="margin:0">${esc(S.user.email || '—')}</dd><dt style="color:var(--mut)">${t('users.role')}</dt><dd style="margin:0"><span class="badge info">${esc(nameOf(S.user, 'role_name'))}</span></dd></dl>
  <h3 style="margin-top:24px">${t('acc.prefs')}</h3><div class="toolbar" style="margin-top:10px"><div class="seg" id="sl"><button data-l="en" class="${LANG === 'en' ? 'on' : ''}">English</button><button data-l="ar" class="${LANG === 'ar' ? 'on' : ''}">العربية</button></div>
  <div class="seg" id="st">${['light', 'dark', 'system'].map(x => `<button data-t="${x}" class="${S.themePref === x ? 'on' : ''}">${t('theme.' + x)}</button>`).join('')}</div></div></div>
  <form class="card s7" id="pf" novalidate><h3>${t('pw.change_title')}</h3><div class="sub">${t('pw.change_sub')}</div><div class="grid" style="gap:14px;max-width:420px">${passwordFields()}<button class="btn pri" type="submit">${t('pw.change')}</button></div></form></div>`;
  $$('#sl button').forEach(b => b.onclick = () => setLang(b.dataset.l)); $$('#st button').forEach(b => b.onclick = () => setTheme(b.dataset.t));
  bindPasswordForm($('#pf'));
}

/* ============ boot ============ */
(async function boot() {
  try {
    await loadDicts();
    S.brand = await api('/api/branding');
    try { const r = await api('/api/auth/me'); S.user = r.user; CSRF = r.csrf; S.license = r.license; } catch (e) { }
    applyBrand(); applyLang(); applyTheme();
    if (!location.hash) location.hash = S.user ? '#/dashboard' : '#/login';
    render();
  } catch (e) {
    $('#root').innerHTML = `<div class="skel">Cannot reach the server. Please try again.</div>`;
  }
})();
setInterval(() => { if (S.user) fetch('/api/auth/me', { credentials: 'same-origin' }).then(r => { if (r.status === 401 && S.user) { S.user = null; CSRF = null; render(); } }).catch(() => { }); }, 60000);
