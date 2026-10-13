// A small animated-GIF writer (GIF89a, global palette, LZW, endless loop). No dependencies.

// Map RGBA pixels drawn in one ink on one paper to a ramp of `levels` shades between them.
// Anti-aliased edges land on the in-between shades, so the GIF keeps soft lines with 16 colours.
export function twoTonePalette(paper, ink, levels = 16) {
  const pal = [];
  for (let i = 0; i < levels; i++) {
    const t = i / (levels - 1);
    pal.push([0, 1, 2].map((c) => Math.round(paper[c] + (ink[c] - paper[c]) * t)));
  }
  return pal;
}

export function quantizeTwoTone(rgba, paper, ink, levels = 16) {
  const n = rgba.length >> 2, out = new Uint8Array(n);
  const lum = (r, g, b) => 0.299 * r + 0.587 * g + 0.114 * b;
  const lp = lum(paper[0], paper[1], paper[2]), li = lum(ink[0], ink[1], ink[2]);
  const span = lp - li || 1, top = levels - 1;
  for (let i = 0, j = 0; i < n; i++, j += 4) {
    const t = (lp - lum(rgba[j], rgba[j + 1], rgba[j + 2])) / span;
    out[i] = t <= 0 ? 0 : t >= 1 ? top : Math.round(t * top);
  }
  return out;
}

function lzw(indices, minCodeSize, out) {
  const clearCode = 1 << minCodeSize, eoi = clearCode + 1;
  let codeSize = minCodeSize + 1, next = eoi + 1;
  let table = new Map();
  const bytes = [];
  let cur = 0, shift = 0;
  const emit = (code) => {
    cur |= code << shift;
    shift += codeSize;
    while (shift >= 8) { bytes.push(cur & 255); cur >>>= 8; shift -= 8; }
  };
  emit(clearCode);
  let prefix = indices[0];
  for (let i = 1; i < indices.length; i++) {
    const k = indices[i];
    const key = (prefix << 8) | k;
    const hit = table.get(key);
    if (hit !== undefined) { prefix = hit; continue; }
    emit(prefix);
    if (next === 4096) {
      emit(clearCode);
      next = eoi + 1;
      codeSize = minCodeSize + 1;
      table = new Map();
    } else {
      if (next >= 1 << codeSize) codeSize++;
      table.set(key, next++);
    }
    prefix = k;
  }
  emit(prefix);
  emit(eoi);
  if (shift > 0) bytes.push(cur & 255);
  out.push(minCodeSize);
  for (let i = 0; i < bytes.length; i += 255) {
    const len = Math.min(255, bytes.length - i);
    out.push(len);
    for (let j = 0; j < len; j++) out.push(bytes[i + j]);
  }
  out.push(0);
}

/**
 * @param {{width:number,height:number,frames:Uint8Array[],palette:number[][],delay:number,loop?:number}} o
 *   frames: one palette index per pixel; delay in hundredths of a second; loop 0 = forever.
 * @returns {Uint8Array}
 */
export function encodeGIF({ width, height, frames, palette, delay = 14, loop = 0 }) {
  let bits = 1;
  while (1 << bits < palette.length) bits++;
  bits = Math.max(bits, 2);
  const size = 1 << bits;
  const out = [];
  const u16 = (v) => out.push(v & 255, (v >> 8) & 255);
  for (const c of "GIF89a") out.push(c.charCodeAt(0));
  u16(width); u16(height);
  out.push(0x80 | ((bits - 1) << 4) | (bits - 1), 0, 0);
  for (let i = 0; i < size; i++) { const c = palette[i] || [0, 0, 0]; out.push(c[0], c[1], c[2]); }
  out.push(0x21, 0xff, 11);
  for (const c of "NETSCAPE2.0") out.push(c.charCodeAt(0));
  out.push(3, 1); u16(loop); out.push(0);
  for (const f of frames) {
    out.push(0x21, 0xf9, 4, 1 << 2); u16(delay); out.push(0, 0);
    out.push(0x2c); u16(0); u16(0); u16(width); u16(height); out.push(0);
    lzw(f, bits, out);
  }
  out.push(0x3b);
  return Uint8Array.from(out);
}
