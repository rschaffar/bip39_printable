# BIP39 Printable Wordlist

A printable 4-page layout of the BIP39 English wordlist (2048 words), designed for fully offline seed phrase generation using physical coin flips. The bit-block layout maps coin outcomes directly to words -- no device needed at any point.

## Why

Software-based seed generation has a large attack surface: compromised RNGs, malware, clipboard sniffers, screen capture, or a backdoored hardware stack. Even an air-gapped computer still requires trusting its entire software and hardware chain.

Physical coin flips are a verifiable entropy source -- the randomness is directly observable. This printable layout eliminates the last digital dependency: looking up the BIP39 word for a given index. That lookup on a screen is an attack surface (screen capture, shoulder-surfing software, process monitoring) that this design removes entirely. The bit-block layout maps coin outcomes directly to words on paper -- no device involved at any point. In a private room without cameras, the entire process is unobservable to any remote attacker. There is simply no digital signal to intercept.

## Preview

[![Page 1](page_1.png)](bip39_wordlist.pdf)

## How to look up a word

Flip 11 coins at once. Then arrange them in 4 rows:

```
          ┌─────────────┐
   page   │  ●  ○       │  2 coins
          ├─────────────┤
   row    │  ○  ○  ●    │  3 coins
          ├─────────────┤
   column │  ●  ○  ●    │  3 coins
          ├─────────────┤
   word   │  ○  ●  ●    │  3 coins
          └─────────────┘
          ● = heads (dark)
          ○ = tails (light)
```

Match each row's pattern against the dark/light blocks on the sheet:

1. **Page** -- match the 2-coin pattern to the page title blocks, pick the right page
2. **Row** -- scan down the left margin, find the matching 3-block band
3. **Column** -- scan right along the column headers, find the matching 3-block column
4. **Word** -- within that cell, match the 3-block pattern next to each word

The bit-block layout is designed to make this as fast and error-resistant as possible -- match visual patterns instead of converting binary to decimal or scanning a sorted word list. Each level narrows the search by a fixed factor (4 → 8 → 8 → 8), so the lookup takes seconds.

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

## Generating

Requires Python 3 and `reportlab`. PNG generation additionally requires `pdftoppm` (poppler).

```sh
# NixOS
nix-shell -p python3Packages.reportlab poppler-utils --run "python3 bip39_pages.py"

# pip
pip install reportlab
python3 bip39_pages.py
```

Produces `bip39_wordlist.pdf` and `page_1.png` through `page_4.png`.

## Files

- `english.txt` -- BIP39 English wordlist (2048 words)
- `bip39_pages.py` -- Generator script
- `bip39_wordlist.pdf` -- Pre-built PDF
- `page_{1..4}.png` -- Pre-built page images

## References

- [BIP-0039](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki) -- Mnemonic code for generating deterministic keys
- [english.txt](https://github.com/bitcoin/bips/blob/master/bip-0039/english.txt) -- Standard BIP-0039 English wordlist from [bitcoin/bips](https://github.com/bitcoin/bips)

## License

MIT
