"""Thai glyphs for the map label font: black core (alpha 128) + soft white halo (alpha ~70), with mipmaps."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import numpy as np
from PIL import Image
from scipy import ndimage
import build as B
from bmfont import Fnt
from imgio import read_dds, write_dds, dds_mipcount
src = sys.argv[1]; name = 'hoi_mapfont4'
fnt = Fnt(os.path.join(src, name + '.fnt')); p = os.path.join(src, name + '.dds')
im, _ = read_dds(p); W0, H0 = im.size
c = fnt.chars[0x78]; A = np.asarray(im)[c['y']:c['y']+c['height'], c['x']:c['x']+c['width'], 3]
rows = np.nonzero((A >= 120).any(axis=1))[0]; xh = rows.max() - rows.min() + 1
size, _ = B.choose_size_weight('sans', xh, None); wght = 700
entries, bitmaps = B.build_glyphs('sans', size, wght)
m = 4
sizes = {k: (b.shape[1] + 2*m, b.shape[0] + 2*m) for k, b in bitmaps.items()}
W, H, pos = B.pack(sizes, W0, H0)
canvas = Image.new('RGBA', (W, H), (140, 140, 140, 0)); canvas.paste(im, (0, 0))
yy, xx = np.mgrid[-3:4, -3:4]; disk = (xx*xx + yy*yy) <= 9.5
for k, b in bitmaps.items():
    M = np.pad(b.astype(np.float32), m)
    O = ndimage.gaussian_filter(ndimage.grey_dilation(M, footprint=disk), 1.0)
    ag = 128/255 * M; ao = 70/255 * np.clip(O, 0, 1)
    a = ag + ao * (1 - ag)
    rgb = np.where(a > 0, (255 * ao * (1 - ag)) / np.maximum(a, 1e-6), 140)
    tile = np.dstack([rgb, rgb, rgb, a * 255]).round().clip(0, 255).astype(np.uint8)
    canvas.paste(Image.fromarray(tile, 'RGBA'), pos[k])
assert np.array_equal(np.asarray(im), np.asarray(canvas)[:H0, :W0])
new_chars = {}
for cp, e in entries.items():
    k = e['bmp']; (x, y) = pos[k]; (w, h) = sizes[k]
    new_chars[cp] = dict(x=x, y=y, width=w, height=h, xoffset=e['l'] - m, yoffset=fnt.base + e['t'] - m, xadvance=e['adv'], page=0, chnl=15)
write_dds(os.path.join(B.OUT, name + '.dds'), canvas, dds_mipcount(p))
B.write_fnt(fnt, new_chars, W, H, os.path.join(B.OUT, name + '.fnt'))
print('map font ok size=%.1f xh=%d atlas %dx%d -> %dx%d glyphs=%d' % (size, xh, W0, H0, W, H, len(new_chars)))
canvas.crop((0, H0, 1400, H0 + 400)).save('mapfont_thai_preview.png')
