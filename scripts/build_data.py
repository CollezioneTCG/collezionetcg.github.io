"""Aggiornamento notturno dei prezzi.

1. Scarica dai file pubblici di Cardmarket il catalogo e il listino prezzi di ogni gioco.
2. Crea i file compatti usati dal sito (out/data/<gioco>.json).
3. Aggiunge il prezzo del giorno allo storico (cartella storico, divisa in tanti piccoli file).

Uso:
  python scripts/build_data.py --out site_build/data --history storico
  python scripts/build_data.py --local <cartella con i file già scaricati> ...   (per prove)
"""
import argparse, collections, json, os, re, sys, urllib.request

BASE = 'https://downloads.s3.cardmarket.com/productCatalog'
# gioco: (id Cardmarket, nome campo reverse/foil nel listino, numero di file dello storico)
GAMES = {
    'pk': (6, 'holo', 4000),
    'op': (18, 'foil', 1000),
}
HISTORY_DAYS = 365
PO = 10  # posizione del primo prezzo in ogni riga
# riga: [id, nome, set, versione, numero, extra, nome italiano, solo giapponese, parole chiave, immagine, prezzi...]
OP_SETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data-src', 'op_sets.json')
JP = re.compile('[぀-ヿ一-鿿가-힯]')


def fetch(url, local_dir=None):
    name = url.rsplit('/', 1)[1]
    if local_dir:
        for f in os.listdir(local_dir):
            if f.endswith(name):
                return json.load(open(os.path.join(local_dir, f), encoding='utf-8'))
        raise FileNotFoundError(name)
    req = urllib.request.Request(url, headers={'User-Agent': 'collezione-tcg/1.0 (aggiornamento giornaliero)'})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def r2(x):
    return None if x in (None, 0) else round(x, 2)


def build_game(g, local_dir, tcgdex):
    gid, hk, _ = GAMES[g]
    products = fetch(f'{BASE}/productList/products_singles_{gid}.json', local_dir)['products']
    pg = fetch(f'{BASE}/priceGuide/price_guide_{gid}.json', local_dir)
    guide = {x['idProduct']: x for x in pg['priceGuides']}
    date = (pg.get('createdAt') or '')[:10]

    prod_map = {int(k): v for k, v in (tcgdex or {}).get('prod', {}).items()}
    exp_map = {}
    for k, v in (tcgdex or {}).get('exp', {}).items():
        exp_map[int(k)] = v if isinstance(v, list) else [v, '']
    op_sets = {}
    if g == 'op' and os.path.exists(OP_SETS):
        op_sets = json.load(open(OP_SETS, encoding='utf-8'))
    if g == 'pk':
        votes = collections.defaultdict(collections.Counter)
        for p in products:
            if p['idProduct'] in prod_map:
                votes[p['idExpansion']][prod_map[p['idProduct']][0]] += 1
        for e, cnt in votes.items():
            if e not in exp_map:
                name, k = cnt.most_common(1)[0]
                if k / sum(cnt.values()) >= 0.6:
                    exp_map[e] = [name, '']

    op_img = {}
    if g == 'op':
        # Immagini ufficiali Bandai: solo per le carte stampate nel loro set d'origine
        # (es. OP05-119 nell'espansione OP05). Lì le versioni, in ordine, sono:
        # base -> CODICE, 1ª alternativa -> CODICE_p1, 2ª -> CODICE_p2 ...
        code_of = lambda n: (re.search(r'\(([A-Z]+\d*-\d+)\)', n) or [None, None])[1]
        prefix = collections.defaultdict(collections.Counter)
        for p in products:
            c = code_of(p['name'])
            if c:
                prefix[p['idExpansion']][c.split('-')[0]] += 1
        dom = {e: c.most_common(1)[0][0] for e, c in prefix.items()}
        groups = collections.defaultdict(list)
        for p in products:
            c = code_of(p['name'])
            if c and dom.get(p['idExpansion']) == c.split('-')[0]:
                groups[(p['idExpansion'], c)].append(p['idProduct'])
        for (e, c), ids in groups.items():
            for k, pid in enumerate(sorted(ids)):
                op_img[pid] = 'B:' + c + ('' if k == 0 else f'_p{k}')

    rows = []
    for p in sorted(products, key=lambda p: p['idProduct']):
        q = guide.get(p['idProduct'])
        if not q:
            continue
        n = [r2(q.get('trend')), r2(q.get('avg7')), r2(q.get('avg30'))]
        h = [r2(q.get('trend-' + hk)), r2(q.get('avg7-' + hk)), r2(q.get('avg30-' + hk))]
        if not n[0] and not h[0]:
            continue
        if g == 'pk':
            m = prod_map.get(p['idProduct'])
            if m:
                setn, num, extra, it, asia, kw, img = (list(m) + ['', ''])[:7]
            else:
                setn, kw = exp_map.get(p['idExpansion'], ['Set #%d' % p['idExpansion'], ''])
                num, extra, it, asia, img = '', '', '', 0, ''
            base = re.sub(r'\s*\[.*$', '', p['name']).strip().lower()
            if it and it.strip().lower() == base:
                it = ''
            jp = 1 if asia or JP.search(setn) else 0
        else:
            m = re.search(r'\(([A-Z0-9]+-\d+)\)', p['name'])
            num = m.group(1) if m else ''
            code = re.search(r'\(([A-Z]+\d*)-\d+\)', p['name'])
            code = code.group(1) if code else ''
            if code == 'P':
                setn, kw = 'Promo', 'P'
            elif code in op_sets:
                setn, kw = f'{op_sets[code]} ({code})', code
            elif code.startswith('ST'):
                setn, kw = f'Starter Deck ({code})', code + ' starter deck'
            else:
                setn, kw = code or 'Altro', code
            extra, it, jp = '', '', 0
            img = op_img.get(p['idProduct'], '')
        rows.append([p['idProduct'], p['name'], setn, 0, num, extra, it, jp, kw, img] + n + (h if h[0] else []))

    key = lambda r: (r[1], r[2], r[4], r[5])
    cnt = collections.Counter(key(r) for r in rows)
    seen = collections.Counter()
    for r in rows:
        k = key(r)
        if cnt[k] > 1:
            seen[k] += 1
            r[3] = seen[k]
    # Prodotti sigillati (box, buste, ETB...): stessi prezzi del listino, nomi dal catalogo "nonsingles"
    sealed = 0
    try:
        ns = fetch(f'{BASE}/productList/products_nonsingles_{gid}.json', local_dir)['products']
    except Exception as e:
        print('catalogo sigillati non disponibile:', e)
        ns = []
    for p in sorted(ns, key=lambda p: p['idProduct']):
        q = guide.get(p['idProduct'])
        if not q:
            continue
        n = [r2(q.get('trend')), r2(q.get('avg7')), r2(q.get('avg30'))]
        if not n[0]:
            continue
        cat = re.sub(r'^(Pokémon|One Piece)\s+', '', p.get('categoryName') or 'Prodotto sigillato')
        # colonna 7 = 2 indica un prodotto sigillato
        rows.append([p['idProduct'], p['name'], cat, 0, '', '', '', 2, cat] + [''] + n)
        sealed += 1
    print(f'{g}: {sealed} prodotti sigillati')
    return date, rows


def update_history(g, date, rows, hist_dir):
    shards = GAMES[g][2]
    gdir = os.path.join(hist_dir, g)
    os.makedirs(gdir, exist_ok=True)
    today = collections.defaultdict(dict)
    for r in rows:
        s = r[0] % shards
        if r[PO]:
            today[s][str(r[0])] = r[PO]
        if len(r) > PO + 3 and r[PO + 3]:
            today[s][str(r[0]) + 'h'] = r[PO + 3]
    for s in range(shards):
        path = os.path.join(gdir, f'{s}.json')
        try:
            h = json.load(open(path, encoding='utf-8'))
        except (FileNotFoundError, ValueError):
            h = {'d': [], 'v': {}}
        if h['d'] and h['d'][-1] == date:
            idx = len(h['d']) - 1          # stesso giorno: sovrascrive
        else:
            h['d'].append(date)
            idx = len(h['d']) - 1
            for k in h['v']:
                h['v'][k].append(None)
        for k, val in today.get(s, {}).items():
            if k not in h['v']:
                h['v'][k] = [None] * len(h['d'])
            h['v'][k][idx] = val
        extra = len(h['d']) - HISTORY_DAYS
        if extra > 0:
            h['d'] = h['d'][extra:]
            h['v'] = {k: v[extra:] for k, v in h['v'].items()}
        h['v'] = {k: v for k, v in h['v'].items() if any(x is not None for x in v)}
        json.dump(h, open(path, 'w', encoding='utf-8'), separators=(',', ':'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True, help='cartella dove scrivere <gioco>.json')
    ap.add_argument('--history', required=True, help='cartella dello storico prezzi')
    ap.add_argument('--tcgdex', default='data-src/pk_tcgdex.json')
    ap.add_argument('--local', help='usa file già scaricati invece di Cardmarket')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    tcgdex = json.load(open(a.tcgdex, encoding='utf-8')) if os.path.exists(a.tcgdex) else None
    for g in GAMES:
        date, rows = build_game(g, a.local, tcgdex if g == 'pk' else None)
        json.dump({'date': date, 'cards': rows}, open(os.path.join(a.out, g + '.json'), 'w', encoding='utf-8'),
                  separators=(',', ':'), ensure_ascii=False)
        update_history(g, date, rows, a.history)
        print(f'{g}: {len(rows)} carte, prezzi del {date}')


if __name__ == '__main__':
    sys.exit(main())
