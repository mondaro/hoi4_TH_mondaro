"""Build Thai-extended copies of HOI4 BMFont fonts.

usage: python3 -I tools/build.py <fonts_src_dir> [name ...]
Writes gfx/fonts/<name>.fnt plus <name>.dds / <name>.tga (whichever atlases exist in the source).
"""
import os, re, sys, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import numpy as np
from PIL import Image
from bmfont import Fnt
from imgio import read_any, write_dds, write_tga, dds_mipcount
import style as st
from thaiglyph import get_font, render
import thai_pua
import thaiglyph

OUT = os.path.join(ROOT, 'mod', 'gfx', 'fonts')
SKIP = {'hoi_arrow_font': 'arrow/number glyphs for map arrows, no running text',
}

THAI = [cp for cp in range(0x0E01, 0x0E5C) if not (0x0E3B <= cp <= 0x0E3E)]
UPPER = [0x0E31, 0x0E34, 0x0E35, 0x0E36, 0x0E37, 0x0E47, 0x0E4D, 0x0E4E]
TONES = [0x0E48, 0x0E49, 0x0E4A, 0x0E4B, 0x0E4C]
LOWER = [0x0E38, 0x0E39, 0x0E3A]
MARKS = set(UPPER + TONES + LOWER)

SERIF_HINTS = ('times', 'garamond', 'afl font', 'typewriter')
SIZE_FACTOR = 1.2     # Thai consonant height / Latin x-height
STEM_FACTOR = 0.95     # Thai stem width / Latin stem width

def pick_face(name, info):
    face = (info.get('face') or '').lower()
    n = name.lower()
    if any(h in face for h in SERIF_HINTS) or n.startswith(('vic_', 'standard', 'garamond', 'newsfeed_title')) or 'typewriter' in n:
        return 'serif'
    return 'sans'

def core_of(fnt, img, sty, cid):
    c = fnt.chars.get(cid)
    if not c or c['width'] <= 0 or c['height'] <= 0:
        return None
    arr = np.asarray(img).astype(np.float32)
    crop = arr[c['y']:c['y'] + c['height'], c['x']:c['x'] + c['width']]
    return st.core_mask(crop, sty)

def ink_rows(M, thr=0.5):
    rows = np.nonzero(M.max(axis=1) >= thr)[0]
    return (rows.min(), rows.max() + 1) if len(rows) else (0, 0)

def stem_width(M, n_stems=1):
    r0, r1 = ink_rows(M)
    h = r1 - r0
    mid = M[r0 + int(h * 0.35): r0 + max(int(h * 0.65), int(h * 0.35) + 1)]
    return float(np.median(mid.sum(axis=1))) / n_stems

def latin_metrics(fnt, img, sty):
    for cid, stem_id, n in ((0x78, 0x6C, 1), (0x445, 0x43F, 2)):
        M = core_of(fnt, img, sty, cid)
        if M is not None:
            r0, r1 = ink_rows(M)
            S = core_of(fnt, img, sty, stem_id)
            sw = stem_width(S, n) if S is not None else None
            return r1 - r0, sw
    raise RuntimeError('no x-height reference glyph')

def choose_size_weight(face, xh, stem):
    f = get_font(face, 100, 400)
    M, l, t, a = render(f, 'น')       # น
    r0, r1 = ink_rows(M)
    ratio = (r1 - r0) / 100.0
    size = xh * SIZE_FACTOR / ratio
    best = (None, 400)
    if stem:
        for w in range(200, 901, 50):
            M, *_ = render(get_font(face, size, w), 'า')   # า
            d = abs(stem_width(M) - stem * STEM_FACTOR)
            if best[0] is None or d < best[0] - 1e-6:
                best = (d, w)
    return size, best[1]

def build_glyphs(face, size, wght):
    """Return dict key -> (M, left, top, adv) for all Thai + PUA forms (pixel units at size)."""
    f = get_font(face, size, wght)
    g = {cp: render(f, chr(cp)) for cp in THAI}
    gap = max(1, int(round(size * 0.035)))
    def top(cp): return g[cp][2]
    def bottom(cp): return g[cp][2] + g[cp][0].shape[0]
    upper_top = min(top(cp) for cp in (0x0E31, 0x0E35, 0x0E36, 0x0E37, 0x0E4D))
    upper_bottom = max(bottom(cp) for cp in (0x0E34, 0x0E35, 0x0E36, 0x0E37))
    cons_top = top(0x0E19)
    # tall consonants: left edge of the ascender relative to the following pen position
    asc_lefts = []
    for cp in (0x0E1B, 0x0E1D, 0x0E1F):
        M, l, t, a = g[cp]
        rows = M[:max(0, cons_top - t - 1)]
        cols = np.nonzero(rows.max(axis=0) >= 0.3)[0] if rows.size else []
        if len(cols):
            asc_lefts.append(l + cols.min() - int(round(a)))
    asc_left = min(asc_lefts)
    desc_bottom = max(bottom(cp) for cp in (0x0E0E, 0x0E0F))
    entries = {}   # code point -> dict(M=..., l, t, adv, src)  (src = shared bitmap key)
    for cp in THAI:
        M, l, t, a = g[cp]
        e = {'bmp': cp, 'l': l, 't': t, 'adv': 0 if cp in MARKS else int(round(a))}
        if cp in TONES:
            # cmap tone = high position (above an upper vowel); low forms live in the PUA
            e['t'] = t + (upper_top - gap) - bottom(cp)
        entries[cp] = e
    bitmaps = {cp: g[cp][0] for cp in THAI}
    def right(cp): return g[cp][1] + g[cp][0].shape[1]
    def left_shift(cp): return min(0, asc_left - gap - right(cp))
    for pua, (base, kind) in thai_pua.PUA_FORMS.items():
        b = ord(base)
        M, l, t, a = g[b]
        if kind == 'descless':
            cut = max(1, int(round(size * 0.03)))
            keep = max(0, min(M.shape[0], cut - t))
            bitmaps[pua] = M[:keep].copy()
            entries[pua] = {'bmp': pua, 'l': l, 't': t, 'adv': int(round(a))}
            continue
        e = dict(entries[b])
        if b in TONES:
            low_t = upper_bottom - (bottom(b) - t)  # bottom aligned with the bottom of upper vowels (just above consonant)
            low_t = min(low_t, cons_top - gap - (bottom(b) - t))
            if kind == 'low':
                e['t'] = low_t
            elif kind == 'lowleft':
                e['t'] = low_t; e['l'] = l + left_shift(b)
            elif kind == 'left':
                e['l'] = l + left_shift(b)
        elif b in LOWER and kind == 'low':
            e['t'] = max(t, desc_bottom + gap)
        elif kind == 'left':
            e['l'] = l + left_shift(b)
        entries[pua] = e
    return entries, bitmaps

# ---------------------------------------------------------------- packing
def pack(sizes, W0, H0, spacing=2):
    """sizes: {key:(w,h)}. Returns (W,H,{key:(x,y)}) keeping [0,W0)x[0,H0) untouched."""
    order = sorted(sizes, key=lambda k: (-sizes[k][1], -sizes[k][0]))
    for W, H in ((W0, H0 * 2), (W0 * 2, H0), (W0 * 2, H0 * 2), (W0 * 2, H0 * 4), (W0 * 4, H0 * 4)):
        regions = []
        if H > H0: regions.append([0, H0, W, H])
        if W > W0: regions.append([W0, 0, W, H0])
        pos = {}
        ok = True
        shelves = [[r, r[0] + spacing, r[1] + spacing, 0] for r in regions]  # region, cx, cy, shelf height
        for k in order:
            w, h = sizes[k]
            placed = False
            for sh in shelves:
                (rx0, ry0, rx1, ry1), cx, cy, shh = sh
                if cx + w + spacing > rx1:
                    cx, cy, shh = rx0 + spacing, cy + shh + spacing, 0
                if cy + h + spacing <= ry1 and cx + w + spacing <= rx1:
                    pos[k] = (cx, cy)
                    sh[1], sh[2], sh[3] = cx + w + spacing, cy, max(shh, h)
                    placed = True
                    break
            if not placed:
                ok = False; break
        if ok:
            return W, H, pos
    raise RuntimeError('cannot pack')

# ---------------------------------------------------------------- .fnt writing
FIELD = re.compile(r'(\w+)=(-?\d+)(\s*)')

def format_like(template, values):
    def sub(m):
        k, v, sp = m.group(1), m.group(2), m.group(3)
        if k not in values:
            return m.group(0)
        tok = '%s=%d' % (k, values[k])
        width = len(k) + 1 + len(v) + len(sp)
        if sp == '':
            return tok
        return tok + ' ' * max(1, width - len(tok))
    return FIELD.sub(sub, template)

def write_fnt(fnt, new_chars, W, H, path):
    lines = list(fnt.lines)
    nl = '\r\n' if fnt.crlf else '\n'
    tmpl = lines[fnt.char_line_idx[-1]]
    new_lines = {cid: format_like(tmpl, dict(id=cid, **vals)) for cid, vals in new_chars.items()}
    ids_in_order = [int(re.search(r'id=(-?\d+)', lines[i]).group(1)) for i in fnt.char_line_idx]
    sorted_ok = ids_in_order == sorted(ids_in_order)
    pending = sorted(new_lines)
    out = []
    last_char = fnt.char_line_idx[-1]
    for i, l in enumerate(lines):
        tag = l.split(None, 1)[0] if l.strip() else ''
        if tag == 'common':
            l = re.sub(r'scaleW=\d+', 'scaleW=%d' % W, l)
            l = re.sub(r'scaleH=\d+', 'scaleH=%d' % H, l)
        elif tag == 'chars':
            l = re.sub(r'count=(\d+)', lambda m: 'count=%d' % (int(m.group(1)) + len(new_lines)), l)
        elif tag == 'char' and sorted_ok:
            cid = int(re.search(r'id=(-?\d+)', l).group(1))
            while pending and pending[0] < cid:
                out.append(new_lines[pending.pop(0)])
        out.append(l)
        if i == last_char:
            while pending:
                out.append(new_lines[pending.pop(0)])
    text = nl.join(out)
    if fnt.text.endswith(('\n', '\r')):
        text += nl
    open(path, 'wb').write(text.encode('latin-1'))

# ---------------------------------------------------------------- main
def process(src_dir, name, log):
    fnt = Fnt(os.path.join(src_dir, name + '.fnt'))
    imgs = []
    for ext in ('.dds', '.tga'):
        p = os.path.join(src_dir, name + ext)
        if os.path.exists(p):
            im, info = read_any(p)
            imgs.append((ext, p, im, info))
    if not imgs:
        log[name] = 'NO ATLAS FOUND - skipped'; return
    W0, H0 = imgs[0][2].size
    assert all(i[2].size == (W0, H0) for i in imgs)
    if (W0, H0) != (fnt.scaleW, fnt.scaleH):
        print('  note: atlas %dx%d vs fnt scale %dx%d' % (W0, H0, fnt.scaleW, fnt.scaleH))
    sample = set(range(0x41, 0x5B)) | set(range(0x61, 0x7B)) | set(range(0x410, 0x450))
    styles = [st.analyze(im, fnt, sample) for _, _, im, _ in imgs]
    prim = imgs[0]
    xh, stem = latin_metrics(fnt, prim[2], styles[0])
    face = pick_face(name, fnt.info)
    mono = all(s.get('binary') for s in styles)
    thaiglyph.MONO = mono
    size, wght = choose_size_weight(face, xh * (1.12 if mono else 1.0), stem)
    if 'ubuntu' in fnt.info.get('face', '').lower() and fnt.info.get('bold') == '1':
        wght = max(wght, 600)
    entries, bitmaps = build_glyphs(face, size, wght)
    m = max(st.margin(s) for s in styles)
    sizes = {k: (b.shape[1] + 2 * m, b.shape[0] + 2 * m) for k, b in bitmaps.items()}
    W, H, pos = pack(sizes, W0, H0)
    new_chars = {}
    for cp, e in entries.items():
        k = e['bmp']; (x, y) = pos[k]; (w, h) = sizes[k]
        new_chars[cp] = dict(x=x, y=y, width=w, height=h, xoffset=e['l'] - m,
                             yoffset=fnt.base + e['t'] - m, xadvance=e['adv'], page=0, chnl=15)
    for (ext, p, im, info), sty in zip(imgs, styles):
        if sty['kind'] == 'L':
            canvas = Image.new('L', (W, H), 0)
        else:
            bg = tuple(int(round(v)) for v in sty['bg'])
            canvas = Image.new('RGBA', (W, H), bg + (0,))
        canvas.paste(im, (0, 0))
        for k, b in bitmaps.items():
            Mp = np.pad(b, m)
            enc = st.encode(Mp, sty)
            tile = Image.fromarray(enc, 'L' if sty['kind'] == 'L' else 'RGBA')
            canvas.paste(tile, pos[k])
        # safety: original region must be byte-identical
        orig = np.asarray(im); new = np.asarray(canvas)[:H0, :W0]
        assert np.array_equal(orig, new), 'original region changed!'
        outp = os.path.join(OUT, name + ext)
        if ext == '.dds':
            write_dds(outp, canvas, dds_mipcount(p))
        else:
            write_tga(outp, canvas, info)
    write_fnt(fnt, new_chars, W, H, os.path.join(OUT, name + '.fnt'))
    log[name] = dict(face=face, size=round(size, 2), wght=wght, xh=int(xh), stem=None if stem is None else round(stem, 2),
                     atlas='%dx%d -> %dx%d' % (W0, H0, W, H), styles=[s['kind'] for s in styles], mono=mono,
                     files=[name + '.fnt'] + [name + i[0] for i in imgs])
    print(name, log[name])

def main():
    src = sys.argv[1]
    only = sys.argv[2:]
    os.makedirs(OUT, exist_ok=True)
    log = {}
    for fn in sorted(os.listdir(src)):
        if not fn.endswith('.fnt'):
            continue
        name = fn[:-4]
        if only and name not in only:
            continue
        if name in SKIP:
            log[name] = 'skipped: ' + SKIP[name]; print(name, log[name]); continue
        process(src, name, log)
    lp = os.path.join(ROOT, 'build_log.json')
    old = json.load(open(lp)) if (only and os.path.exists(lp)) else {}
    old.update(log)
    json.dump(old, open(lp, 'w'), indent=1, ensure_ascii=False)

if __name__ == '__main__':
    main()
