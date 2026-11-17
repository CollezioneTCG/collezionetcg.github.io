# Collezione TCG

Sito per gestire collezioni di carte Pokémon e One Piece e seguirne il valore di mercato.

## Come funziona

- **`site/`** – il sito (una pagina sola, funziona anche da telefono).
- **`scripts/build_data.py`** – ogni notte scarica i file pubblici di Cardmarket (catalogo e listino prezzi), crea i dati del sito e aggiunge il prezzo del giorno allo storico.
- **`scripts/tcgdex_map.py`** – collega le carte Pokémon di Cardmarket al database [TCGdex](https://github.com/tcgdex/cards-database) (licenza MIT) per avere nome del set e numero della carta. Si aggiorna da solo ogni lunedì.
- **`.github/workflows/aggiorna-prezzi.yml`** – l'automazione: gira ogni giorno alle 06:17 (ora italiana), salva lo storico nel ramo `storico` e pubblica il sito su GitHub Pages.

## Fonti dei dati

- Prezzi: listino pubblico di [Cardmarket](https://www.cardmarket.com) (Price Trend, media di tutte le lingue e condizioni). Questo sito non è affiliato con Cardmarket.
- Set e numeri delle carte Pokémon: [TCGdex](https://www.tcgdex.net).
