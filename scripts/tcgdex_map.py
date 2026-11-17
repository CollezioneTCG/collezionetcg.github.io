"""Crea la mappa Cardmarket -> TCGdex (nome set, numero carta, varianti, nome italiano).

Uso: python scripts/tcgdex_map.py <cartella cards-database estratta> data-src/pk_tcgdex.json
Legge i file del database TCGdex (licenza MIT) come semplice testo: non esegue nulla.
"""
import json, os, re, sys


def block(txt, key):
    m = re.search(key + r'\s*:\s*\{', txt)
    if not m:
        return None
    i = j = m.end()
    depth = 1
    while depth and j < len(txt):
        if txt[j] == '{':
            depth += 1
        elif txt[j] == '}':
            depth -= 1
        j += 1
    return txt[i:j - 1]


def sval(b, k):
    if not b:
        return None
    m = re.search(r'\b' + k + r'\s*:\s*["\']([^"\']*)["\']', b)
    return m.group(1) if m else None


def parse(root, asia):
    sets, exp, prod = {}, {}, {}
    for dp, _, fn in os.walk(root):
        for f in fn:
            if not f.endswith('.ts'):
                continue
            p = os.path.join(dp, f)
            base = p[:-3]
            if os.path.isdir(base) and os.path.dirname(p) != root:
                t = open(p, encoding='utf-8').read()
                nm = block(t, 'name')
                name = sval(nm, 'en') or sval(nm, 'it') or sval(nm, 'ja') or os.path.basename(base)
                off = re.search(r'official\s*:\s*(\d+)', block(t, 'cardCount') or '')
                cm = re.search(r'cardmarket\s*:\s*(\d+)', block(t, 'thirdParty') or '')
                ab = re.search(r'official\s*:\s*["\']([^"\']+)["\']', block(t, 'abbreviations') or '')
                sid = re.search(r'\bid\s*:\s*["\']([^"\']+)["\']', t)
                kw = []
                for k in (ab.group(1) if ab else None, sid.group(1) if sid else None, sval(nm, 'it')):
                    if k and k.lower() not in [x.lower() for x in kw] and k.lower() != name.lower():
                        kw.append(k)
                sets[base] = {'name': name, 'off': off.group(1) if off else None, 'kw': ' '.join(kw)}
                if cm:
                    exp[int(cm.group(1))] = [name, ' '.join(kw)]
    for base, info in sets.items():
        for f in os.listdir(base):
            if not f.endswith('.ts'):
                continue
            t = open(os.path.join(base, f), encoding='utf-8').read()
            local = f[:-3]
            it = sval(block(t, 'name'), 'it')
            found = []
            vb = re.search(r'variants\s*:\s*\[(.*?)\n\t\]', t, re.S)
            if vb:
                for v in re.split(r'\n\t\t\},?\s*\n\t\t\{', vb.group(1)):
                    cm = re.search(r'cardmarket\s*:\s*(\d+)', v)
                    if not cm:
                        continue
                    extra = []
                    st = re.search(r"stamp\s*:\s*\[([^\]]*)\]", v)
                    fo = re.search(r"foil\s*:\s*['\"]([^'\"]+)['\"]", v)
                    if st:
                        extra.append('timbro ' + re.sub(r"['\"]", '', st.group(1)).replace('-', ' '))
                    if fo:
                        extra.append('foil ' + fo.group(1))
                    found.append((int(cm.group(1)), ', '.join(extra)))
            for cm in re.findall(r'cardmarket\s*:\s*(\d+)', t):
                if int(cm) not in [x[0] for x in found]:
                    found.append((int(cm), ''))
            num = local + ('/' + info['off'] if info['off'] and local.isdigit() else '')
            for cid, extra in found:
                prod.setdefault(cid, [info['name'], num, extra, it or '', 1 if asia else 0, info['kw']])
    return exp, prod


def main(src, out):
    exp, prod = {}, {}
    for sub, asia in (('data', False), ('data-asia', True)):
        d = os.path.join(src, sub)
        if os.path.isdir(d):
            e, p = parse(d, asia)
            for k, v in e.items():
                exp.setdefault(k, v)
            for k, v in p.items():
                prod.setdefault(k, v)
    json.dump({'exp': exp, 'prod': prod}, open(out, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f'TCGdex: {len(exp)} espansioni, {len(prod)} carte collegate')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
