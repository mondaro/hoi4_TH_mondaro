"""Render single Thai glyphs from Noto (no shaping) and return coverage + ink box relative to origin/baseline."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os
SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'fonts-src')
FACES = {'sans': os.path.join(SRC, 'NotoSansThai-VF.ttf'), 'serif': os.path.join(SRC, 'NotoSerifThai-VF.ttf')}

_cache = {}
def get_font(face, size, wght):
    key = (face, round(size, 3), int(wght))
    if key not in _cache:
        f = ImageFont.truetype(FACES[face], size, layout_engine=ImageFont.Layout.BASIC)
        f.set_variation_by_axes([wght, 100])
        _cache[key] = f
    return _cache[key]

MONO = False
def render(font, ch):
    """returns (M float32 HxW in 0..1, left, top, advance) ; left/top = ink box offset from pen origin on baseline (top negative = above)."""
    size = int(font.size * 3) + 8
    ox, oy = size, size * 2
    im = Image.new('L', (size * 3, size * 3), 0)
    d = ImageDraw.Draw(im)
    if MONO:
        d.fontmode = '1'
    d.text((ox, oy), ch, fill=255, font=font, anchor='ls')
    a = np.asarray(im)
    ys, xs = np.nonzero(a)
    adv = font.getlength(ch)
    if len(xs) == 0:
        return np.zeros((0, 0), np.float32), 0, 0, adv
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    return a[y0:y1, x0:x1].astype(np.float32) / 255.0, int(x0 - ox), int(y0 - oy), adv
