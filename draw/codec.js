// A flipbook in a link: the strokes themselves ride in the URL fragment (#f=…), so nothing is uploaded.
//
// Binary layout (version 1), before deflate:
//   u8 version · u8 frameCount
//   per frame:  varint strokeCount
//   per stroke: u8 head (bit0 eraser · bit1 pressure · bits2-7 width) · varint pointCount
//               varint x0 · varint y0 · then zigzag-varint dx, dy per point
//               if pressure: one nibble per point (0–15), two per byte
// Points live on a GRID × GRID square. Strokes are simplified (Ramer–Douglas–Peucker) before packing;
// the tolerance grows until the link fits LIMIT characters.
// Text form: "z" + base64url(deflate-raw(bytes)) when CompressionStream exists and it helps, else "r" + base64url(bytes).

export const GRID = 512;
export const LIMIT = 6000;
const VERSION = 1;
const MAX_FRAMES = 12;
const MAX_POINTS = 60000;

// ---------- strokes ----------
// stroke: { e: 0|1 (eraser), w: width in grid units, p: [x, y, x, y, ...] floats, pr: [0..1, ...] | null }

function simplify(p, pr, eps) {
  const n = p.length / 2;
  if (n <= 2 || eps <= 0) return { p: p.slice(), pr: pr ? pr.slice() : null };
  const keep = new Uint8Array(n);
  keep[0] = keep[n - 1] = 1;
  const stack = [[0, n - 1]];
  const e2 = eps * eps;
  while (stack.length) {
    const [a, b] = stack.pop();
    const ax = p[2 * a], ay = p[2 * a + 1], bx = p[2 * b], by = p[2 * b + 1];
    const dx = bx - ax, dy = by - ay, len2 = dx * dx + dy * dy;
    let best = -1, bestD = e2;
    for (let i = a + 1; i < b; i++) {
      const px = p[2 * i] - ax, py = p[2 * i + 1] - ay;
      let d;
      if (len2 === 0) d = px * px + py * py;
      else {
        const t = Math.max(0, Math.min(1, (px * dx + py * dy) / len2));
        const qx = px - t * dx, qy = py - t * dy;
        d = qx * qx + qy * qy;
      }
      // Keep a point where pressure turns, too, so a pencil stroke keeps its swell.
      if (pr && Math.abs(pr[i] - (pr[a] + (pr[b] - pr[a]) * ((i - a) / (b - a)))) > 0.12) d = Math.max(d, e2 * 1.01);
      if (d > bestD) { bestD = d; best = i; }
    }
    if (best > 0) { keep[best] = 1; stack.push([a, best], [best, b]); }
  }
  const op = [], opr = pr ? [] : null;
  for (let i = 0; i < n; i++) if (keep[i]) { op.push(p[2 * i], p[2 * i + 1]); if (opr) opr.push(pr[i]); }
  return { p: op, pr: opr };
}

const clampGrid = (v) => Math.max(0, Math.min(GRID - 1, Math.round(v)));

// ---------- bytes ----------
class Writer {
  constructor() { this.buf = new Uint8Array(1024); this.n = 0; }
  byte(b) {
    if (this.n === this.buf.length) { const nb = new Uint8Array(this.buf.length * 2); nb.set(this.buf); this.buf = nb; }
    this.buf[this.n++] = b & 255;
  }
  varint(v) { while (v > 127) { this.byte((v & 127) | 128); v >>>= 7; } this.byte(v); }
  zig(v) { this.varint(v >= 0 ? v * 2 : -v * 2 - 1); }
  bytes() { return this.buf.slice(0, this.n); }
}

class Reader {
  constructor(b) { this.b = b; this.i = 0; }
  byte() { if (this.i >= this.b.length) throw new Error("short"); return this.b[this.i++]; }
  varint() {
    let v = 0, s = 0, b;
    do { b = this.byte(); v += (b & 127) * 2 ** s; s += 7; if (s > 28) throw new Error("varint"); } while (b & 128);
    return v;
  }
  zig() { const v = this.varint(); return v % 2 ? -(v + 1) / 2 : v / 2; }
}

export function encodeBinary(frames, eps = 0.75) {
  const w = new Writer();
  w.byte(VERSION);
  w.byte(frames.length);
  for (const strokes of frames) {
    const packed = [];
    for (const s of strokes) {
      const hasPr = !!(s.pr && s.pr.length * 2 === s.p.length);
      const simp = simplify(s.p, hasPr ? s.pr : null, eps);
      // Round to the grid and drop repeats.
      const pts = [], prs = [];
      for (let i = 0; i < simp.p.length; i += 2) {
        const x = clampGrid(simp.p[i]), y = clampGrid(simp.p[i + 1]);
        const L = pts.length;
        if (L && pts[L - 2] === x && pts[L - 1] === y) continue;
        pts.push(x, y);
        if (hasPr) prs.push(Math.max(0, Math.min(15, Math.round(simp.pr[i / 2] * 15))));
      }
      if (pts.length) packed.push({ e: s.e ? 1 : 0, w: Math.max(1, Math.min(63, Math.round(s.w))), pts, prs: hasPr ? prs : null });
    }
    w.varint(packed.length);
    for (const s of packed) {
      w.byte(s.e | (s.prs ? 2 : 0) | (s.w << 2));
      const n = s.pts.length / 2;
      w.varint(n);
      w.varint(s.pts[0]); w.varint(s.pts[1]);
      for (let i = 2; i < s.pts.length; i += 2) { w.zig(s.pts[i] - s.pts[i - 2]); w.zig(s.pts[i + 1] - s.pts[i - 1]); }
      if (s.prs) for (let i = 0; i < n; i += 2) w.byte((s.prs[i] << 4) | (i + 1 < n ? s.prs[i + 1] : 0));
    }
  }
  return w.bytes();
}

export function decodeBinary(bytes) {
  const r = new Reader(bytes);
  if (r.byte() !== VERSION) throw new Error("version");
  const fc = r.byte();
  if (fc < 1 || fc > MAX_FRAMES) throw new Error("frames");
  const frames = [];
  let total = 0;
  for (let f = 0; f < fc; f++) {
    const sc = r.varint();
    if (sc > MAX_POINTS) throw new Error("strokes");
    const strokes = [];
    for (let k = 0; k < sc; k++) {
      const head = r.byte();
      const n = r.varint();
      total += n;
      if (n < 1 || total > MAX_POINTS) throw new Error("points");
      const p = new Array(n * 2);
      let x = r.varint(), y = r.varint();
      p[0] = x; p[1] = y;
      for (let i = 1; i < n; i++) { x += r.zig(); y += r.zig(); p[2 * i] = x; p[2 * i + 1] = y; }
      let pr = null;
      if (head & 2) {
        pr = new Array(n);
        for (let i = 0; i < n; i += 2) { const b = r.byte(); pr[i] = (b >> 4) / 15; if (i + 1 < n) pr[i + 1] = (b & 15) / 15; }
      }
      strokes.push({ e: head & 1, w: head >> 2, p, pr });
    }
    frames.push(strokes);
  }
  return frames;
}

// ---------- text ----------
export function toB64u(bytes) {
  let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function fromB64u(str) {
  if (!/^[A-Za-z0-9_-]*$/.test(str)) throw new Error("b64");
  const s = atob(str.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((str.length + 3) % 4));
  const out = new Uint8Array(s.length);
  for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
  return out;
}

const canZip = () => typeof CompressionStream === "function" && typeof DecompressionStream === "function";

async function pipe(bytes, stream) {
  const res = new Response(new Blob([bytes]).stream().pipeThrough(stream));
  return new Uint8Array(await res.arrayBuffer());
}

export async function encodeLink(frames, { limit = LIMIT } = {}) {
  let out = "";
  for (const eps of [0.6, 1, 1.6, 2.4, 3.5, 5]) {
    const raw = encodeBinary(frames, eps);
    out = "r" + toB64u(raw);
    if (canZip()) {
      try {
        const z = await pipe(raw, new CompressionStream("deflate-raw"));
        if (z.length < raw.length) out = "z" + toB64u(z);
      } catch { /* keep raw */ }
    }
    if (out.length <= limit) break;
  }
  return out;
}

export async function decodeLink(str) {
  const kind = str[0], body = fromB64u(str.slice(1));
  if (kind === "r") return decodeBinary(body);
  if (kind === "z") {
    if (!canZip()) throw new Error("no-inflate");
    const raw = await pipe(body, new DecompressionStream("deflate-raw"));
    if (raw.length > 1 << 20) throw new Error("big");
    return decodeBinary(raw);
  }
  throw new Error("kind");
}
