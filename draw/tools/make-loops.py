#!/usr/bin/env python3
"""Build media/otto-<name>.gif: small looping GIFs of Otto as he ships in iFlipbook.

Source: the app's hand-drawn starter flipbooks (iFlipbook/StarterFlipbooks/otto-{hello,dance,groove}-episode
.iflipbook.json) — the same poses the app plays, with its in-betweens (easeInOut) where a transition has them.
Nothing here is engine output. Reads the flipbooks the way make-otto.py does.

Usage: python3 draw/tools/make-loops.py [path/to/iFlipbook repo]
"""
import importlib.util
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(os.path.dirname(HERE))
APP = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Projects/iFlipbook")
NAMES = ["hello", "dance", "groove"]
SIZE, SS = 240, 3          # 240 px files (120 pt on Retina), drawn 3x and box-filtered
INK, PAPER = (27, 27, 31), (251, 248, 241)

spec = importlib.util.spec_from_file_location("make_otto", os.path.join(HERE, "make-otto.py"))
mo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mo)


def ease(t):
    return t * t * (3 - 2 * t)


def lerp_pose(a, b, t):
    out = []
    for sa, sb in zip(a, b):
        paths = []
        for pa, pb in zip(sa["p"], sb["p"]):
            paths.append([pa[0]] + [x + (y - x) * t for x, y in zip(pa[1:], pb[1:])])
        out.append({"f": sa["f"], "w": sa["w"], "p": paths})
    return out


def sequence(poses, tweens):
    seq = []
    for i, p in enumerate(poses):
        seq.append(p)
        k = tweens[i] if i < len(tweens) else 0
        if k and i + 1 < len(poses):
            seq += [lerp_pose(p, poses[i + 1], ease(j / (k + 1))) for j in range(1, k + 1)]
    return seq


def bbox(poses):
    xs, ys = [], []
    for pose in poses:
        for s in pose:
            for path in s["p"]:
                pts, _ = mo.flatten(path, 6)
                xs += [x for x, _ in pts]; ys += [y for _, y in pts]
    return min(xs), min(ys), max(xs), max(ys)


def render(pose, box):
    W = SIZE * SS
    im = Image.new("RGB", (W, W), PAPER)
    dr = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    pad = 22
    sc = (SIZE - 2 * pad) * SS / max(x1 - x0, y1 - y0)
    ox = (W - (x1 - x0) * sc) / 2 - x0 * sc
    oy = (W - (y1 - y0) * sc) / 2 - y0 * sc
    for shape in pose:
        for path in shape["p"]:
            pts, closed = mo.flatten(path)
            pts = [(ox + x * sc, oy + y * sc) for x, y in pts]
            if shape["f"]:
                dr.polygon(pts, fill=(255, 255, 255))
            if shape["w"]:
                w = max(2, shape["w"] * sc)
                seq = pts + ([pts[0]] if closed else [])
                dr.line(seq, fill=INK, width=int(w))
                for x, y in seq:
                    dr.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=INK)
    return im.resize((SIZE, SIZE), Image.LANCZOS)


def main():
    for name in NAMES:
        mo.SRC = os.path.join(APP, f"iFlipbook/StarterFlipbooks/otto-{name}-episode.iflipbook.json")
        d, poses, tweens = mo.load()
        frames = [render(p, bbox(poses)) for p in sequence(poses, tweens)]
        out = os.path.join(SITE, "media", f"otto-{name}.gif")
        pal = [f.convert("P", palette=Image.ADAPTIVE, colors=16) for f in frames]
        pal[0].save(out, save_all=True, append_images=pal[1:], duration=int(1000 / d["defaultTransitionFPS"]), loop=0, optimize=True, disposal=1)
        print(out, len(frames), "frames", os.path.getsize(out), "bytes")


if __name__ == "__main__":
    main()
