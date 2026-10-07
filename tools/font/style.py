"""Learn how an existing BMFont atlas encodes glyphs (colour/alpha/outline/shadow) and
apply the same encoding to new coverage masks.

Two models:
  'P' (plain):   alpha = coverage, RGB = LUT[alpha]   (white, black/inverted, grey, RGB=coverage...)
  'O' (outline): glyph layer colour c_g with alpha M, over an effect layer of colour c_s whose alpha
                 S = clip(k * blur(dilate(shift(M)))) - fitted from the existing glyphs.
"""
import numpy as np
from scipy import ndimage

def glyph_crops(arr, fnt, ids=None):
    H, W = arr.shape[:2]
    out = []
    for cid, c in fnt.chars.items():
        if ids is not None and cid not in ids:
            continue
        x, y, w, h = c['x'], c['y'], c['width'], c['height']
        if w <= 0 or h <= 0 or x + w > W or y + h > H:
            continue
        out.append((cid, arr[y:y + h, x:x + w]))
    return out

def _effect(M, dx, dy, r, sigma):
    E = M
    if dx or dy:
        E = ndimage.shift(E, (dy, dx), order=0, mode='constant', cval=0.0)
    if r:
        E = ndimage.grey_dilation(E, footprint=_disk(r))
    if sigma:
        E = ndimage.gaussian_filter(E, sigma, mode='constant')
    return E

_disks = {}
def _disk(r):
    if r not in _disks:
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        _disks[r] = (xx * xx + yy * yy) <= r * r + 0.5
    return _disks[r]

def analyze(img, fnt, sample_ids):
    """img: PIL RGBA (or L). Returns style dict."""
    if img.mode == 'L':
        return {'kind': 'L', 'binary': False}
    arr = np.asarray(img.convert('RGBA')).astype(np.float32)
    A = arr[..., 3]
    lum = arr[..., :3].mean(axis=2)
    crops = glyph_crops(arr, fnt)
    inA = np.concatenate([c[..., 3].ravel() for _, c in crops])
    inL = np.concatenate([c[..., :3].mean(axis=2).ravel() for _, c in crops])
    inRGB = np.concatenate([c[..., :3].reshape(-1, 3) for _, c in crops])
    # background colour of transparent texels (to keep filtering behaviour similar)
    zero = A == 0
    bg = np.median(arr[..., :3][zero], axis=0) if zero.any() else np.array([255, 255, 255])
    binary = np.isin(inA, (0, 255)).mean() > 0.995
    strong = inA >= 128
    mx = np.percentile(inL[strong], 99) if strong.any() else 255
    bright = (inL[strong] > 0.7 * mx).mean() if mx > 20 else 0
    dark = (inL[strong] < 0.3 * mx).mean() if mx > 20 else 0
    # dark halo texels: clearly opaque but much darker than a premultiplied/coverage encoding would give
    mid = inA >= 40
    halo = ((inL[mid] < 0.3 * mx) & (inA[mid] > inL[mid] * 255.0 / max(mx, 1) + 60)).mean() if mx > 20 else 0
    if not ((bright > 0.03 and dark > 0.03) or (bright > 0.03 and halo > 0.05)):
        lut = np.zeros((256, 3), np.float32)
        have = np.zeros(256, bool)
        for v in range(1, 256):
            sel = inA == v
            if sel.sum() >= 3:
                lut[v] = np.median(inRGB[sel], axis=0); have[v] = True
        idx = np.nonzero(have)[0]
        for ch in range(3):
            lut[:, ch] = np.interp(np.arange(256), idx, lut[idx, ch])
        lut[0] = bg
        levels = np.unique(inA)
        return {'kind': 'P', 'lut': lut, 'binary': bool(binary), 'bg': bg, 'levels': levels}
    # ---- outline / shadow model ----
    cg = np.percentile(inRGB[(inA >= 250) & (inL > 0.7 * mx)], 90, axis=0) if ((inA >= 250) & (inL > 0.7 * mx)).any() else np.array([255.] * 3)
    cgl = max(cg.mean(), 1.0)
    samples = []
    for cid, c in crops:
        if cid not in sample_ids:
            continue
        a = c[..., 3] / 255.0
        l = c[..., :3].mean(axis=2)
        M = np.clip(l * a / cgl, 0, 1)
        P = 6
        samples.append((np.pad(M, P), np.pad(a, P)))
    # shadow colour: texels that are opaque-ish but not glyph
    Ms = np.concatenate([s[0].ravel() for s in samples]); As = np.concatenate([s[1].ravel() for s in samples])
    best = None
    for dx in range(-1, 4):
        for dy in range(-1, 4):
            for r in range(0, 4):
                for sigma in (0, 0.6, 1.0, 1.5, 2.0, 3.0):
                    Es = np.concatenate([_effect(m, dx, dy, r, sigma).ravel() for m, _ in samples])
                    for k in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 6.0):
                        S = np.clip(k * Es, 0, 1)
                        Apred = Ms + S * (1 - Ms)
                        err = np.mean((Apred - As) ** 2)
                        if best is None or err < best[0]:
                            best = (err, dx, dy, r, sigma, k)
    err, dx, dy, r, sigma, k = best
    sel = (Ms < 0.05) & (As > 0.5)
    lumall = None
    cs_vals = []
    for cid, c in crops:
        if cid not in sample_ids:
            continue
        a = c[..., 3] / 255.0
        M = np.clip(c[..., :3].mean(axis=2) * a / cgl, 0, 1)
        s = (M < 0.05) & (a > 0.5)
        if s.any():
            cs_vals.append(c[..., :3][s])
    cs = np.median(np.concatenate(cs_vals), axis=0) if cs_vals else np.zeros(3)
    return {'kind': 'O', 'cg': cg, 'cs': cs, 'dx': dx, 'dy': dy, 'r': r, 'sigma': sigma, 'k': k,
            'err': err, 'binary': False, 'bg': bg}

def margin(style):
    if style['kind'] == 'O':
        return int(np.ceil(style['r'] + 3 * style['sigma'] + max(abs(style['dx']), abs(style['dy'])))) + 1
    return 1

def core_mask(img_crop, style):
    """Recover glyph coverage (0..1) from an atlas crop (numpy float RGBA / L)."""
    if style['kind'] == 'L':
        return img_crop / 255.0
    a = img_crop[..., 3] / 255.0
    if style['kind'] == 'P':
        return a
    l = img_crop[..., :3].mean(axis=2)
    return np.clip(l * a / max(style['cg'].mean(), 1), 0, 1)

def encode(M, style):
    """M: coverage already padded by margin(style). Returns uint8 array (H,W,4) or (H,W) for L."""
    if style['kind'] == 'L':
        return np.clip(np.round(M * 255), 0, 255).astype(np.uint8)
    if style['binary']:
        M = (M >= 0.5).astype(np.float32)
    if style['kind'] == 'P':
        A = np.clip(np.round(M * 255), 0, 255).astype(np.int32)
        levels = style['levels']
        if len(levels) < 64:  # quantised alpha (e.g. DXT3 4-bit) -> snap to existing levels
            idx = np.abs(A[..., None] - levels[None, None, :]).argmin(axis=2)
            A = levels[idx].astype(np.int32)
        rgb = style['lut'][A]
        out = np.dstack([np.round(rgb), A]).astype(np.uint8)
        return out
    S = np.clip(style['k'] * _effect(M, style['dx'], style['dy'], style['r'], style['sigma']), 0, 1)
    Aout = M + S * (1 - M)
    with np.errstate(invalid='ignore', divide='ignore'):
        rgb = (style['cg'][None, None, :] * M[..., None] + style['cs'][None, None, :] * (S * (1 - M))[..., None]) / Aout[..., None]
    rgb = np.where(Aout[..., None] > 1e-4, rgb, style['bg'][None, None, :])
    out = np.dstack([np.clip(np.round(rgb), 0, 255), np.clip(np.round(Aout * 255), 0, 255)]).astype(np.uint8)
    return out
