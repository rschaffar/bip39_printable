#!/usr/bin/env python3
"""Generate a nicely organized BIP39 word list as PDF.

Layout: 4 pages × 8 columns × 8 sections × 8 words = 2048 words.

11-bit index split (left to right, matching coin throw order):
  [10:9] 2 bits → page          (page title)
  [8:6]  3 bits → section/row   (left margin)
  [5:3]  3 bits → column        (column header)
  [2:0]  3 bits → word in section (per word)

Coin-throw friendly: colored bit blocks for visual pattern matching.
"""

import shutil
import subprocess

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import mm
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas

WORDS_FILE = "english.txt"
OUTPUT = "bip39_wordlist.pdf"
PNG_PREFIX = "page"
PNG_DPI = 200

PAGES = 4
MANUAL_PAGES = 1
TOTAL_PAGES = PAGES + MANUAL_PAGES
COLS = 8
SECTIONS = 8
WORDS_PER_SECTION = 8

# Layout
PAGE_W, PAGE_H = A4
MARGIN_TOP = 20 * mm   # room for column header
MARGIN_BOTTOM = 6 * mm
LEFT_MARGIN = 14 * mm
MARGIN_RIGHT = 4 * mm
USABLE_W = PAGE_W - LEFT_MARGIN - MARGIN_RIGHT
USABLE_H = PAGE_H - MARGIN_TOP - MARGIN_BOTTOM
COL_W = USABLE_W / COLS
SECTION_H = USABLE_H / SECTIONS
SECTION_LABEL_H = 3 * mm
WORD_ROW_H = (SECTION_H - SECTION_LABEL_H) / WORDS_PER_SECTION

# Fonts
FONT_SIZE = 6.2
TITLE_FONT_SIZE = 11

# Colors for bit blocks
C0 = Color(0.82, 0.82, 0.82)  # 0 = light grey
C1 = Color(0.20, 0.20, 0.20)  # 1 = near-black

# 8 subtle section background colors (row bands)
SECTION_BG = [
    Color(0.97, 0.91, 0.91),  # 000 warm pink
    Color(0.97, 0.94, 0.88),  # 001 peach
    Color(0.96, 0.96, 0.88),  # 010 cream
    Color(0.90, 0.96, 0.90),  # 011 mint
    Color(0.88, 0.95, 0.96),  # 100 ice
    Color(0.89, 0.91, 0.97),  # 101 periwinkle
    Color(0.93, 0.90, 0.97),  # 110 lavender
    Color(0.96, 0.90, 0.95),  # 111 mauve
]

# Alternating column tint factor (applied to odd columns)
COL_TINT = 0.93

BIT_BLOCK_SIZE = 2.2 * mm
BIT_BLOCK_GAP = 0.5 * mm
BIT_BLOCK_SMALL = 1.5 * mm
BIT_BLOCK_SMALL_GAP = 0.3 * mm

# Column header block sizing
COL_BLOCK_SIZE = 2.5 * mm
COL_BLOCK_GAP = 0.5 * mm
COL_BLOCKS_W = 3 * COL_BLOCK_SIZE + 2 * COL_BLOCK_GAP  # total width of 3 blocks

# Row/section block sizing
SEC_BLOCK_SIZE = 2.2 * mm
SEC_BLOCK_GAP = 0.4 * mm

# Page title block sizing
PAGE_BLOCK_SIZE = 3 * mm
PAGE_BLOCK_GAP = 0.8 * mm


def darken(color, factor=COL_TINT):
    """Return a slightly darkened copy of a Color."""
    return Color(color.red * factor, color.green * factor, color.blue * factor)


def draw_bit_blocks(c, x, y, bits, size=None, gap=None, start_num=None):
    """Draw colored squares for each bit at (x, y) bottom-left. Returns total width."""
    sz = size or BIT_BLOCK_SIZE
    gp = gap or BIT_BLOCK_GAP

    if start_num is not None:
        font_name = "Helvetica"
        font_size = max(2.0, sz * 0.45)
        ascent = pdfmetrics.getAscent(font_name, font_size)
        descent = pdfmetrics.getDescent(font_name, font_size)
        baseline = y + (sz - (ascent - descent)) / 2 - descent
        c.setFont(font_name, font_size)

    for i, b in enumerate(bits):
        bx = x + i * (sz + gp)
        color = C1 if b == "1" else C0
        c.setFillColor(color)
        c.setStrokeColor(Color(0.5, 0.5, 0.5))
        c.setLineWidth(0.2)
        c.rect(bx, y, sz, sz, fill=1, stroke=1)

        if start_num is not None:
            c.setFillColor(Color(1, 1, 1) if b == "1" else Color(0, 0, 0))
            c.drawCentredString(bx + sz / 2, baseline, str(start_num + i))

    return len(bits) * sz + (len(bits) - 1) * gp


def wrap_text(text, font_name, font_size, max_width):
    """Wrap a single paragraph to fit max_width."""
    words = text.split()
    if not words:
        return [""]

    lines = [words[0]]
    for word in words[1:]:
        candidate = f"{lines[-1]} {word}"
        if pdfmetrics.stringWidth(candidate, font_name, font_size) <= max_width:
            lines[-1] = candidate
        else:
            lines.append(word)
    return lines


def draw_wrapped_text(c, text, x, y, width, font_name="Helvetica", font_size=8,
                      leading=None, color=Color(0.1, 0.1, 0.1)):
    """Draw wrapped text and return the next y position."""
    leading = leading or font_size * 1.25
    c.setFont(font_name, font_size)
    c.setFillColor(color)

    for paragraph in text.split("\n"):
        if paragraph.strip():
            for line in wrap_text(paragraph, font_name, font_size, width):
                c.drawString(x, y, line)
                y -= leading
        else:
            y -= leading * 0.6

    return y


def draw_coin_arrangement(c, x, y):
    """Draw a 2×2 visual arrangement for placing 11 flipped coins."""
    groups = [
        ("page", 2, 1, "bits 1–2", 0, 0),
        ("column", 3, 6, "bits 6–8", 1, 0),
        ("row", 3, 3, "bits 3–5", 0, 1),
        ("word", 3, 9, "bits 9–11", 1, 1),
    ]
    col_w = 78 * mm
    col_gap = 10 * mm
    label_h = 5 * mm
    box_w = 78 * mm
    box_h = 18 * mm
    row_gap = 7 * mm
    coin_r = 4.7 * mm
    coin_gap = 6.5 * mm

    for label, count, start_num, note, gx, gy in groups:
        left = x + gx * (col_w + col_gap)
        top = y - gy * (label_h + box_h + row_gap)
        box_y = top - label_h - box_h
        cy = box_y + box_h / 2

        c.setFont("Helvetica-Bold", 9)
        c.setFillColorRGB(0.1, 0.1, 0.1)
        c.drawString(left, top - 3, label)
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.35, 0.35, 0.35)
        c.drawRightString(left + box_w, top - 3, note)

        c.setFillColor(Color(0.98, 0.98, 0.98))
        c.setStrokeColor(Color(0.7, 0.7, 0.7))
        c.roundRect(left, box_y, box_w, box_h, 2.5 * mm, fill=1, stroke=1)

        total_w = count * (2 * coin_r) + (count - 1) * coin_gap
        cx = left + (box_w - total_w) / 2 + coin_r
        for n in range(count):
            c.setFillColor(Color(1, 1, 1))
            c.setStrokeColor(Color(0.45, 0.45, 0.45))
            c.circle(cx, cy, coin_r, fill=1, stroke=1)
            c.setFillColorRGB(0.2, 0.2, 0.2)
            c.setFont("Helvetica", 9)
            c.drawCentredString(cx, cy - 3, str(start_num + n))
            cx += 2 * coin_r + coin_gap

    legend_y = y - 2 * (label_h + box_h + row_gap) + 2 * mm
    c.setFillColor(C1)
    c.setStrokeColor(Color(0.4, 0.4, 0.4))
    c.circle(x + 3 * mm, legend_y, 2.2 * mm, fill=1, stroke=1)
    c.setFillColorRGB(0.15, 0.15, 0.15)
    c.setFont("Helvetica", 8)
    c.drawString(x + 8 * mm, legend_y - 2.5, "heads = dark = 1")

    c.setFillColor(C0)
    c.setStrokeColor(Color(0.4, 0.4, 0.4))
    c.circle(x + 53 * mm, legend_y, 2.2 * mm, fill=1, stroke=1)
    c.setFillColorRGB(0.15, 0.15, 0.15)
    c.drawString(x + 58 * mm, legend_y - 2.5, "tails = light = 0")

    return legend_y - 7 * mm


def draw_manual_page(c, words):
    """Draw the manual / rationale page."""
    margin_x = 15 * mm
    top_y = PAGE_H - 16 * mm
    text_w = PAGE_W - 2 * margin_x

    example_num = 1125
    example_idx = example_num - 1
    example_word = words[example_idx]
    example_bits = format(example_idx, "011b")
    page_bits = example_bits[:2]
    row_bits = example_bits[2:5]
    col_bits = example_bits[5:8]
    word_bits = example_bits[8:11]

    c.setFont("Helvetica-Bold", 16)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(margin_x, top_y, "BIP39 Printable Wordlist — Manual")

    y = top_y - 9 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin_x, y, "Why")
    y -= 5 * mm
    y = draw_wrapped_text(
        c,
        "Software-based seed generation has a large attack surface: compromised RNGs, malware, clipboard sniffers, screen capture, or a backdoored hardware stack. Even an air-gapped computer still requires trusting its entire software and hardware chain.",
        margin_x,
        y,
        text_w,
    )
    y -= 2 * mm
    y = draw_wrapped_text(
        c,
        "Physical coin flips are a verifiable entropy source — the randomness is directly observable. This also avoids having to trust the random-number generator inside a hardware wallet or other device. If that RNG is flawed or badly implemented, the generated seed may be weaker than it appears. With this printable layout, you can go from coin flips to words on paper, with no screen or device involved in the generation step.",
        margin_x,
        y,
        text_w,
    )

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 11)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(margin_x, y, "How to use the coin flips")
    y -= 5 * mm
    y = draw_wrapped_text(
        c,
        "Flip 11 coins. Place them left to right into the slots below. Then match each group against the dark/light blocks on the lookup pages. You do not need to convert anything by hand — just match the patterns.",
        margin_x,
        y,
        text_w,
    )
    y -= 2 * mm
    y = draw_wrapped_text(
        c,
        "Do not reroll just because the result looks too uneven, too balanced, or otherwise unusual. A real random process naturally produces streaks and lopsided results. Rejecting those outcomes would bias the space of possible seeds.",
        margin_x,
        y,
        text_w,
    )
    y -= 2 * mm
    y = draw_wrapped_text(
        c,
        "What matters is that the flipping and placement process itself is neutral. A good method: shake all 11 coins in a closed box, spill them onto the table without looking, then slowly sweep a ruler across the spread in a fixed direction (e.g. top to bottom). The order in which the ruler's edge first touches each coin defines the bit order — first touched = bit 1, second = bit 2, and so on through bit 11. Only then read off heads/tails in that fixed order. Do not spin coins on a table — spun coins are biased by their center of mass and can land one way 70%+ of the time. Do not subconsciously pick coins based on how they landed, and do not reorder them after seeing the faces.",
        margin_x,
        y,
        text_w,
    )
    y -= 2 * mm
    y = draw_coin_arrangement(c, margin_x, y)

    y -= 4 * mm
    c.setFont("Helvetica-Bold", 11)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(margin_x, y, "How to create a wallet")
    y -= 5 * mm
    y = draw_wrapped_text(
        c,
        "You can build a BIP39 wallet entirely from your own coin flips, instead of trusting the random-number generator inside a hardware wallet. The idea is simple: use the lookup pages to turn each batch of 11 coin flips into one BIP39 word, repeat for every word in the phrase, and then have a hardware wallet import that phrase as if it had generated it itself.",
        margin_x,
        y,
        text_w,
    )
    y -= 2 * mm
    y = draw_wrapped_text(
        c,
        "There is one subtlety. BIP39 does not let every word be fully random. A 12-word phrase encodes 128 bits of your own entropy plus a 4-bit checksum that BIP39 computes from those 128 bits. The first 11 words are 11 × 11 = 121 bits — fully yours. The 12th word holds the remaining 7 bits of entropy plus the 4 checksum bits, all packed into its 11 bits. So the 12th word is partly random (your last 7 coin flips) and partly determined (the 4 checksum bits, which you cannot choose).",
        margin_x,
        y,
        text_w,
    )
    y -= 2 * mm
    y = draw_wrapped_text(
        c,
        "A practical workflow:",
        margin_x,
        y,
        text_w,
    )
    y -= 1 * mm
    y = draw_wrapped_text(
        c,
        "1. Flip 11 coins for each of the first 11 words and look them up on the sheet.",
        margin_x + 4 * mm,
        y,
        text_w - 4 * mm,
    )
    y = draw_wrapped_text(
        c,
        "2. Flip 11 coins for the 12th word as well, but treat the result as a starting point. Look up the word the sheet gives you.",
        margin_x + 4 * mm,
        y,
        text_w - 4 * mm,
    )
    y = draw_wrapped_text(
        c,
        "3. Keep its first 7 bits fixed — the last 4 are the BIP39 checksum.",
        margin_x + 4 * mm,
        y,
        text_w - 4 * mm,
    )
    y = draw_wrapped_text(
        c,
        "4. On a trusted hardware wallet (e.g. a Trezor), start the recovery / import flow and enter your phrase. Try each of the 16 candidates as the 12th word until the device accepts the phrase. A wrong checksum is rejected immediately; the accepted phrase is your real mnemonic.",
        margin_x + 4 * mm,
        y,
        text_w - 4 * mm,
    )
    y -= 1 * mm
    y = draw_wrapped_text(
        c,
        "The wallet is not adding randomness — your flips already fixed the entropy; it only checks the checksum and derives the wallet from your phrase. The seed becomes digital at this step, which is unavoidable: the goal here is to keep the generation off any device, not the seed's whole lifetime. For the same reason, do the checksum check via the wallet's own restore flow, not a website or other software (unless fully offline and trusted).",
        margin_x,
        y,
        text_w,
    )
    y -= 2 * mm
    y = draw_wrapped_text(
        c,
        "Longer phrases work the same way, with more checksum bits in the last word: 15 words → 32 candidates, 18 → 64, 21 → 128, 24 → 256.",
        margin_x,
        y,
        text_w,
    )

    y -= 3 * mm
    c.setFont("Helvetica-Bold", 11)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(margin_x, y, "Backing up the words")
    y -= 5 * mm
    y = draw_wrapped_text(
        c,
        "This sheet only helps you generate the words. Storing them safely — paper vs. metal, memorization, geographic splits, Shamir secret sharing, inheritance planning — is a separate problem beyond the scope of this project. A seed phrase is permanent: lose it and the funds are unrecoverable; share it (with passphrase, if any) and someone else can spend them.",
        margin_x,
        y,
        text_w,
    )

    y -= 5 * mm
    fine_x = margin_x + 4 * mm
    fine_w = text_w - 4 * mm
    fine_size = 6
    fine_lead = 7.2

    c.setFont("Helvetica-Bold", 7)
    c.setFillColorRGB(0.25, 0.25, 0.25)
    c.drawString(fine_x, y, "Additional detail: exact mapping")
    y -= 3 * mm
    y = draw_wrapped_text(
        c,
        "You do not need to understand this to use the sheet. This is only for someone who wants to know how the printed layout maps to the exact BIP39 index.",
        fine_x,
        y,
        fine_w,
        font_name="Helvetica-Oblique",
        font_size=fine_size,
        leading=fine_lead,
        color=Color(0.3, 0.3, 0.3),
    )
    y -= 0.8 * mm
    y = draw_wrapped_text(
        c,
        "Read the numbered bits from left to right. Heads/dark means 1. Tails/light means 0. Split the 11 bits as 2 | 3 | 3 | 3. Those four groups mean page | row | column | word.",
        fine_x,
        y,
        fine_w,
        font_size=fine_size,
        leading=fine_lead,
        color=Color(0.25, 0.25, 0.25),
    )
    y -= 0.8 * mm
    y = draw_wrapped_text(
        c,
        "If you want the exact BIP39 list position, read the full 11-bit pattern as a binary number. The BIP39 wordlist counts from 0, so the Nth word uses binary(N-1).",
        fine_x,
        y,
        fine_w,
        font_size=fine_size,
        leading=fine_lead,
        color=Color(0.25, 0.25, 0.25),
    )

    y -= 2 * mm
    c.setFont("Helvetica-Bold", 7)
    c.setFillColorRGB(0.25, 0.25, 0.25)
    c.drawString(fine_x, y, f"Example: {example_num}th word")
    y -= 3 * mm
    y = draw_wrapped_text(
        c,
        f"The {example_num}th BIP39 word is '{example_word}'. Take {example_num}-1 = {example_idx}. In 11-bit binary that is {example_bits}, or split up: {page_bits} | {row_bits} | {col_bits} | {word_bits}.",
        fine_x,
        y,
        fine_w,
        font_size=fine_size,
        leading=fine_lead,
        color=Color(0.25, 0.25, 0.25),
    )
    example_block_size = 3.8 * mm
    example_block_gap = 0.7 * mm
    example_group_gap = 2.2 * mm
    example_blocks_y = y - example_block_size

    group_x = fine_x
    for bits, start_num in ((page_bits, 1), (row_bits, 3), (col_bits, 6), (word_bits, 9)):
        draw_bit_blocks(c, group_x, example_blocks_y, bits,
                        size=example_block_size, gap=example_block_gap, start_num=start_num)
        group_w = len(bits) * example_block_size + (len(bits) - 1) * example_block_gap
        group_x += group_w
        if start_num != 9:
            c.setFont("Helvetica-Bold", 9)
            c.setFillColor(Color(0.45, 0.45, 0.45))
            c.drawCentredString(group_x + example_group_gap / 2, example_blocks_y + 0.55 * mm, "|")
            group_x += example_group_gap

    y -= 8 * mm
    draw_wrapped_text(
        c,
        "So on the printed sheet: go to page 10, then row 001, then column 100, then word 100. That lands on 'milk'.",
        fine_x,
        y,
        fine_w,
        font_size=fine_size,
        leading=fine_lead,
        color=Color(0.25, 0.25, 0.25),
    )



def main():
    with open(WORDS_FILE) as f:
        words = [line.strip() for line in f]
    assert len(words) == 2048, f"Expected 2048 words, got {len(words)}"

    c = canvas.Canvas(OUTPUT, pagesize=A4)

    # Y positions for header elements
    title_y = PAGE_H - 10 * mm
    col_header_y = PAGE_H - MARGIN_TOP + 4 * mm  # bottom of column bit blocks

    for page in range(PAGES):
        page_bits = format(page, "02b")

        # --- Page title ---
        page_blocks_x = MARGIN_RIGHT + 18 * mm
        page_blocks_y = title_y - 0.5 * mm

        c.setFont("Helvetica-Bold", TITLE_FONT_SIZE)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(MARGIN_RIGHT, title_y, "BIP39")

        draw_bit_blocks(c, page_blocks_x, page_blocks_y, page_bits,
                        size=PAGE_BLOCK_SIZE, gap=PAGE_BLOCK_GAP, start_num=1)

        # Explanatory text on title level
        after_blocks_x = page_blocks_x + 2 * (PAGE_BLOCK_SIZE + PAGE_BLOCK_GAP) + 3 * mm
        c.setFont("Helvetica", 7)
        c.setFillColorRGB(0.35, 0.35, 0.35)
        c.drawString(after_blocks_x, title_y,
                     "11 coin flips per word:  2 bits page, 3 bits row, 3 bits column, 3 bits word")

        # Horizontal bar separating title from column headers
        bar_y = (title_y + col_header_y + COL_BLOCK_SIZE) / 2
        c.setStrokeColorRGB(0.45, 0.45, 0.45)
        c.setLineWidth(0.8)
        c.line(MARGIN_RIGHT, bar_y, LEFT_MARGIN + USABLE_W, bar_y)

        # --- Column headers (centered horizontally in each column) ---
        for col in range(COLS):
            x = LEFT_MARGIN + col * COL_W
            col_bits = format(col, "03b")

            # Center blocks horizontally in column
            blocks_x = x + (COL_W - COL_BLOCKS_W) / 2
            draw_bit_blocks(c, blocks_x, col_header_y, col_bits,
                            size=COL_BLOCK_SIZE, gap=COL_BLOCK_GAP, start_num=6)

        # --- Sections ---
        sec_blocks_x = MARGIN_RIGHT
        for sec in range(SECTIONS):
            sec_bits = format(sec, "03b")
            section_top = PAGE_H - MARGIN_TOP - sec * SECTION_H

            # Background bands per column (alternating tint on odd columns)
            for col in range(COLS):
                bg = SECTION_BG[sec] if col % 2 == 0 else darken(SECTION_BG[sec])
                col_x = LEFT_MARGIN + col * COL_W
                c.setFillColor(bg)
                c.rect(col_x, section_top - SECTION_H, COL_W, SECTION_H,
                       fill=1, stroke=0)

            # Fine separators after every second column
            c.setStrokeColor(Color(1, 1, 1))
            c.setLineWidth(0.45)
            for boundary in range(2, COLS, 2):
                sep_x = LEFT_MARGIN + boundary * COL_W
                c.line(sep_x, section_top - SECTION_H, sep_x, section_top)

            # Horizontal separator line
            c.setStrokeColorRGB(0.6, 0.6, 0.6)
            c.setLineWidth(0.4)
            c.line(LEFT_MARGIN, section_top, LEFT_MARGIN + USABLE_W, section_top)

            # Left margin: section bit blocks — vertically centered in section band
            blocks_y = section_top - SECTION_H / 2 - SEC_BLOCK_SIZE / 2
            draw_bit_blocks(c, sec_blocks_x, blocks_y, sec_bits,
                            size=SEC_BLOCK_SIZE, gap=SEC_BLOCK_GAP, start_num=3)

            # Words in this section
            for col in range(COLS):
                x = LEFT_MARGIN + col * COL_W

                for w in range(WORDS_PER_SECTION):
                    idx = page * 512 + sec * 64 + col * 8 + w
                    word = words[idx]
                    word_bits = format(w, "03b")
                    y = section_top - SECTION_LABEL_H - w * WORD_ROW_H

                    # Small bit blocks for word
                    draw_bit_blocks(c, x + 0.5 * mm, y + 0.2 * mm, word_bits,
                                    size=BIT_BLOCK_SMALL, gap=BIT_BLOCK_SMALL_GAP, start_num=9)

                    # Word text
                    c.setFont("Courier", FONT_SIZE)
                    c.setFillColorRGB(0.05, 0.05, 0.05)
                    c.drawString(x + 6.5 * mm, y, word)

        c.showPage()

    draw_manual_page(c, words)
    c.showPage()

    c.save()
    print(f"Written {OUTPUT}")

    # Generate per-page PNG previews using pdftoppm (poppler)
    if shutil.which("pdftoppm"):
        for p in range(TOTAL_PAGES):
            page_num = p + 1  # pdftoppm uses 1-based page numbers
            out_file = f"{PNG_PREFIX}_{page_num}"
            subprocess.run(
                [
                    "pdftoppm", "-png", "-singlefile",
                    "-r", str(PNG_DPI),
                    "-f", str(page_num), "-l", str(page_num),
                    OUTPUT, out_file,
                ],
                check=True,
            )
            print(f"Written {out_file}.png")
    else:
        print("pdftoppm not found -- skipping PNG generation.")
        print("Install poppler (e.g. nix-shell -p poppler-utils) to generate PNGs.")


if __name__ == "__main__":
    main()
