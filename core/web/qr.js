"use strict";
/* QR Code generator - byte mode, error-correction level M, versions 1-10 (up to 213 bytes).
   Dependency-free; follows ISO/IEC 18004 (structure after Project Nayuki's reference implementation, MIT). */
const QR = (() => {
  const ECC_PER_BLOCK = [0, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26];
  const BLOCKS = [0, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5];
  const ALIGN = [[], [], [6, 18], [6, 22], [6, 26], [6, 30], [6, 34], [6, 22, 38], [6, 24, 42], [6, 26, 46], [6, 28, 50]];
  const ECL_M = 0;                                                  // format bits for level M
  const rawModules = v => { let r = (16 * v + 128) * v + 64; if (v >= 2) { const n = Math.floor(v / 7) + 2; r -= (25 * n - 10) * n - 55; if (v >= 7) r -= 36; } return r; };
  const dataCodewords = v => Math.floor(rawModules(v) / 8) - ECC_PER_BLOCK[v] * BLOCKS[v];

  // ---- Reed-Solomon over GF(2^8) with polynomial 0x11D
  const mul = (x, y) => { let z = 0; for (let i = 7; i >= 0; i--) { z = (z << 1) ^ ((z >>> 7) * 0x11D); z ^= ((y >>> i) & 1) * x; } return z; };
  function rsDivisor(deg) {
    const r = new Array(deg).fill(0); r[deg - 1] = 1; let root = 1;
    for (let i = 0; i < deg; i++) { for (let j = 0; j < r.length; j++) { r[j] = mul(r[j], root); if (j + 1 < r.length) r[j] ^= r[j + 1]; } root = mul(root, 0x02); }
    return r;
  }
  function rsRemainder(data, div) {
    const r = div.map(() => 0);
    for (const b of data) { const f = b ^ r.shift(); r.push(0); div.forEach((c, i) => { r[i] ^= mul(c, f); }); }
    return r;
  }
  const formatBits = mask => { const data = (ECL_M << 3) | mask; let rem = data; for (let i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537); return ((data << 10) | rem) ^ 0x5412; };
  const bit = (x, i) => ((x >>> i) & 1) !== 0;
  const MASKS = [(x, y) => (x + y) % 2 === 0, (x, y) => y % 2 === 0, (x, y) => x % 3 === 0, (x, y) => (x + y) % 3 === 0,
    (x, y) => (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0, (x, y) => x * y % 2 + x * y % 3 === 0,
    (x, y) => (x * y % 2 + x * y % 3) % 2 === 0, (x, y) => ((x + y) % 2 + x * y % 3) % 2 === 0];

  function codewords(bytes) {
    let ver = 1;
    for (; ver <= 10; ver++) if (4 + (ver < 10 ? 8 : 16) + bytes.length * 8 <= dataCodewords(ver) * 8) break;
    if (ver > 10) throw new Error('QR: text too long');
    const bits = [], put = (val, len) => { for (let i = len - 1; i >= 0; i--) bits.push((val >>> i) & 1); };
    put(4, 4); put(bytes.length, ver < 10 ? 8 : 16); bytes.forEach(b => put(b, 8));
    const cap = dataCodewords(ver) * 8;
    put(0, Math.min(4, cap - bits.length)); put(0, (8 - bits.length % 8) % 8);
    for (let p = 0xEC; bits.length < cap; p ^= 0xEC ^ 0x11) put(p, 8);
    const data = []; for (let i = 0; i < bits.length; i += 8) { let b = 0; for (let j = 0; j < 8; j++) b = (b << 1) | bits[i + j]; data.push(b); }
    const nb = BLOCKS[ver], ecl = ECC_PER_BLOCK[ver], raw = Math.floor(rawModules(ver) / 8), numShort = nb - raw % nb, shortLen = Math.floor(raw / nb);
    const div = rsDivisor(ecl), blocks = [];
    for (let i = 0, k = 0; i < nb; i++) {
      const dat = data.slice(k, k + shortLen - ecl + (i < numShort ? 0 : 1)); k += dat.length;
      const ecc = rsRemainder(dat, div); if (i < numShort) dat.push(0); blocks.push(dat.concat(ecc));
    }
    const out = [];
    for (let i = 0; i < blocks[0].length; i++) blocks.forEach((b, j) => { if (i !== shortLen - ecl || j >= numShort) out.push(b[i]); });
    return { ver, out };
  }

  function matrix(text) {
    const { ver, out } = codewords([...new TextEncoder().encode(text)]);
    const size = ver * 4 + 17;
    const mods = Array.from({ length: size }, () => new Array(size).fill(false)), fn = Array.from({ length: size }, () => new Array(size).fill(false));
    const set = (x, y, d) => { mods[y][x] = d; fn[y][x] = true; };
    for (let i = 0; i < size; i++) { set(6, i, i % 2 === 0); set(i, 6, i % 2 === 0); }
    const finder = (cx, cy) => { for (let dy = -4; dy <= 4; dy++) for (let dx = -4; dx <= 4; dx++) { const d = Math.max(Math.abs(dx), Math.abs(dy)), x = cx + dx, y = cy + dy; if (x >= 0 && x < size && y >= 0 && y < size) set(x, y, d !== 2 && d !== 4); } };
    finder(3, 3); finder(size - 4, 3); finder(3, size - 4);
    const al = ALIGN[ver], na = al.length;
    for (let i = 0; i < na; i++) for (let j = 0; j < na; j++) {
      if ((i === 0 && j === 0) || (i === 0 && j === na - 1) || (i === na - 1 && j === 0)) continue;
      for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) set(al[i] + dx, al[j] + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
    }
    const drawFormat = mask => {
      const b = formatBits(mask);
      for (let i = 0; i <= 5; i++) set(8, i, bit(b, i));
      set(8, 7, bit(b, 6)); set(8, 8, bit(b, 7)); set(7, 8, bit(b, 8));
      for (let i = 9; i < 15; i++) set(14 - i, 8, bit(b, i));
      for (let i = 0; i < 8; i++) set(size - 1 - i, 8, bit(b, i));
      for (let i = 8; i < 15; i++) set(8, size - 15 + i, bit(b, i));
      set(8, size - 8, true);
    };
    drawFormat(0);
    if (ver >= 7) {
      let rem = ver; for (let i = 0; i < 12; i++) rem = (rem << 1) ^ ((rem >>> 11) * 0x1F25);
      const b = (ver << 12) | rem;
      for (let i = 0; i < 18; i++) { const c = bit(b, i), a = size - 11 + i % 3, bb = Math.floor(i / 3); set(a, bb, c); set(bb, a, c); }
    }
    let i = 0;
    for (let right = size - 1; right >= 1; right -= 2) {
      if (right === 6) right = 5;
      for (let vert = 0; vert < size; vert++) for (let j = 0; j < 2; j++) {
        const x = right - j, up = ((right + 1) & 2) === 0, y = up ? size - 1 - vert : vert;
        if (!fn[y][x] && i < out.length * 8) { mods[y][x] = bit(out[i >>> 3], 7 - (i & 7)); i++; }
      }
    }
    const applyMask = m => { for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) if (!fn[y][x] && MASKS[m](x, y)) mods[y][x] = !mods[y][x]; };
    let best = 0, bestScore = Infinity;
    for (let m = 0; m < 8; m++) { applyMask(m); drawFormat(m); const s = penalty(mods, size); if (s < bestScore) { bestScore = s; best = m; } applyMask(m); }
    applyMask(best); drawFormat(best);
    return { size, mods, ver, mask: best };
  }

  // ISO 18004 penalty rules N1-N4 (used only to pick the most readable mask)
  function penalty(m, n) {
    let s = 0, dark = 0;
    const lineScore = get => {
      let sc = 0, run = 1;
      for (let i = 1; i <= n; i++) {
        if (i < n && get(i) === get(i - 1)) run++;
        else { if (run >= 5) sc += 3 + run - 5; run = 1; }
      }
      for (let i = 0; i + 10 < n; i++) {
        const p = [1, 0, 1, 1, 1, 0, 1].every((v, k) => get(i + k) === !!v);
        if (p && ([7, 8, 9, 10].every(k => !get(i + k)) || (i >= 4 && [1, 2, 3, 4].every(k => !get(i - k))))) sc += 40;
      }
      return sc;
    };
    for (let y = 0; y < n; y++) { s += lineScore(x => m[y][x]); s += lineScore(x => m[x][y]); }
    for (let y = 0; y < n - 1; y++) for (let x = 0; x < n - 1; x++) { const c = m[y][x]; if (c === m[y][x + 1] && c === m[y + 1][x] && c === m[y + 1][x + 1]) s += 3; }
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) if (m[y][x]) dark++;
    s += Math.floor(Math.abs(dark * 100 / (n * n) - 50) / 5) * 10;
    return s;
  }

  /* SVG markup for `text`; quiet zone of 4 modules (required by the standard) */
  function svg(text, cls = 'qr') {
    const q = matrix(text), z = 4, w = q.size + z * 2; let d = '';
    for (let y = 0; y < q.size; y++) for (let x = 0; x < q.size; x++) if (q.mods[y][x]) d += `M${x + z} ${y + z}h1v1h-1z`;
    return `<svg class="${cls}" viewBox="0 0 ${w} ${w}" shape-rendering="crispEdges" xmlns="http://www.w3.org/2000/svg" role="img"><rect width="${w}" height="${w}" fill="#fff"/><path d="${d}" fill="#000"/></svg>`;
  }
  return { svg, matrix, _rs: (data, n) => rsRemainder(data, rsDivisor(n)), _format: formatBits, _codewords: codewords };
})();
