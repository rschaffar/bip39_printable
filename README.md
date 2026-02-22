# BIP39 Printable Wordlist

A printable, coin-flip-friendly layout of the BIP39 English wordlist (2048 words) across 4 A4 pages.

## Layout

Each word's 11-bit index is split into four visual levels:

| Bits | Level | How to find it |
|------|-------|----------------|
| 2 | Page (1 of 4) | Pick the right page |
| 3 | Row band (1 of 8) | Scan down to the colored band |
| 3 | Column (1 of 8) | Scan right to the column |
| 3 | Word (1 of 8) | Find the word in the group |

Each level uses dark/light bit-blocks for visual pattern matching -- throw coins (heads=dark, tails=light) and match the pattern directly.

The 8 row bands per page have distinct background colors for quick scanning.

## Generating the PDF

Requires Python 3 and `reportlab`.

```sh
# NixOS
nix-shell -p python3Packages.reportlab --run "python3 bip39_pages.py"

# pip
pip install reportlab
python3 bip39_pages.py
```

Produces `bip39_wordlist.pdf`.

## Files

- `english.txt` -- BIP39 English wordlist (2048 words)
- `bip39_pages.py` -- Generator script
- `bip39_wordlist.pdf` -- Pre-built PDF

## License

MIT
