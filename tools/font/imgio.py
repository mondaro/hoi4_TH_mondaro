"""Atlas image I/O: read DDS (uncompressed 32bpp or DXT via Pillow) and TGA; write DDS 32bpp BGRA / TGA."""
import struct
from PIL import Image

def read_dds(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'DDS '
    h, w = struct.unpack('<II', b[12:20])
    pflags, fourcc, bits, rm, gm, bm, am = struct.unpack('<I4sIIIII', b[80:108])
    if pflags & 0x4:  # fourcc -> let Pillow decode
        im = Image.open(path); im.load()
        return im.convert('RGBA'), {'kind': 'dds', 'src_fourcc': fourcc.decode()}
    assert bits == 32 and (rm, gm, bm, am) == (0xff0000, 0xff00, 0xff, 0xff000000), path
    data = b[128:128 + w * h * 4]
    im = Image.frombytes('RGBA', (w, h), data, 'raw', 'BGRA')
    return im, {'kind': 'dds', 'src_fourcc': None}

def dds_mipcount(path):
    b = open(path, 'rb').read(32)
    flags, = struct.unpack('<I', b[8:12]); mc, = struct.unpack('<I', b[28:32])
    return mc if (flags & 0x20000) and mc > 1 else 1

def write_dds(path, im, mips=1):
    im = im.convert('RGBA')
    w, h = im.size
    DDSD = 0x1 | 0x2 | 0x4 | 0x1000  # CAPS|HEIGHT|WIDTH|PIXELFORMAT
    if mips > 1: DDSD |= 0x20000
    hdr = bytearray(128)
    hdr[0:4] = b'DDS '
    struct.pack_into('<IIIIIII', hdr, 4, 124, DDSD, h, w, w * 4, 0, mips if mips > 1 else 0)
    # pixel format at offset 76
    struct.pack_into('<II4sIIIII', hdr, 76, 32, 0x1 | 0x40, b'\0\0\0\0', 32,
                     0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000)
    struct.pack_into('<I', hdr, 108, 0x1000 | ((0x400000 | 0x8) if mips > 1 else 0))
    with open(path, 'wb') as f:
        f.write(bytes(hdr))
        f.write(im.tobytes('raw', 'BGRA'))
        cur = im
        for _ in range(mips - 1):
            cur = cur.resize((max(1, cur.width // 2), max(1, cur.height // 2)), Image.BOX)
            f.write(cur.tobytes('raw', 'BGRA'))

def read_tga(path):
    b = open(path, 'rb').read(18)
    info = {'kind': 'tga', 'type': b[2], 'bpp': b[16], 'desc': b[17], 'footer': open(path, 'rb').read()[-18:] == b'TRUEVISION-XFILE.\0'}
    im = Image.open(path); im.load()
    info['mode'] = im.mode
    return im.convert('RGBA') if im.mode not in ('L',) else im, info

def write_tga(path, im, info):
    """Uncompressed TGA keeping original type/bpp/origin. im is RGBA (or L for type 3)."""
    w, h = im.size
    top = bool(info['desc'] & 0x20)
    if info['type'] == 3:
        im = im.convert('L') if im.mode != 'L' else im
        pix = im.tobytes() if top else im.transpose(Image.FLIP_TOP_BOTTOM).tobytes()
        hdr = struct.pack('<BBBHHBHHHHBB', 0, 0, 3, 0, 0, 0, 0, 0, w, h, 8, info['desc'])
    else:
        im = im.convert('RGBA')
        src = im if top else im.transpose(Image.FLIP_TOP_BOTTOM)
        pix = src.tobytes('raw', 'BGRA')
        hdr = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, w, h, 32, info['desc'])
    with open(path, 'wb') as f:
        f.write(hdr); f.write(pix)
        if info.get('footer'):
            f.write(b'\0' * 8 + b'TRUEVISION-XFILE.\0')

def read_any(path):
    return read_dds(path) if path.lower().endswith('.dds') else read_tga(path)
