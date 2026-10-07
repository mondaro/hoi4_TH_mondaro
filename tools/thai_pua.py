"""Thai pre-shaping for engines without OpenType shaping (e.g. Hearts of Iron IV BMFont text).

apply(text) rewrites Thai combining marks to the Microsoft/Apple Thai PUA presentation forms
(U+F700-U+F71A) so that a plain "cursor += xadvance" renderer stacks them correctly.
Only Thai code points (U+0E00-U+0E7F) are changed; everything else (ASCII, $VAR$, [Scope.GetName],
section signs, colour codes, newlines ...) is returned untouched.

PUA mapping (standard Windows Thai PUA):
  F700 THO THAN without descender        F70F YO YING without descender
  F701-F704 SARA I/II/UE/UEE  left       F710 MAI HAN-AKAT left
  F711 NIKHAHIT left                     F712 MAITAIKHU left
  F705-F709 MAI EK..THANTHAKHAT low-left F70A-F70E MAI EK..THANTHAKHAT low
  F713-F717 MAI EK..THANTHAKHAT left (high)
  F718-F71A SARA U / SARA UU / PHINTHU low
"""
import re

TALL = set('ปฝฟฬ')          # ป ฝ ฟ ฬ
DESC_CUT = {'ญ': '', 'ฐ': ''}  # ญ ฐ: remove descender before a lower vowel
DESC_LOW = set('ฎฏ')                  # ฎ ฏ: lower vowel goes further down

UPPER = 'ัิีึื็ํ'   # ั ิ ี ึ ื ็ ํ
TONES = '่้๊๋์'               # ่ ้ ๊ ๋ ์
LOWER = 'ฺุู'                           # ุ ู ฺ

UPPER_LEFT = {'ั': '', 'ิ': '', 'ี': '', 'ึ': '',
              'ื': '', '็': '', 'ํ': ''}
TONE_LOW = dict(zip(TONES, ''))
TONE_LOWLEFT = dict(zip(TONES, ''))
TONE_LEFT = dict(zip(TONES, ''))
LOWER_LOW = dict(zip(LOWER, ''))

# every PUA code point a font must provide for apply() output
PUA_FORMS = {
    0xF700: ('ฐ', 'descless'), 0xF70F: ('ญ', 'descless'),
    **{ord(v): (k, 'left') for k, v in UPPER_LEFT.items()},
    **{ord(v): (k, 'low') for k, v in TONE_LOW.items()},
    **{ord(v): (k, 'lowleft') for k, v in TONE_LOWLEFT.items()},
    **{ord(v): (k, 'left') for k, v in TONE_LEFT.items()},
    **{ord(v): (k, 'low') for k, v in LOWER_LOW.items()},
}

_AM = re.compile('([' + TONES + ']*)ำ')

def _is_thai(ch):
    return '฀' <= ch <= '๿'

def apply(text: str) -> str:
    if not any(_is_thai(c) for c in text):
        return text
    # SARA AM: C + [tone] + ำ  ->  C + ํ + [tone] + า  (nikhahit behaves like an upper vowel,
    # so the tone is raised above it; า is an ordinary spacing vowel)
    text = _AM.sub(lambda m: 'ํ' + m.group(1) + 'า', text)
    out = []
    base = None        # current base consonant
    base_idx = -1
    has_upper = False
    for ch in text:
        if not _is_thai(ch):
            base = None
            out.append(ch)
            continue
        if ch in UPPER:
            if base in TALL:
                ch = UPPER_LEFT[ch]
            has_upper = True
        elif ch in TONES:
            if base in TALL:
                ch = TONE_LEFT[ch] if has_upper else TONE_LOWLEFT[ch]
            elif not has_upper:
                ch = TONE_LOW[ch]
        elif ch in LOWER:
            if base in DESC_LOW:
                ch = LOWER_LOW[ch]
            elif base in DESC_CUT and base_idx >= 0:
                out[base_idx] = DESC_CUT[base]
        elif ch == '๎':      # yamakkan: no variant
            pass
        else:                     # any spacing Thai character starts a new cluster
            base = ch
            base_idx = len(out)
            has_upper = False
        out.append(ch)
    return ''.join(out)


def _selftest():
    cases = {
        'ที่นี่': 'ที่นี่',                                   # upper vowel + tone: tone stays high
        'ไทย': 'ไทย',
        'แม่': 'แม',                                   # tone without vowel -> low
        'ปู่': 'ปู',                                    # tall + tone, no upper vowel -> low-left
        'ปี่': 'ป',                           # tall + upper vowel + tone -> both left
        'ฟ้า': 'ฟา',
        'ญี่ปุ่น': 'ญี่ปุน',
        'ญุ': 'ุ',
        'ฐุ': 'ุ',
        'ฎุ': 'ฎ',
        'น้ำ': 'นํ้า',                          # sara am decomposed, tone above nikhahit
        'ทำ': 'ทํา',
        'ป่ำ': 'ปา',
        'กรุงเทพฯ': 'กรุงเทพฯ',
    }
    for src, exp in cases.items():
        got = apply(src)
        assert got == exp, (src, [hex(ord(c)) for c in got], [hex(ord(c)) for c in exp])
    s = '§YHello $COUNTRY$ [ROOT.GetName] \\n 100%§! @THA £pol_power'
    assert apply(s) == s
    mixed = '§Y' + 'ประเทศไทย' + '§! $VAR$ น้ำ'
    r = apply(mixed)
    assert r.startswith('§Y') and '§! $VAR$ ' in r
    assert all(ord(c) < 0x80 or '฀' <= c <= '๿' or 0xF700 <= ord(c) <= 0xF71A or c == '§' for c in r)
    # idempotent
    for src in cases:
        assert apply(apply(src)) == apply(src), src
    return True


if __name__ == '__main__':
    _selftest()
    print('thai_pua self-test OK')
