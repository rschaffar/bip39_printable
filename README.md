# BIP39 Printable Wordlist

A printable 5-page layout of the BIP39 English wordlist (2048 words): 4 lookup pages plus 1 manual page. It is designed for fully offline seed phrase generation using physical coin flips. The bit-block layout maps coin outcomes directly to words -- no device needed at any point.

## Why

Software-based seed generation has a large attack surface: compromised RNGs, malware, clipboard sniffers, screen capture, or a backdoored hardware stack. Even an air-gapped computer still requires trusting its entire software and hardware chain.

Physical coin flips are a verifiable entropy source -- the randomness is directly observable. This also avoids having to trust the random-number generator inside a hardware wallet or other device. If that RNG is flawed or badly implemented, the seed it produces may be weaker than you expect. This printable layout eliminates the last digital dependency: looking up the BIP39 word for a given index. That lookup on a screen is an attack surface (screen capture, shoulder-surfing software, process monitoring) that this design removes entirely. The bit-block layout maps coin outcomes directly to words on paper -- no device involved in the generation step. In a private room without cameras, the entire process is unobservable to any remote attacker. There is simply no digital signal to intercept.

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

Important: do **not** reroll just because the result looks too uneven, too balanced, or otherwise unusual. Real randomness naturally produces streaks and lopsided outcomes. Rejecting those results would bias the space of possible seeds.

What matters is that the process itself is neutral. A good manual method:

1. Shake all 11 coins in a closed box or cup.
2. Spill them onto the table without looking at them yet.
3. Take a straight edge (ruler, book spine, sheet of paper) and **slowly sweep it across the spread** -- always in the same direction, e.g. top to bottom, or left to right.
4. The order in which the ruler's edge first touches each coin defines the bit order: first coin touched = bit 1, second = bit 2, ..., eleventh = bit 11.
5. Only then look at each coin's face, in that fixed order, and write down heads/tails.

The ruler sweep is what makes the ordering neutral: position on the table is determined by the spill (random), and the sweep direction is fixed in advance, so you never decide which coin is "next" based on how it landed. If two coins are touched at the same instant, pick consistently (e.g. the leftmost / topmost) -- the rule must be fixed before you look at the faces.

Avoid:

- **Spinning coins on a table.** Spun coins are heavily biased by the coin's center of mass and can land one way 70%+ of the time.
- **Catch-and-slap flips** (catching the coin in mid-air and slapping it onto your wrist). This introduces a small but measurable bias toward the starting face. The bias is too small to meaningfully weaken a 132-bit seed, but the shake-and-spill method avoids the issue entirely.
- **Inspecting and rearranging coins before recording.** If you reorder coins based on how they landed, you have biased the result. Place them in fixed positions without looking at the faces, then read.

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

## Creating a wallet from the sheet

You can also use the sheet to create a BIP39 wallet directly from coin flips, which eliminates the need to trust the random-number generator inside the hardware wallet.

Note on scope: the seed unavoidably becomes digital the moment you type it into a hardware wallet for the recovery/import flow. The point of this method is to keep the *generation* step entirely off any device, so that a compromised RNG, a screen capture, or a malicious process cannot influence or observe the entropy. Pick a hardware wallet you trust for the import, and ideally do the import in the same private setting where you generated the seed -- then wipe any scratch paper.

For a **12-word** wallet, BIP39 defines the mnemonic as **128 bits of entropy plus a 4-bit checksum**. See the **Generating the mnemonic** section of [BIP-0039](https://bips.dev/39/).

That makes the **12th word** special. It is not just another completely free 11-bit choice. Its first **7 bits** still come from your own randomness, but its last **4 bits** are checksum bits that must match the previous entropy.

A practical workflow is:

1. Generate the first 11 words normally from coin flips.
2. Generate the 12th position from coin flips as well, but treat it as a **family of candidates** rather than one final word.
3. Keep the first 7 bits of that last word fixed.
4. Try the **16** possible final words that differ only in the last 4 checksum bits.
5. On a trusted hardware wallet such as a **Trezor**, start the recovery/import flow and test those candidates until the device accepts the phrase.

The hardware wallet is not creating new randomness here. It is only helping you identify which final word has the correct BIP39 checksum, and then restoring the wallet described by your coin flips.

As a rule, avoid using websites or extra software tools just to validate the checksum, unless they are fully offline and truly trusted. The whole point of this method is to avoid leaving a digital trace of the seed. Using the hardware wallet's own restore flow is usually the least invasive place to do that final checksum check.

This same idea works for longer BIP39 mnemonics too, but the number of last-word candidates grows quickly:

- **12 words** = 128-bit entropy + 4-bit checksum → **16** candidates
- **15 words** = 160-bit entropy + 5-bit checksum → **32** candidates
- **18 words** = 192-bit entropy + 6-bit checksum → **64** candidates
- **21 words** = 224-bit entropy + 7-bit checksum → **128** candidates
- **24 words** = 256-bit entropy + 8-bit checksum → **256** candidates

## Backing up the words

This sheet only helps you generate the words. Storing them so they survive fire, theft, loss, and the people who shouldn't have access is a separate problem and is **beyond the scope of this project**. Paper vs. metal backups, memorization, geographic splits, Shamir secret sharing, BIP-85 derivation, and inheritance planning each have their own trade-offs; the right choice depends on the value at stake, who you trust, and how often you need access.

Two things to keep in mind: a seed phrase is permanent -- if you lose it, the funds are unrecoverable, and if someone else finds it (along with the passphrase, if any), they can spend the funds. Plan for both failure modes.

## Exact mapping (optional)

You do not need this to use the sheet. It is only useful if you want to know exactly how the layout maps to the original BIP39 list.

Read the numbered bits from left to right:

- bits **1-2** = page
- bits **3-5** = row
- bits **6-8** = column
- bits **9-11** = word

Interpret **heads/dark = 1** and **tails/light = 0**.

If you want the exact BIP39 list position, read the full 11-bit pattern as a binary number. The BIP39 wordlist counts from 0, so the **Nth** word uses binary(**N-1**).

Example: the **1125th** word is `milk`.

- `1125 - 1 = 1124`
- `1124` in 11-bit binary is `10001100100`
- split into groups: `10 | 001 | 100 | 100`
- so: page `10`, row `001`, column `100`, word `100`

## Generating

Requires Python 3 and `reportlab`. PNG generation additionally requires `pdftoppm` (poppler).

```sh
# NixOS
nix-shell -p python3Packages.reportlab poppler-utils --run "python3 bip39_pages.py"

# pip
pip install reportlab
python3 bip39_pages.py
```

Produces `bip39_wordlist.pdf` and `page_1.png` through `page_5.png`.

## Files

- `english.txt` -- BIP39 English wordlist (2048 words)
- `bip39_pages.py` -- Generator script
- `bip39_wordlist.pdf` -- Pre-built PDF
- `page_{1..5}.png` -- Pre-built page images

## References

- [BIP-0039](https://github.com/bitcoin/bips/blob/master/bip-0039.mediawiki) -- Original spec in the bitcoin/bips repository
- [BIP 39 on bips.dev](https://bips.dev/39/) -- Easy-to-read web mirror of the spec
- [english.txt](https://github.com/bitcoin/bips/blob/master/bip-0039/english.txt) -- Standard BIP-0039 English wordlist from [bitcoin/bips](https://github.com/bitcoin/bips)

## License

MIT
