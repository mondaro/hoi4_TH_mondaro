"""Minimal BMFont text-format parser that preserves original lines."""
import re, os

KV = re.compile(r'(\w+)=("[^"]*"|\S+)')

def parse_line(line):
    tag = line.split(None, 1)[0] if line.strip() else ''
    d = {}
    for k, v in KV.findall(line):
        d[k] = v[1:-1] if v.startswith('"') else v
    return tag, d

class Fnt:
    def __init__(self, path):
        self.path = path
        raw = open(path, 'rb').read()
        self.raw = raw
        self.crlf = b'\r\n' in raw
        self.text = raw.decode('latin-1')
        self.lines = self.text.splitlines()
        self.info = self.common = None
        self.page_file = None
        self.chars = {}
        self.char_line_idx = []
        self.chars_count_idx = None
        for i, l in enumerate(self.lines):
            tag, d = parse_line(l)
            if tag == 'info': self.info = d
            elif tag == 'common': self.common = d
            elif tag == 'page': self.page_file = d.get('file')
            elif tag == 'chars': self.chars_count_idx = i
            elif tag == 'char':
                c = {k: int(v) for k, v in d.items() if re.fullmatch(r'-?\d+', v)}
                self.chars[c['id']] = c
                self.char_line_idx.append(i)
        self.base = int(self.common['base'])
        self.lineHeight = int(self.common['lineHeight'])
        self.scaleW = int(self.common['scaleW']); self.scaleH = int(self.common['scaleH'])
