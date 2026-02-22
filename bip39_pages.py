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
from reportlab.lib.units import mm
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas

WORDS_FILE = "english.txt"
OUTPUT = "bip39_wordlist.pdf"
PNG_PREFIX = "page"
PNG_DPI = 200

PAGES = 4
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


def draw_bit_blocks(c, x, y, bits, size=None, gap=None):
    """Draw colored squares for each bit at (x, y) bottom-left. Returns total width."""
    sz = size or BIT_BLOCK_SIZE
    gp = gap or BIT_BLOCK_GAP
    for i, b in enumerate(bits):
        bx = x + i * (sz + gp)
        color = C1 if b == "1" else C0
        c.setFillColor(color)
        c.setStrokeColor(Color(0.5, 0.5, 0.5))
        c.setLineWidth(0.2)
        c.rect(bx, y, sz, sz, fill=1, stroke=1)
    return len(bits) * sz + (len(bits) - 1) * gp


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
                        size=PAGE_BLOCK_SIZE, gap=PAGE_BLOCK_GAP)

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
                            size=COL_BLOCK_SIZE, gap=COL_BLOCK_GAP)

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

            # Horizontal separator line
            c.setStrokeColorRGB(0.6, 0.6, 0.6)
            c.setLineWidth(0.4)
            c.line(LEFT_MARGIN, section_top, LEFT_MARGIN + USABLE_W, section_top)

            # Left margin: section bit blocks — vertically centered in section band
            blocks_y = section_top - SECTION_H / 2 - SEC_BLOCK_SIZE / 2
            draw_bit_blocks(c, sec_blocks_x, blocks_y, sec_bits,
                            size=SEC_BLOCK_SIZE, gap=SEC_BLOCK_GAP)

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
                                    size=BIT_BLOCK_SMALL, gap=BIT_BLOCK_SMALL_GAP)

                    # Word text
                    c.setFont("Courier", FONT_SIZE)
                    c.setFillColorRGB(0.05, 0.05, 0.05)
                    c.drawString(x + 6.5 * mm, y, word)

        c.showPage()

    c.save()
    print(f"Written {OUTPUT}")

    # Generate per-page PNG previews using pdftoppm (poppler)
    if shutil.which("pdftoppm"):
        for p in range(PAGES):
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
