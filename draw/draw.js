// Three frames, onion skin, a loop — then a GIF to keep and a link to send.
import { startLesson, INK, PAPER } from "./otto.js";
import { encodeLink, decodeLink, GRID } from "./codec.js";
import { encodeGIF, quantizeTwoTone, twoTonePalette } from "./gif.js";
import { track } from "./track.js";

const SIZE = GRID;          // drawing space: SIZE × SIZE
const FRAMES = 3;
const FPS = 7;
const PEN_W = 7, ERASER_W = 34;
const GIF_SIZE = 480;
const PAPER_RGB = [251, 248, 241], INK_RGB = [27, 27, 31];
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = (s) => document.querySelector(s);

// ---------- strokes ----------
// stroke: { e: 0|1 eraser, w: width, p: [x, y, ...] in SIZE space, pr: [0..1] per point | null }
function drawStroke(ctx, s, k) {
  const p = s.p, n = p.length / 2;
  if (!n) return;
  ctx.save();
  ctx.lineCap = ctx.lineJoin = "round";
  if (s.e) ctx.globalCompositeOperation = "destination-out";
  ctx.strokeStyle = ctx.fillStyle = INK;
  const width = (i) => s.w * k * (s.pr ? 0.35 + 1.3 * s.pr[i] : 1);
  const X = (i) => p[2 * i] * k, Y = (i) => p[2 * i + 1] * k;
  const mx = (i) => (X(i) + X(i + 1)) / 2, my = (i) => (Y(i) + Y(i + 1)) / 2;
  if (n === 1) {
    ctx.beginPath();
    ctx.arc(X(0), Y(0), width(0) / 2, 0, Math.PI * 2);
    ctx.fill();
  } else if (!s.pr) {
    ctx.beginPath();
    ctx.moveTo(X(0), Y(0));
    for (let i = 1; i < n - 1; i++) ctx.quadraticCurveTo(X(i), Y(i), mx(i), my(i));
    ctx.lineTo(X(n - 1), Y(n - 1));
    ctx.lineWidth = width(0);
    ctx.stroke();
  } else {
    // Pencil: each piece takes the width of its pressure.
    let sx = X(0), sy = Y(0);
    for (let i = 1; i < n; i++) {
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      if (i < n - 1) { ctx.quadraticCurveTo(X(i), Y(i), mx(i), my(i)); sx = mx(i); sy = my(i); }
      else ctx.lineTo(X(i), Y(i));
      ctx.lineWidth = width(i);
      ctx.stroke();
    }
  }
  ctx.restore();
}

function renderStrokes(ctx, strokes, k) {
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  for (const s of strokes) drawStroke(ctx, s, k);
}

const layer = () => { const c = document.createElement("canvas"); return { c, x: c.getContext("2d") }; };
const drawn = (frames) => frames.map((f, i) => (f.length ? i : -1)).filter((i) => i >= 0);

// ---------- a player (the received flipbook) ----------
function player(canvas, frames, onTap) {
  const ctx = canvas.getContext("2d");
  const caches = frames.map(() => layer());
  const list = drawn(frames);
  let j = 0, timer = 0, playing = false;
  const fit = () => {
    const px = Math.max(1, Math.round(canvas.clientWidth * Math.min(3, devicePixelRatio || 1)));
    if (canvas.width === px) return;
    canvas.width = canvas.height = px;
    caches.forEach((L, i) => { L.c.width = L.c.height = px; renderStrokes(L.x, frames[i], px / SIZE); });
  };
  const paint = () => {
    fit();
    ctx.fillStyle = PAPER;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    if (list.length) ctx.drawImage(caches[list[j]].c, 0, 0);
  };
  const play = (on) => {
    playing = on && list.length > 1;
    clearInterval(timer);
    if (playing) timer = setInterval(() => { j = (j + 1) % list.length; paint(); }, 1000 / FPS);
    onTap?.(playing);
  };
  new ResizeObserver(paint).observe(canvas);
  canvas.addEventListener("click", () => play(!playing));
  paint();
  play(!reduce);
  return { stop: () => play(false) };
}

// ---------- the studio ----------
const pad = $("#pad");
const pctx = pad.getContext("2d");
const caches = Array.from({ length: FRAMES }, layer);
const scratch = layer();
const S = {
  frames: Array.from({ length: FRAMES }, () => []),
  cur: 0, tool: "pen",
  playing: false, playIdx: 0, timer: 0,
  active: null, pointerId: null, rect: null, penSeen: false,
  reply: false, link: "", linkFor: -1, version: 0,
};

let k = 1;
function fitPad() {
  const px = Math.max(1, Math.round(pad.clientWidth * Math.min(3, devicePixelRatio || 1)));
  if (pad.width === px) return;
  pad.width = pad.height = px;
  scratch.c.width = scratch.c.height = px;
  k = px / SIZE;
  caches.forEach((L, i) => { L.c.width = L.c.height = px; renderStrokes(L.x, S.frames[i], k); });
}

function paint() {
  fitPad();
  pctx.globalAlpha = 1;
  pctx.fillStyle = PAPER;
  pctx.fillRect(0, 0, pad.width, pad.height);
  if (S.playing) { pctx.drawImage(caches[S.playIdx].c, 0, 0); return; }
  const prev = S.cur - 1;
  if (prev >= 0 && S.frames[prev].length) {
    pctx.globalAlpha = 0.2;
    pctx.drawImage(caches[prev].c, 0, 0);
    pctx.globalAlpha = 1;
  }
  if (S.active) {
    scratch.x.clearRect(0, 0, pad.width, pad.height);
    scratch.x.drawImage(caches[S.cur].c, 0, 0);
    drawStroke(scratch.x, S.active, k);
    pctx.drawImage(scratch.c, 0, 0);
  } else pctx.drawImage(caches[S.cur].c, 0, 0);
}

let raf = 0;
const requestPaint = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; paint(); }); };

// Tabs with a small picture of each frame.
const tabs = [...document.querySelectorAll(".tab")];
function thumb(i) {
  const c = tabs[i].querySelector("canvas");
  const px = Math.round(c.clientWidth * Math.min(3, devicePixelRatio || 1)) || 96;
  if (c.width !== px) c.width = c.height = px;
  const x = c.getContext("2d");
  x.fillStyle = PAPER;
  x.fillRect(0, 0, px, px);
  if (caches[i].c.width > 1) x.drawImage(caches[i].c, 0, 0, px, px);
}

function syncUI() {
  const shown = S.playing ? S.playIdx : S.cur;
  tabs.forEach((t, i) => {
    t.setAttribute("aria-current", i === shown ? "true" : "false");
    t.classList.toggle("has", S.frames[i].length > 0);
  });
  const any = S.frames.some((f) => f.length);
  $("#play").setAttribute("aria-pressed", S.playing ? "true" : "false");
  $("#play .lbl").textContent = S.playing ? "Stop" : "Play";
  $("#play").disabled = !any;
  $("#undo").disabled = !S.frames[S.cur].length || S.playing;
  $("#clear").disabled = !S.frames[S.cur].length || S.playing;
  $("#gif").disabled = !any;
  $("#send").disabled = !any;
  for (const b of document.querySelectorAll("[data-tool]")) b.setAttribute("aria-pressed", b.dataset.tool === S.tool ? "true" : "false");
  pad.classList.toggle("erasing", S.tool === "eraser");
}

function changed(i) {
  renderStrokes(caches[i].x, S.frames[i], k);
  thumb(i);
  S.version++;
  scheduleLink();
  syncUI();
  requestPaint();
}

function select(i) {
  stopPlay();
  S.cur = i;
  syncUI();
  requestPaint();
}

// ---------- drawing ----------
function addPoint(ev) {
  const r = S.rect;
  const x = ((ev.clientX - r.left) / r.width) * SIZE, y = ((ev.clientY - r.top) / r.height) * SIZE;
  const p = S.active.p, n = p.length;
  if (n && Math.hypot(x - p[n - 2], y - p[n - 1]) < 0.6) return;
  p.push(x, y);
  if (S.active.pr) S.active.pr.push(ev.pressure > 0 ? ev.pressure : 0.5);
}

pad.addEventListener("pointerdown", (e) => {
  if (S.pointerId !== null || e.button > 0) return;
  if (e.pointerType === "pen") S.penSeen = true;
  else if (e.pointerType === "touch" && S.penSeen) return; // palm, while a Pencil is in use
  e.preventDefault();
  stopPlay();
  try { pad.setPointerCapture(e.pointerId); } catch {}
  S.pointerId = e.pointerId;
  S.rect = pad.getBoundingClientRect();
  const eraser = S.tool === "eraser";
  S.active = { e: eraser ? 1 : 0, w: eraser ? ERASER_W : PEN_W, p: [], pr: e.pointerType === "pen" && !eraser ? [] : null };
  addPoint(e);
  requestPaint();
});

pad.addEventListener("pointermove", (e) => {
  if (e.pointerId !== S.pointerId || !S.active) return;
  const evs = e.getCoalescedEvents ? e.getCoalescedEvents() : [];
  for (const ev of evs.length ? evs : [e]) addPoint(ev);
  requestPaint();
});

function endStroke(e) {
  if (e.pointerId !== S.pointerId) return;
  const s = S.active;
  S.active = null;
  S.pointerId = null;
  if (s && s.p.length) {
    S.frames[S.cur].push(s);
    track("draw_start", { reply: S.reply ? 1 : 0 }, { onlyOnce: true });
    changed(S.cur);
  } else requestPaint();
}
pad.addEventListener("pointerup", endStroke);
pad.addEventListener("pointercancel", endStroke);
pad.addEventListener("contextmenu", (e) => e.preventDefault());

// ---------- play ----------
function startPlay() {
  const list = drawn(S.frames);
  if (!list.length) return;
  S.playing = true;
  let j = 0;
  S.playIdx = list[0];
  S.timer = setInterval(() => { j = (j + 1) % list.length; S.playIdx = list[j]; syncUI(); requestPaint(); }, 1000 / FPS);
  if (list.length >= 2) track("draw_play", { frames: list.length }, { onlyOnce: true });
  syncUI();
  requestPaint();
}
function stopPlay() {
  if (!S.playing) return;
  clearInterval(S.timer);
  S.playing = false;
  syncUI();
  requestPaint();
}

// ---------- the link ----------
let linkTimer = 0;
function scheduleLink() {
  clearTimeout(linkTimer);
  linkTimer = setTimeout(makeLink, 250);
}
async function makeLink() {
  const v = S.version;
  const s = await encodeLink(S.frames);
  if (v === S.version) { S.link = s; S.linkFor = v; }
  return s;
}
const linkURL = (s) => `${location.origin}${location.pathname}#f=${s}`;

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.add("on");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.remove("on"), 1800);
}

async function copy(url) {
  try { await navigator.clipboard.writeText(url); toast("Link copied"); return "copy"; }
  catch { window.prompt("Copy this link", url); return "prompt"; }
}

async function send() {
  stopPlay();
  // Keep the share call close to the tap (Safari wants a fresh gesture): the link is usually ready already.
  const s = S.linkFor === S.version ? S.link : await makeLink();
  const url = linkURL(s);
  let method;
  if (navigator.share) {
    try { await navigator.share({ title: "A flipbook", text: "I drew you a flipbook.", url }); method = "share"; }
    catch (e) { if (e && e.name === "AbortError") return; method = await copy(url); }
  } else method = await copy(url);
  track("draw_share", { method, chars: s.length, frames: drawn(S.frames).length });
}

// ---------- the GIF ----------
function makeGIF(frames) {
  const list = drawn(frames);
  const c = document.createElement("canvas"), L = layer();
  c.width = c.height = L.c.width = L.c.height = GIF_SIZE;
  const x = c.getContext("2d", { willReadFrequently: true });
  const out = list.map((i) => {
    x.fillStyle = PAPER;
    x.fillRect(0, 0, GIF_SIZE, GIF_SIZE);
    renderStrokes(L.x, frames[i], GIF_SIZE / SIZE);
    x.drawImage(L.c, 0, 0);
    x.font = "600 14px Inter, system-ui, sans-serif";
    x.textAlign = "right";
    x.fillStyle = "rgba(27,27,31,.34)";
    x.fillText("iflipbook.com", GIF_SIZE - 14, GIF_SIZE - 14);
    return quantizeTwoTone(x.getImageData(0, 0, GIF_SIZE, GIF_SIZE).data, PAPER_RGB, INK_RGB, 16);
  });
  return encodeGIF({ width: GIF_SIZE, height: GIF_SIZE, frames: out, palette: twoTonePalette(PAPER_RGB, INK_RGB, 16), delay: Math.round(100 / FPS) });
}

function download(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

async function saveGIF() {
  stopPlay();
  const bytes = makeGIF(S.frames);
  const name = "flipbook.gif";
  const file = new File([bytes], name, { type: "image/gif" });
  let via = "download";
  const coarse = matchMedia("(pointer: coarse)").matches;
  if (coarse && navigator.canShare && navigator.canShare({ files: [file] })) {
    try { await navigator.share({ files: [file] }); via = "share"; }
    catch (e) { if (e && e.name === "AbortError") return; download(file, name); }
  } else download(file, name);
  track("draw_gif", { frames: drawn(S.frames).length, via, bytes: bytes.length });
}

// ---------- wiring ----------
tabs.forEach((t, i) => t.addEventListener("click", () => select(i)));
$("#play").addEventListener("click", () => (S.playing ? stopPlay() : startPlay()));
for (const b of document.querySelectorAll("[data-tool]")) b.addEventListener("click", () => { S.tool = b.dataset.tool; syncUI(); });
$("#undo").addEventListener("click", () => { if (S.frames[S.cur].pop()) changed(S.cur); });
$("#clear").addEventListener("click", () => { if (S.frames[S.cur].length) { S.frames[S.cur] = []; changed(S.cur); } });
$("#gif").addEventListener("click", saveGIF);
$("#send").addEventListener("click", send);

document.addEventListener("keydown", (e) => {
  if (e.target.closest && e.target.closest("input, textarea")) return;
  if ($("#studio").hidden) return;
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "z") { e.preventDefault(); $("#undo").click(); return; }
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  if (e.key >= "1" && e.key <= String(FRAMES)) select(Number(e.key) - 1);
  else if (e.key === " " && !e.target.closest("button, a")) { e.preventDefault(); $("#play").click(); }
  else if (e.key === "e") { S.tool = "eraser"; syncUI(); }
  else if (e.key === "p" || e.key === "b") { S.tool = "pen"; syncUI(); }
});

new ResizeObserver(() => { paint(); tabs.forEach((_, i) => thumb(i)); }).observe(pad);

// ---------- open ----------
let received = null;

function showStudio() {
  $("#received").hidden = true;
  $("#lesson").hidden = false;
  $("#studio").hidden = false;
  if (!showStudio.started) { showStudio.started = true; startLesson($("#otto"), { reduce }); }
  syncUI();
  requestPaint();
}

async function open() {
  const m = location.hash.match(/^#f=([rz][A-Za-z0-9_-]+)$/);
  if (m) {
    try {
      const frames = await decodeLink(m[1]);
      if (frames.some((f) => f.length)) {
        received?.stop();
        $("#received").hidden = false;
        $("#lesson").hidden = true;
        $("#studio").hidden = true;
        received = player($("#rx"), frames, (on) => { $("#rx").setAttribute("aria-label", on ? "A flipbook, playing. Tap to pause." : "A flipbook. Tap to play."); });
        track("draw_received", { frames: drawn(frames).length, chars: m[1].length });
        return;
      }
    } catch { /* a broken link opens the studio */ }
  }
  showStudio();
}

$("#back").addEventListener("click", () => {
  received?.stop();
  received = null;
  history.replaceState(null, "", location.pathname + location.search);
  S.reply = true;
  S.frames = Array.from({ length: FRAMES }, () => []);
  S.cur = 0;
  caches.forEach((_, i) => changed(i));
  showStudio();
  $("#studio").scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
});

window.addEventListener("hashchange", open);
tabs.forEach((_, i) => thumb(i));
open();
