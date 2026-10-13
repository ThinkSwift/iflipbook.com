// Otto, as he ships in iFlipbook (starter flipbook "Otto says hello"), and his first lesson:
// he waves, draws a ball three times — each over a faint copy of the last — and plays it.
import { OTTO } from "./otto-data.js";

export const INK = "#1b1b1f";
export const PAPER = "#fbf8f1";
const CARD = "#efe9dc";
const AC = "#22d3ee";

const ease = (t) => (t < 0.5 ? 2 * t * t : 1 - (-2 * t + 2) ** 2 / 2);

// The app's play order: each pose, then its in-betweens (easeInOut), at OTTO.fps.
export const SEQ = (() => {
  const s = [];
  OTTO.poses.forEach((_, i) => {
    s.push({ a: i, b: i, t: 0, pose: i });
    const k = OTTO.tweens[i] || 0;
    for (let j = 1; j <= k; j++) s.push({ a: i, b: i + 1, t: ease(j / (k + 1)) });
  });
  return s;
})();

export function drawOtto(ctx, f, x, y, scale) {
  const A = OTTO.poses[f.a], B = OTTO.poses[f.b];
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(scale, scale);
  ctx.lineCap = ctx.lineJoin = "round";
  A.forEach((sa, si) => {
    const sb = B[si];
    const path = new Path2D();
    sa.p.forEach((pa, pi) => {
      const pb = sb.p[pi];
      const v = f.t ? pa.map((n, k) => (k === 0 ? n : n + (pb[k] - n) * f.t)) : pa;
      const m = (v.length - 1) / 6;
      const X = (i, o) => v[1 + i * 6 + o];
      const seg = (j, k) => path.bezierCurveTo(
        X(j, 0) + X(j, 4), X(j, 1) + X(j, 5), X(k, 0) + X(k, 2), X(k, 1) + X(k, 3), X(k, 0), X(k, 1));
      path.moveTo(X(0, 0), X(0, 1));
      for (let k = 1; k < m; k++) seg(k - 1, k);
      if (v[0]) { seg(m - 1, 0); path.closePath(); }
    });
    if (sa.f) { ctx.fillStyle = "#fff"; ctx.fill(path); }
    if (sa.w) { ctx.strokeStyle = INK; ctx.lineWidth = sa.w; ctx.stroke(path); }
  });
  ctx.restore();
}

// ---------- the lesson ----------
const W = 800, H = 500;
const PAGE = { x: 448, y: 34, w: 316, h: 372 };
const TAB = { y: 424, s: 40, gap: 12 };
// Three balls in page coordinates: up high, squashed on the ground, on the way up.
const BALLS = [
  { cx: 158, cy: 84, rx: 40, ry: 40, seed: 0.3 },
  { cx: 158, cy: 334, rx: 51, ry: 26, seed: 1.7 },
  { cx: 158, cy: 204, rx: 40, ry: 40, seed: 2.9 },
];

function handCircle({ cx, cy, rx, ry, seed }) {
  const pts = [], n = 54, a0 = -Math.PI * 0.75, a1 = a0 + Math.PI * 2 + 0.38;
  for (let i = 0; i <= n; i++) {
    const a = a0 + (a1 - a0) * (i / n);
    const wob = 1 + 0.035 * Math.sin(3 * a + seed) + 0.02 * Math.sin(5 * a + seed * 2) + 0.03 * (i / n);
    pts.push([cx + Math.cos(a) * rx * wob, cy + Math.sin(a) * ry * wob]);
  }
  return pts;
}
const BALL_PTS = BALLS.map(handCircle);

const idxOfPose = (p) => SEQ.findIndex((f) => f.pose === p);
const WAVE = SEQ.slice(0, idxOfPose(2) + 1); // stand, raise, wave
const POINT = SEQ[idxOfPose(2)];             // arm out towards the page
const HOP = SEQ.slice(idxOfPose(3));          // crouch, jump, land
const STAND = SEQ[0];
const STEP = 1000 / OTTO.fps;
const BALL_STEP = 1000 / 7;
const T_WAVE = WAVE.length * STEP;
const T_DRAW = 760, T_HOLD = 300, T_FRAME = T_DRAW + T_HOLD;
const T_PLAY = 3900, T_REST = 500;
const T_ALL = T_WAVE + 3 * T_FRAME + T_PLAY + T_REST;

function stateAt(t) {
  if (t < T_WAVE) return { otto: WAVE[Math.floor(t / STEP)], tab: 0, ball: -1 };
  t -= T_WAVE;
  if (t < 3 * T_FRAME) {
    const k = Math.floor(t / T_FRAME), local = t - k * T_FRAME;
    return { otto: POINT, tab: k, ball: k, onion: k - 1, progress: Math.min(1, local / T_DRAW) };
  }
  t -= 3 * T_FRAME;
  if (t < T_PLAY) {
    const k = Math.floor(t / BALL_STEP) % 3;
    return { otto: HOP[Math.min(HOP.length - 1, Math.floor(t / STEP))], tab: k, ball: k, playing: true };
  }
  return { otto: STAND, tab: 0, ball: -1 };
}

const STILL = { otto: POINT, tab: 2, ball: 2, onion: 1, progress: 1 };

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.roundRect ? ctx.roundRect(x, y, w, h, r) : ctx.rect(x, y, w, h);
}

function paintLesson(ctx, s) {
  ctx.fillStyle = CARD;
  ctx.fillRect(0, 0, W, H);
  drawOtto(ctx, s.otto, 6, 52, 0.84);

  // The page.
  roundRect(ctx, PAGE.x, PAGE.y, PAGE.w, PAGE.h, 16);
  ctx.fillStyle = PAPER;
  ctx.fill();
  ctx.strokeStyle = "rgba(27,27,31,.10)";
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.save();
  ctx.translate(PAGE.x, PAGE.y);
  ctx.lineCap = ctx.lineJoin = "round";
  const line = (pts, upto, color, width) => {
    const n = Math.max(2, Math.round(pts.length * upto));
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < n; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.stroke();
    return pts[n - 1];
  };
  if (s.onion >= 0) line(BALL_PTS[s.onion], 1, "rgba(27,27,31,.2)", 8);
  if (s.ball >= 0) {
    const p = s.progress ?? 1;
    const tip = line(BALL_PTS[s.ball], p, INK, 8);
    if (p < 1) {
      ctx.beginPath();
      ctx.arc(tip[0], tip[1], 8, 0, Math.PI * 2);
      ctx.fillStyle = AC;
      ctx.fill();
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = INK;
      ctx.stroke();
    }
  }
  ctx.restore();

  // Frame tabs 1 2 3 (and a play mark while it loops), the same as the ones under your page.
  const total = 3 * TAB.s + 2 * TAB.gap;
  const x0 = PAGE.x + (PAGE.w - total) / 2;
  ctx.font = "600 19px 'Space Grotesk', system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  for (let i = 0; i < 3; i++) {
    const x = x0 + i * (TAB.s + TAB.gap);
    roundRect(ctx, x, TAB.y, TAB.s, TAB.s, 10);
    const on = i === s.tab;
    ctx.fillStyle = on ? INK : PAPER;
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = on ? INK : "rgba(27,27,31,.18)";
    ctx.stroke();
    ctx.fillStyle = on ? PAPER : "rgba(27,27,31,.55)";
    ctx.fillText(String(i + 1), x + TAB.s / 2, TAB.y + TAB.s / 2 + 1);
  }
  if (s.playing) {
    const x = x0 + total + 18, y = TAB.y + TAB.s / 2;
    ctx.beginPath();
    ctx.moveTo(x, y - 11);
    ctx.lineTo(x + 18, y);
    ctx.lineTo(x, y + 11);
    ctx.closePath();
    ctx.fillStyle = INK;
    ctx.fill();
  }
}

export function startLesson(canvas, { reduce = false } = {}) {
  const ctx = canvas.getContext("2d");
  let t0 = 0, raf = 0, onScreen = true, running = !reduce, once = false;
  const visible = () => onScreen && !document.hidden;

  const fit = () => {
    const dpr = Math.min(3, window.devicePixelRatio || 1);
    const w = Math.max(1, Math.round(canvas.clientWidth * dpr));
    if (canvas.width !== w) { canvas.width = w; canvas.height = Math.round((w * H) / W); }
  };
  const draw = (s) => {
    fit();
    ctx.setTransform(canvas.width / W, 0, 0, canvas.width / W, 0, 0);
    paintLesson(ctx, s);
  };
  const tick = (now) => {
    raf = 0;
    if (!t0) t0 = now;
    const t = now - t0;
    if (once && t >= T_ALL) { once = false; running = false; draw(STILL); return; }
    draw(stateAt(t % T_ALL));
    if (running && visible()) raf = requestAnimationFrame(tick);
  };
  const go = () => { if (!raf && running && visible()) raf = requestAnimationFrame(tick); };

  draw(reduce ? STILL : stateAt(0)); // a picture even before the first animation frame (or in a hidden tab)
  go();
  // Reduced motion: still picture; a tap plays the lesson once.
  canvas.addEventListener("click", () => {
    if (running) return;
    running = true; once = true; t0 = 0; go();
  });
  new ResizeObserver(() => { if (!running) draw(STILL); }).observe(canvas);
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(([e]) => { onScreen = e.isIntersecting; go(); }).observe(canvas);
  }
  document.addEventListener("visibilitychange", go);
}
