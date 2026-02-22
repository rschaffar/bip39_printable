#!/usr/bin/env python3
"""Generate a nicely organized BIP39 word list as PDF.

Layout: 4 pages × 8 columns × 8 sections × 8 words = 2048 words.

11-bit index split (left to right, matching coin throw order):
  [10:9] 2 bits → page          (page title)       ①
  [8:6]  3 bits → section/row   (left margin)       ②
  [5:3]  3 bits → column        (column header)     ③
  [2:0]  3 bits → word in section (per word)

Coin-throw friendly: colored bit blocks for visual pattern matching.
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas

WORDS_FILE = "english.txt"
OUTPUT = "bip39_wordlist.pdf"

PAGES = 4
COLS = 8
SECTIONS = 8
WORDS_PER_SECTION = 8
ROWS = SECTIONS * WORDS_PER_SECTION  # 64

# Layout
PAGE_W, PAGE_H = A4
MARGIN_TOP = 20 * mm   # room for column header + circled 3 above
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
BITS_FONT_SIZE = 5
HEADER_FONT_SIZE = 7
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
SEC_BLOCKS_H = SEC_BLOCK_SIZE  # height of a row of blocks

# Circled number sizing
CIRCLE_R = 2.2 * mm
CIRCLE_FONT = 6


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


def draw_circled_number(c, cx, cy, num):
    """Draw a number inside a circle, centered at (cx, cy)."""
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.setLineWidth(0.5)
    c.setFillColorRGB(1, 1, 1)
    c.circle(cx, cy, CIRCLE_R, fill=1, stroke=1)
    c.setFillColorRGB(0.25, 0.25, 0.25)
    c.setFont("Helvetica-Bold", CIRCLE_FONT)
    c.drawCentredString(cx, cy - CIRCLE_FONT * 0.35, str(num))


def draw_arrow(c, x1, y1, x2, y2):
    """Draw a small dashed arrow from (x1,y1) to (x2,y2)."""
    c.setStrokeColorRGB(0.4, 0.4, 0.4)
    c.setLineWidth(0.5)
    c.setDash(1.5, 1.5)
    c.line(x1, y1, x2, y2)
    c.setDash()
    # Arrowhead
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    arrow_len = 1.8 * mm
    arrow_angle = 0.45
    c.setFillColorRGB(0.4, 0.4, 0.4)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2 - arrow_len * math.cos(angle - arrow_angle),
             y2 - arrow_len * math.sin(angle - arrow_angle))
    p.lineTo(x2 - arrow_len * math.cos(angle + arrow_angle),
             y2 - arrow_len * math.sin(angle + arrow_angle))
    p.close()
    c.drawPath(p, fill=1, stroke=0)


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

        # --- ① Page title ---
        page_blocks_x = MARGIN_RIGHT + 18 * mm
        page_blocks_y = title_y - 0.5 * mm
        page_block_sz = 3 * mm
        page_block_gap = 0.8 * mm

        c.setFont("Helvetica-Bold", TITLE_FONT_SIZE)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(MARGIN_RIGHT, title_y, "BIP39")

        # Circled 1 to the left of page blocks
        draw_circled_number(c, page_blocks_x - 4 * mm, page_blocks_y + page_block_sz / 2, 1)

        draw_bit_blocks(c, page_blocks_x, page_blocks_y, page_bits,
                        size=page_block_sz, gap=page_block_gap)

        # Explanatory text on title level
        after_blocks_x = page_blocks_x + 2 * (page_block_sz + page_block_gap) + 3 * mm
        c.setFont("Helvetica", 7)
        c.setFillColorRGB(0.35, 0.35, 0.35)
        c.drawString(after_blocks_x, title_y,
                     "11 coin flips per word:  2 bits page, 3 bits row, 3 bits column, 3 bits word")

        # --- ③ Column headers (centered horizontally in each column) ---
        for col in range(COLS):
            x = LEFT_MARGIN + col * COL_W
            col_bits = format(col, "03b")

            # Center blocks horizontally in column
            blocks_x = x + (COL_W - COL_BLOCKS_W) / 2
            draw_bit_blocks(c, blocks_x, col_header_y, col_bits,
                            size=COL_BLOCK_SIZE, gap=COL_BLOCK_GAP)

            # Vertical column separator
            if col > 0:
                c.setStrokeColorRGB(0.75, 0.75, 0.75)
                c.setLineWidth(0.3)
                c.line(x - 0.8 * mm, PAGE_H - MARGIN_TOP + 8 * mm,
                       x - 0.8 * mm, MARGIN_BOTTOM)

        # --- ② in the left margin, one diameter below ①
        sec_blocks_x = MARGIN_RIGHT
        sec_blocks_center_x = sec_blocks_x + (3 * SEC_BLOCK_SIZE + 2 * SEC_BLOCK_GAP) / 2
        circle1_actual_y = page_blocks_y + page_block_sz / 2
        circle2_y = circle1_actual_y - CIRCLE_R * 4  # ~one circle height below
        draw_circled_number(c, sec_blocks_center_x, circle2_y, 2)

        # --- ③ vertically aligned with ①
        col_blocks_center_y = col_header_y + COL_BLOCK_SIZE / 2
        circle1_actual_x = page_blocks_x - 4 * mm
        draw_circled_number(c, circle1_actual_x, col_blocks_center_y, 3)

        # --- Arrows: ① → ② → ③ ---
        import math
        circle1_x = circle1_actual_x
        circle1_y = circle1_actual_y
        circle3_x = circle1_actual_x  # same x as ①
        circle3_y = col_blocks_center_y

        # ① → ②: from bottom-left of ① to top-right of ②
        a1 = math.atan2(circle2_y - circle1_y, sec_blocks_center_x - circle1_x)
        draw_arrow(c,
                   circle1_x + CIRCLE_R * math.cos(a1),
                   circle1_y + CIRCLE_R * math.sin(a1),
                   sec_blocks_center_x - CIRCLE_R * math.cos(a1),
                   circle2_y - CIRCLE_R * math.sin(a1))

        # ② → ③: from bottom-right of ② to top-left of ③
        a2 = math.atan2(circle3_y - circle2_y, circle3_x - sec_blocks_center_x)
        draw_arrow(c,
                   sec_blocks_center_x + CIRCLE_R * math.cos(a2),
                   circle2_y + CIRCLE_R * math.sin(a2),
                   circle3_x - CIRCLE_R * math.cos(a2),
                   circle3_y - CIRCLE_R * math.sin(a2))

        # --- Sections ---
        for sec in range(SECTIONS):
            sec_bits = format(sec, "03b")
            section_top = PAGE_H - MARGIN_TOP - sec * SECTION_H

            # Background band across all columns
            c.setFillColor(SECTION_BG[sec])
            c.setStrokeColor(SECTION_BG[sec])
            c.rect(LEFT_MARGIN, section_top - SECTION_H, USABLE_W, SECTION_H,
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


if __name__ == "__main__":
    main()
