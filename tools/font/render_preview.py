"""Render text with a BMFont (.fnt + atlas) exactly like a simple BMFont engine:
glyph drawn at (cursor + xoffset, line_top + yoffset); cursor += xadvance (+ kerning).

usage: python3 -I tools/render_preview.py [out.png]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
from PIL import Image, ImageDraw
from bmfont import Fnt, parse_line
from imgio import read_any
import thai_pua

FONTS = os.path.join(ROOT, 'gfx', 'fonts')

def load(name):
    f = Fnt(os.path.join(FONTS, name + '.fnt'))
    for ext in ('.dds', '.tga'):
        p = os.path.join(FONTS, name + ext)
        if os.path.exists(p):
            im, _ = read_any(p)
            im = im.convert('RGBA') if im.mode != 'L' else Image.merge('RGBA', [Image.new('L', im.size, 255)] * 3 + [im])
            break
    assert im.size == (f.scaleW, f.scaleH), (name, im.size, f.scaleW, f.scaleH)
    kern = {}
    for l in f.lines:
        tag, d = parse_line(l)
        if tag == 'kerning':
            kern[(int(d['first']), int(d['second']))] = int(d['amount'])
    return f, im, kern

def draw_text(canvas, x, y, text, font, missing):
    f, im, kern = font
    cx = x
    prev = None
    for ch in text:
        cp = ord(ch)
        c = f.chars.get(cp)
        if c is None:
            missing.add(cp); prev = None; continue
        if prev is not None:
            cx += kern.get((prev, cp), 0)
        if c['width'] > 0 and c['height'] > 0:
            g = im.crop((c['x'], c['y'], c['x'] + c['width'], c['y'] + c['height']))
            canvas.alpha_composite(g, (cx + c['xoffset'], y + c['yoffset']))
        cx += c['xadvance']
        prev = cp
    return cx

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'preview.png')
    names = ['hoi_18mbs', 'hoi_20bs', 'hoi_16mbs', 'hoi_36header', 'hoi_24header', 'hoi_22typewriter',
             'vic_22', 'hoi_16tooltip3', 'standard_18']
    names += [n for n in sys.argv[2:]]
    text = 'Hearts of Iron ประเทศไทย ที่นี่ ปู่ ฟ้า ญี่ปุ่น น้ำ กรุงเทพฯ สงครามโลกครั้งที่สอง'
    shaped = thai_pua.apply(text)
    fonts = [(n, load(n)) for n in names]
    scale = 2
    rows = []
    for n, font in fonts:
        f = font[0]
        h = f.lineHeight + 24
        row = Image.new('RGBA', (1400, h), (24, 28, 34, 255))
        missing = set()
        draw_text(row, 8, 12, shaped, font, missing)
        # baseline + line box guides
        d = ImageDraw.Draw(row)
        rows.append((n, row, missing))
    W = max(r[1].width for r in rows) * scale
    label_h = 14
    H = sum(r[1].height * scale + label_h for r in rows)
    canvas = Image.new('RGBA', (W, H), (24, 28, 34, 255))
    d = ImageDraw.Draw(canvas)
    y = 0
    for n, row, missing in rows:
        d.text((6, y + 1), n + ('  MISSING: ' + ' '.join('%04X' % m for m in sorted(missing)) if missing else ''), fill=(150, 160, 170, 255))
        y += label_h
        canvas.paste(row.resize((row.width * scale, row.height * scale), Image.NEAREST), (0, y))
        y += row.height * scale
    # trim right side
    bbox = canvas.getbbox()
    canvas.convert('RGB').save(out)
    print('wrote', out, canvas.size)

if __name__ == '__main__':
    main()
