"""Scarica le immagini di anteprima delle carte One Piece e ne fa una copia leggera (webp).

I server Bandai non permettono di mostrare le loro immagini su altri siti
(cross-origin-resource-policy: same-site), quindi il sito usa una copia propria.
Scarica solo le immagini che mancano, un po' per volta, per non sovraccaricare Bandai.

Uso: python scripts/op_images.py <op.json> <cartella immagini> [massimo per esecuzione]
"""
import io, json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

URL = 'https://en.onepiece-cardgame.com/images/cardlist/card/{}.png'
WIDTH = 360


def get(code, out_dir):
    dest = os.path.join(out_dir, code + '.webp')
    try:
        req = urllib.request.Request(URL.format(code), headers={'User-Agent': 'collezione-tcg/1.0 (copia immagini anteprima)'})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
        im = Image.open(io.BytesIO(data)).convert('RGB')
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
        im.save(dest, 'WEBP', quality=78, method=6)
        time.sleep(0.2)
        return True
    except Exception as e:  # immagine non disponibile: riproveremo la prossima volta
        print('non scaricata', code, e)
        return False


def main(op_json, out_dir, limit=2500):
    os.makedirs(out_dir, exist_ok=True)
    cards = json.load(open(op_json, encoding='utf-8'))['cards']
    codes = sorted({r[9][2:] for r in cards if len(r) > 9 and str(r[9]).startswith('B:')})
    missing = [c for c in codes if not os.path.exists(os.path.join(out_dir, c + '.webp'))]
    todo = missing[:int(limit)]
    with ThreadPoolExecutor(4) as ex:
        ok = sum(ex.map(lambda c: get(c, out_dir), todo))
    print(f'Immagini One Piece: {len(codes)} necessarie, {len(codes) - len(missing) + ok} presenti, {ok} scaricate ora')


if __name__ == '__main__':
    main(*sys.argv[1:])
