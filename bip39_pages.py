#!/usr/bin/env python3
"""Generate a printable BIP39 word list as PDF.

Layout:
- 1 manual page
- 1 worksheet page
- 4 lookup pages × 8 columns × 8 sections × 8 words = 2048 words

11-bit index split (left to right):
  [10:9] 2 bits → page
  [8:6]  3 bits → row/section
  [5:3]  3 bits → column
  [2:0]  3 bits → word in section

The worksheet supports two die-based workflows:
- simple mapping for a die you consider fair: 1-3 → 0, 4-6 → 1
- bias-resistant comparison for a die whose fairness is unknown:
  roll twice, discard ties, first < second → 0, first > second → 1
"""

import shutil
import subprocess

from reportlab.lib.colors import Color
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

WORDS_FILE = "english.txt"
OUTPUT = "bip39_wordlist.pdf"
PNG_PREFIX = "page"
PNG_DPI = 200

LOOKUP_PAGES = 4
MANUAL_PAGES = 1
WORKSHEET_PAGES = 1
TOTAL_PAGES = LOOKUP_PAGES + MANUAL_PAGES + WORKSHEET_PAGES
COLS = 8
SECTIONS = 8
WORDS_PER_SECTION = 8

# Layout
PAGE_W, PAGE_H = A4
MARGIN_TOP = 20 * mm
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
FONT_SIZE = 6.8
TITLE_FONT_SIZE = 11

# Colors
C0 = Color(0.82, 0.82, 0.82)  # 0 = light grey
C1 = Color(0.20, 0.20, 0.20)  # 1 = near-black
TEXT = Color(0.1, 0.1, 0.1)
SUBTLE = Color(0.35, 0.35, 0.35)
BORDER = Color(0.55, 0.55, 0.55)

SECTION_BG = [
    Color(0.97, 0.91, 0.91),
    Color(0.97, 0.94, 0.88),
    Color(0.96, 0.96, 0.88),
    Color(0.90, 0.96, 0.90),
    Color(0.88, 0.95, 0.96),
    Color(0.89, 0.91, 0.97),
    Color(0.93, 0.90, 0.97),
    Color(0.96, 0.90, 0.95),
]
COL_TINT = 0.93

BIT_BLOCK_SIZE = 2.2 * mm
BIT_BLOCK_GAP = 0.5 * mm
BIT_BLOCK_SMALL = 1.8 * mm
BIT_BLOCK_SMALL_GAP = 0.3 * mm
COL_BLOCK_SIZE = 2.5 * mm
COL_BLOCK_GAP = 0.5 * mm
COL_BLOCKS_W = 3 * COL_BLOCK_SIZE + 2 * COL_BLOCK_GAP
SEC_BLOCK_SIZE = 2.2 * mm
SEC_BLOCK_GAP = 0.4 * mm
PAGE_BLOCK_SIZE = 3 * mm
PAGE_BLOCK_GAP = 0.8 * mm


def darken(color, factor=COL_TINT):
    return Color(color.red * factor, color.green * factor, color.blue * factor)


def draw_bit_blocks(c, x, y, bits, size=None, gap=None, start_num=None,
                    show_positions=True, show_bits=True):
    """Draw colored squares for bits. Returns total width."""
    sz = size or BIT_BLOCK_SIZE
    gp = gap or BIT_BLOCK_GAP

    if show_bits:
        inner_font_name = "Helvetica-Bold"
        inner_font_size = max(2.7, sz * 0.60)
        inner_ascent = pdfmetrics.getAscent(inner_font_name, inner_font_size)
        inner_descent = pdfmetrics.getDescent(inner_font_name, inner_font_size)
        inner_baseline = y + (sz - (inner_ascent - inner_descent)) / 2 - inner_descent - 0.09 * mm

    if start_num is not None and show_positions:
        outer_font_name = "Helvetica"
        outer_font_size = max(1.8, sz * 0.30)
        outer_baseline = y - max(0.9 * mm, sz * 0.42)

    for i, b in enumerate(bits):
        bx = x + i * (sz + gp)
        c.setFillColor(C1 if b == "1" else C0)
        c.setStrokeColor(Color(0.5, 0.5, 0.5))
        c.setLineWidth(0.2)
        c.rect(bx, y, sz, sz, fill=1, stroke=1)
        if show_bits:
            c.setFont(inner_font_name, inner_font_size)
            c.setFillColor(Color(1, 1, 1) if b == "1" else Color(0, 0, 0))
            c.drawCentredString(bx + sz / 2, inner_baseline, b)

        if start_num is not None and show_positions:
            c.setFont(outer_font_name, outer_font_size)
            c.setFillColor(SUBTLE)
            c.drawCentredString(bx + sz / 2, outer_baseline, str(start_num + i))

    return len(bits) * sz + (len(bits) - 1) * gp


def draw_blank_blocks(c, x, y, count, size=None, gap=None, highlight_indices=None,
                      start_num=None, show_positions=False):
    """Draw empty squares for handwritten bits. Returns total width."""
    sz = size or BIT_BLOCK_SIZE
    gp = gap or BIT_BLOCK_GAP
    highlight_indices = set(highlight_indices or [])

    if start_num is not None and show_positions:
        outer_font_name = "Helvetica"
        outer_font_size = max(3.4, sz * 0.56)
        outer_baseline = y - max(1.65 * mm, sz * 0.56)

    for i in range(count):
        bx = x + i * (sz + gp)
        c.setFillColor(Color(0.90, 0.90, 0.90) if i in highlight_indices else Color(1, 1, 1))
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.35)
        c.rect(bx, y, sz, sz, fill=1, stroke=1)
        if start_num is not None and show_positions:
            c.setFont(outer_font_name, outer_font_size)
            c.setFillColor(SUBTLE)
            c.drawCentredString(bx + sz / 2, outer_baseline, str(start_num + i))
    return count * sz + (count - 1) * gp


def wrap_text(text, font_name, font_size, max_width):
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
                      leading=None, color=TEXT):
    """Draw wrapped text and return next y."""
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


def draw_section_heading(c, x, y, title, font_size=11, color=Color(0, 0, 0), gap=5 * mm):
    c.setFont("Helvetica-Bold", font_size)
    c.setFillColor(color)
    c.drawString(x, y, title)
    return y - gap


def draw_paragraphs(c, paragraphs, x, y, width, paragraph_gap=2 * mm, **text_kwargs):
    for i, paragraph in enumerate(paragraphs):
        y = draw_wrapped_text(c, paragraph, x, y, width, **text_kwargs)
        if i != len(paragraphs) - 1:
            y -= paragraph_gap
    return y


def draw_numbered_list(c, items, x, y, width, indent=4 * mm, **text_kwargs):
    for i, item in enumerate(items, start=1):
        y = draw_wrapped_text(c, f"{i}. {item}", x + indent, y, width - indent, **text_kwargs)
    return y


def draw_content_blocks(c, x, y, width, blocks):
    for block in blocks:
        kind = block["type"]
        if kind == "paragraphs":
            indent = block.get("indent", 0)
            y = draw_paragraphs(
                c,
                block["items"],
                x + indent,
                y,
                width - indent,
                paragraph_gap=block.get("paragraph_gap", 2 * mm),
                **block.get("text", {}),
            )
        elif kind == "numbered":
            y = draw_numbered_list(
                c,
                block["items"],
                x,
                y,
                width,
                indent=block.get("indent", 4 * mm),
                **block.get("text", {}),
            )
        elif kind == "custom":
            y = block["draw"](c, x, y, width)
        elif kind == "spacer":
            y -= block["height"]
    return y


def draw_bit_group_diagram(c, x, y, width):
    """Draw the page/row/column/word grouping diagram."""
    groups = [
        ("page", 2, "bits 1–2", 0, 0),
        ("column", 3, "bits 6–8", 1, 0),
        ("row", 3, "bits 3–5", 0, 1),
        ("word", 3, "bits 9–11", 1, 1),
    ]
    gap_x = 3 * mm
    gap_y = 2 * mm
    box_w = (width - gap_x) / 2
    box_h = 9 * mm
    total_h = 2 * box_h + gap_y

    for label, count, note, gx, gy in groups:
        left = x + gx * (box_w + gap_x)
        top = y - gy * (box_h + gap_y)
        bottom = top - box_h
        c.setFillColor(Color(0.985, 0.985, 0.985))
        c.setStrokeColor(Color(0.75, 0.75, 0.75))
        c.roundRect(left, bottom, box_w, box_h, 1.5 * mm, fill=1, stroke=1)

        c.setFont("Helvetica-Bold", 7.6)
        c.setFillColor(TEXT)
        c.drawString(left + 2.2 * mm, top - 3.4 * mm, label)
        c.setFont("Helvetica", 6.4)
        c.setFillColor(SUBTLE)
        c.drawRightString(left + box_w - 2.2 * mm, top - 3.4 * mm, note)

        blocks_w = count * 3.0 * mm + (count - 1) * 0.6 * mm
        start_num = {"page": 1, "row": 3, "column": 6, "word": 9}[label]
        draw_blank_blocks(c, left + box_w / 2 - blocks_w / 2, bottom + 4.3 * mm, count,
                          size=3.0 * mm, gap=0.6 * mm, start_num=start_num, show_positions=True)

    return y - total_h - 2 * mm


def draw_die_face(c, x, y, size, value):
    c.setFillColor(Color(1, 1, 1))
    c.setStrokeColor(Color(0.55, 0.55, 0.55))
    c.setLineWidth(0.3)
    c.roundRect(x, y, size, size, 0.9 * mm, fill=1, stroke=1)

    cx = [x + size * 0.26, x + size * 0.5, x + size * 0.74]
    cy = [y + size * 0.26, y + size * 0.5, y + size * 0.74]
    pips = {
        1: [(1, 1)],
        2: [(0, 2), (2, 0)],
        3: [(0, 2), (1, 1), (2, 0)],
        4: [(0, 2), (2, 2), (0, 0), (2, 0)],
        5: [(0, 2), (2, 2), (1, 1), (0, 0), (2, 0)],
        6: [(0, 2), (2, 2), (0, 1), (2, 1), (0, 0), (2, 0)],
    }
    c.setFillColor(TEXT)
    for px, py in pips[value]:
        c.circle(cx[px], cy[py], size * 0.065, fill=1, stroke=0)


def draw_die_comparison_examples(c, x, y, width):
    """Draw examples for the bias-resistant two-roll die method."""
    cards = [
        (2, 5, "0"),
        (5, 2, "1"),
        (4, 4, "discard"),
    ]
    gap = 2.2 * mm
    card_w = (width - 2 * gap) / 3
    card_h = 11.5 * mm
    die_size = 5.3 * mm
    die_gap = 3.2 * mm
    result_box = 5.2 * mm
    lift = 0.8 * mm

    for i, (first_roll, second_roll, result) in enumerate(cards):
        left = x + i * (card_w + gap)
        bottom = y - card_h + lift
        c.setFillColor(Color(0.985, 0.985, 0.985))
        c.setStrokeColor(Color(0.75, 0.75, 0.75))
        c.roundRect(left, bottom, card_w, card_h, 1.5 * mm, fill=1, stroke=1)

        dice_total_w = 2 * die_size + die_gap
        content_y = bottom + (card_h - die_size) / 2
        left_pad = 16 * mm
        right_pad = 16 * mm
        dice_x = left + left_pad
        draw_die_face(c, dice_x, content_y, die_size, first_roll)
        draw_die_face(c, dice_x + die_size + die_gap, content_y, die_size, second_roll)

        relation_symbol = "<" if result == "0" else ">" if result == "1" else "="
        c.setFont("Helvetica-Bold", 9.5)
        c.setFillColor(SUBTLE)
        c.drawCentredString(dice_x + die_size + die_gap / 2, bottom + card_h / 2 - 2.35, relation_symbol)

        arrow_y = bottom + card_h / 2 - 0.15 * mm

        if result in {"0", "1"}:
            box_x = left + card_w - right_pad - result_box
            box_y = bottom + (card_h - result_box) / 2
            arrow_end_x = box_x - 0.45 * mm
            c.setFillColor(Color(1, 1, 1))
            c.setStrokeColor(BORDER)
            c.setLineWidth(0.35)
            c.rect(box_x, box_y, result_box, result_box, fill=1, stroke=1)
            c.setFont("Helvetica-Bold", 7.8)
            c.setFillColor(TEXT)
            c.drawCentredString(box_x + result_box / 2, box_y + 1.45 * mm, result)
        else:
            c.setFont("Helvetica-Bold", 7.0)
            c.setFillColor(TEXT)
            discard_x = left + card_w - right_pad - 7.8 * mm
            arrow_end_x = discard_x - 0.45 * mm
            c.drawString(discard_x, bottom + card_h / 2 - 2.7, result)

        arrow_start_x = dice_x + dice_total_w + 0.55 * mm
        c.setStrokeColor(SUBTLE)
        c.setLineWidth(0.8)
        c.line(arrow_start_x, arrow_y, arrow_end_x, arrow_y)
        head = 1.1 * mm
        c.line(arrow_end_x, arrow_y, arrow_end_x - head, arrow_y + 0.55 * mm)
        c.line(arrow_end_x, arrow_y, arrow_end_x - head, arrow_y - 0.55 * mm)

    return y - card_h - 1.2 * mm - lift


def draw_two_roll_unbiased_box(c, x, y, width):
    box_h = 15 * mm
    bottom = y - box_h
    c.setFillColor(Color(0.98, 0.98, 0.98))
    c.setStrokeColor(Color(0.75, 0.75, 0.75))
    c.roundRect(x, bottom, width, box_h, 2.2 * mm, fill=1, stroke=1)

    title_x = x + 3 * mm
    title_w = 42 * mm
    formula_w = 62 * mm
    formula_x0 = x + title_w
    text_x = formula_x0 + formula_w + 2 * mm
    text_w = x + width - 3 * mm - text_x

    draw_wrapped_text(
        c,
        "Why the two-roll method is unbiased",
        title_x,
        y - 4.3 * mm,
        title_w - 4 * mm,
        font_name="Helvetica-Bold",
        font_size=9,
        leading=10,
        color=TEXT,
    )

    formula_font = 9.5
    left_term = "p(a<b)"
    mid_term = " = p(a)p(b) = "
    right_term = "p(a>b)"
    total_formula_w = (
        pdfmetrics.stringWidth(left_term, "Helvetica", formula_font)
        + pdfmetrics.stringWidth(mid_term, "Helvetica", formula_font)
        + pdfmetrics.stringWidth(right_term, "Helvetica", formula_font)
    )
    formula_x = formula_x0 + (formula_w - total_formula_w) / 2
    formula_y = y - 4.7 * mm

    c.setFont("Helvetica", formula_font)
    c.setFillColor(Color(0.2, 0.2, 0.2))
    c.drawString(formula_x, formula_y, left_term)
    mid_x = formula_x + pdfmetrics.stringWidth(left_term, "Helvetica", formula_font)
    c.drawString(mid_x, formula_y, mid_term)
    right_x_formula = mid_x + pdfmetrics.stringWidth(mid_term, "Helvetica", formula_font)
    c.drawString(right_x_formula, formula_y, right_term)

    left_center = formula_x + pdfmetrics.stringWidth(left_term, "Helvetica", formula_font) / 2
    right_center = right_x_formula + pdfmetrics.stringWidth(right_term, "Helvetica", formula_font) / 2
    symbol_box = 5.2 * mm
    symbol_y = formula_y - 7.3 * mm
    left_box_x = left_center - symbol_box / 2
    right_box_x = right_center - symbol_box / 2
    c.setFillColor(Color(1, 1, 1))
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.35)
    c.rect(left_box_x, symbol_y, symbol_box, symbol_box, fill=1, stroke=1)
    c.rect(right_box_x, symbol_y, symbol_box, symbol_box, fill=1, stroke=1)

    c.setFont("Helvetica-Bold", 7.8)
    c.setFillColor(TEXT)
    c.drawCentredString(left_box_x + symbol_box / 2, symbol_y + 1.45 * mm, "0")
    c.drawCentredString(right_box_x + symbol_box / 2, symbol_y + 1.45 * mm, "1")

    draw_wrapped_text(
        c,
        "For any two different numbers a and b, getting a then b is just as likely as getting b then a. Shake well, and only use one die, so each roll is made the same way.",
        text_x,
        y - 4.2 * mm,
        text_w,
        font_size=6.6,
        leading=7.2,
        color=Color(0.2, 0.2, 0.2),
    )

    return y - box_h - 1.5 * mm


def draw_exact_mapping_note(c, x, y, width, example_num, example_word, example_idx, example_bits):
    page_bits = example_bits[:2]
    row_bits = example_bits[2:5]
    col_bits = example_bits[5:8]
    word_bits = example_bits[8:11]

    note_color = Color(0.38, 0.38, 0.38)
    note_text = {"font_size": 8, "leading": 10, "color": note_color}

    y = draw_section_heading(c, x, y, "Additional detail: exact mapping",
                             font_size=8, color=note_color, gap=3 * mm)
    y = draw_content_blocks(
        c,
        x,
        y,
        width,
        [
            {
                "type": "paragraphs",
                "items": [
                    "You do not need this to use the sheet. It only explains how the printed layout maps to the exact BIP39 index.",
                ],
                "text": {
                    "font_name": "Helvetica-Oblique",
                    "font_size": 8,
                    "leading": 10,
                    "color": note_color,
                },
            },
            {"type": "spacer", "height": 1.0 * mm},
            {
                "type": "paragraphs",
                "items": [
                    "Read the 11 recorded bits from left to right. Split them as 2 | 3 | 3 | 3, which means page | row | column | word.",
                    "If you want the exact BIP39 list position, read the full 11-bit pattern as a binary number. The BIP39 wordlist counts from 0, so the Nth word uses binary(N-1).",
                ],
                "paragraph_gap": 1.0 * mm,
                "text": note_text,
            },
            {"type": "spacer", "height": 2 * mm},
        ],
    )

    y = draw_section_heading(c, x, y, f"Example: {example_num}th word",
                             font_size=8, color=note_color, gap=3 * mm)
    y = draw_paragraphs(
        c,
        [
            f"The {example_num}th BIP39 word is '{example_word}'. Take {example_num}-1 = {example_idx}. In 11-bit binary that is {example_bits}, or split up: {page_bits} | {row_bits} | {col_bits} | {word_bits}.",
        ],
        x,
        y,
        width,
        **note_text,
    )

    example_block_size = 3.0 * mm
    example_block_gap = 0.6 * mm
    example_group_gap = 1.8 * mm
    example_blocks_y = y - 0.3 * mm - example_block_size

    group_x = x
    for bits, start_num in ((page_bits, 1), (row_bits, 3), (col_bits, 6), (word_bits, 9)):
        draw_bit_blocks(c, group_x, example_blocks_y, bits,
                        size=example_block_size, gap=example_block_gap, start_num=start_num,
                        show_positions=True, show_bits=True)
        group_w = len(bits) * example_block_size + (len(bits) - 1) * example_block_gap
        group_x += group_w
        if start_num != 9:
            c.setFont("Helvetica-Bold", 7.5)
            c.setFillColor(Color(0.45, 0.45, 0.45))
            c.drawCentredString(group_x + example_group_gap / 2, example_blocks_y + 0.2 * mm, "|")
            group_x += example_group_gap

    y -= 10.5 * mm
    return draw_paragraphs(
        c,
        ["So on the printed sheet: go to page 10, then row 001, then column 100, then word 010. That lands on 'middle'."],
        x,
        y,
        width,
        **note_text,
    )


def draw_filled_word_example(c, x, y, width):
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(TEXT)
    c.drawString(x, y, "Example filled row")

    y -= 4.2 * mm
    block_size = 3.6 * mm
    block_gap = 0.8 * mm
    group_gap = 3.2 * mm
    text_gap = 4.5 * mm

    groups = [("10", "page"), ("001", "row"), ("100", "column"), ("010", "word")]
    group_x = x
    for bits, label in groups:
        group_w = len(bits) * block_size + (len(bits) - 1) * block_gap
        draw_bit_blocks(c, group_x, y - block_size, bits, size=block_size, gap=block_gap,
                        show_positions=False, show_bits=True)
        c.setFont("Helvetica", 7)
        c.setFillColor(SUBTLE)
        c.drawCentredString(group_x + group_w / 2, y - block_size - 3.1 * mm, label)
        group_x += group_w + group_gap

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(TEXT)
    c.drawString(group_x, y - 2.3 * mm, "→ middle")

    return y - block_size - 5.2 * mm


def draw_manual_page(c, words):
    """Draw the manual page."""
    margin_x = 15 * mm
    top_y = PAGE_H - 16 * mm
    text_w = PAGE_W - 2 * margin_x
    body_text = {"font_size": 8, "leading": 10}

    example_num = 1123
    example_idx = example_num - 1
    example_word = words[example_idx]
    example_bits = format(example_idx, "011b")

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(Color(0, 0, 0))
    c.drawString(margin_x, top_y, "BIP39 Printable Wordlist — Manual")

    y = top_y - 9 * mm
    y = draw_paragraphs(
        c,
        [
            "These pages are meant to make rolling wallets or generating passphrases by hand easy to follow and as error-resistant as possible.",
            "Generate the bits, record them clearly, and use the lookup pages step by step.",
        ],
        margin_x,
        y,
        text_w,
        paragraph_gap=1.2 * mm,
        **body_text,
    )
    y -= 2.5 * mm

    sections = [
        {
            "title": "Why",
            "blocks": [
                {
                    "type": "paragraphs",
                    "items": [
                        "Software-based seed generation has a large attack surface: compromised RNGs, malware, clipboard sniffers, screen capture, or a backdoored hardware stack. Even an air-gapped computer still requires trusting its software and hardware chain.",
                        "This layout lets you generate the seed words offline from your own physical randomness and look them up directly on paper. No screen or device is involved in the entropy-generation step.",
                        "The layout is designed to keep rolling wallets or generating passphrases by hand simple, to reduce avoidable mistakes during recording and lookup, and to keep the random generation secure even when faced with low-quality dice.",
                    ],
                    "text": body_text,
                },
            ],
        },
        {
            "title": "Generating bits with a die",
            "blocks": [
                {
                    "type": "paragraphs",
                    "items": [
                        "Use this bias-resistant method: always use a single die and roll that same die twice. If both values are equal, discard the pair. If the first value is smaller than the second, write 0. If the first value is greater than the second, write 1. If you discard a pair, start over with two fresh rolls.",
                    ],
                    "text": body_text,
                },
                {"type": "spacer", "height": 0.0 * mm},
                {"type": "custom", "draw": draw_die_comparison_examples},
                {"type": "spacer", "height": 0.8 * mm},
                {"type": "custom", "draw": draw_two_roll_unbiased_box},
                {"type": "spacer", "height": 2.6 * mm},
                {
                    "type": "paragraphs",
                    "items": [
                        "Expected number of rolls: for a fair d6, about 26.4 raw rolls per 11-bit word. For a fair d20, about 23.2. In general, only ties are discarded, so an n-sided die wastes just 1/n of pairs.",
                    ],
                    "text": body_text,
                },
            ],
        },
        {
            "title": "Using the lookup pages",
            "blocks": [
                {
                    "type": "paragraphs",
                    "items": [
                        "For one BIP39 word, record 11 bits and split them as 2 | 3 | 3 | 3 = page | row | column | word.",
                    ],
                    "text": body_text,
                },
                {"type": "spacer", "height": 0.8 * mm},
                {"type": "custom", "draw": lambda c, x, y, width: draw_bit_group_diagram(c, x + 16 * mm, y, width - 32 * mm)},
                {"type": "spacer", "height": 1.2 * mm},
                {
                    "type": "paragraphs",
                    "items": [
                        "Use the first 2 bits for the page, the next 3 for the row band, the next 3 for the column, and the last 3 for the word inside that cell.",
                        "The worksheet on the next page lets you record the page, row, column, and word bits, and also write down the actual BIP39 word.",
                    ],
                    "text": body_text,
                },
            ],
        },
        {
            "title": "How to create a wallet",
            "blocks": [
                {
                    "type": "paragraphs",
                    "items": [
                        "Generate the words on paper first. Then open the restore/import flow on a trusted hardware wallet. This is the trick: do not let the wallet create a new phrase. Instead, enter the words you generated on paper as if the wallet already existed. In simple terms, restoring those words gives you the same wallet the device would have created if it had generated that exact phrase itself.",
                        "For most people, 12 words are enough when they are generated securely. Longer phrases are possible, but they are not required just to get strong security.",
                        "For a 12-word phrase, generate the first 11 words normally. For the 12th word, only the first 7 bits come from your own rolls. The last 4 bits are a BIP39 checksum. They are there for error detection, so wallets can reject mistyped or otherwise invalid phrases. On the worksheet, those are the greyed fields in row 12. So after you have fixed the first 7 bits, there are 16 possible final words that fit that pattern.",
                        "Try those final words one by one in the wallet's restore/import screen. In other words, you are using the restore screen to test which final phrase is valid. The wallet will reject the wrong ones and accept the right one. The accepted phrase is your real mnemonic.",
                        "Expect about 8 tries on average. Some wallets may make you enter all 12 words each time, so this can take quite some time.",
                        "The same idea works for longer phrases. On the worksheet, the greyed fields mark the bits you do not generate in the final row of a 12-, 15-, 18-, 21-, or 24-word phrase: 15 words → 32 candidates, 18 → 64, 21 → 128, 24 → 256. Avoid websites or extra software for checking candidate phrases unless they are fully offline and truly trusted.",
                    ],
                    "text": body_text,
                },
            ],
        },
        {
            "title": "Backing up the words",
            "blocks": [
                {
                    "type": "paragraphs",
                    "items": [
                        "This project only helps with generation and lookup. Safe storage is a separate problem: paper vs. metal, geographic splits, memorization, inheritance planning, and so on. Lose the phrase and the funds are unrecoverable; leak it and someone else can spend them.",
                    ],
                    "text": body_text,
                },
            ],
        },
    ]

    for section in sections:
        y = draw_section_heading(c, margin_x, y, section["title"])
        y = draw_content_blocks(c, margin_x, y, text_w, section["blocks"])
        y -= 4 * mm

    draw_exact_mapping_note(
        c,
        margin_x,
        y - 4 * mm,
        text_w,
        example_num,
        example_word,
        example_idx,
        example_bits,
    )


def draw_recording_page(c):
    """Draw the worksheet page."""
    margin_x = 14 * mm
    top_y = PAGE_H - 16 * mm
    text_w = PAGE_W - 2 * margin_x

    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(Color(0, 0, 0))
    c.drawString(margin_x, top_y, "BIP39 Printable Wordlist — Worksheet")

    y = top_y - 8 * mm
    y = draw_wrapped_text(
        c,
        "Use this page to record the 11 bits for each word and the resulting BIP39 word itself. The worksheet is meant for the bias-resistant two-roll method.",
        margin_x,
        y,
        text_w,
        font_size=8.5,
        leading=10,
    )

    left_x = margin_x
    left_y = y - 1 * mm
    left_y = draw_section_heading(c, left_x, left_y, "Process", font_size=10, gap=4.5 * mm)
    left_y = draw_numbered_list(
        c,
        [
            "Use a single die and roll that same die twice. If both rolls are equal, discard that pair.",
            "If the first roll is smaller than the second, write 0. If the first roll is greater than the second, write 1.",
            "If you discard a pair, start over with two fresh rolls.",
            "Fill the boxes from left to right: 2 bits page, 3 bits row, 3 bits column, 3 bits word.",
            "Look up the resulting BIP39 word and write it in the last column.",
        ],
        left_x,
        left_y,
        text_w,
        font_size=8,
        leading=9.4,
    )

    y = left_y - 1.5 * mm
    y = draw_filled_word_example(c, margin_x, y, text_w)
    y -= 3.5 * mm
    y = draw_wrapped_text(
        c,
        "On rows 12, 15, 18, 21, and 24, the light grey boxes mark checksum bits in the final word. Do not roll those bits if that row is the last row for the number of words you want to use. Only generate the remaining boxes in that row, then find the accepted final word by recovery/import.",
        margin_x,
        y,
        text_w,
        font_size=7.8,
        leading=9,
        color=Color(0.25, 0.25, 0.25),
    )

    table_top = y - 3 * mm
    table_bottom = 10 * mm
    rows = 24
    row_h = (table_top - table_bottom) / (rows + 1)
    table_left = margin_x + 8 * mm
    table_right = PAGE_W - margin_x
    table_w = table_right - table_left

    page_col_w = 22 * mm
    row_col_w = 30 * mm
    col_col_w = 30 * mm
    word_bits_col_w = 30 * mm
    actual_word_col_w = table_w - page_col_w - row_col_w - col_col_w - word_bits_col_w

    x0 = table_left
    x1 = x0 + page_col_w
    x2 = x1 + row_col_w
    x3 = x2 + col_col_w
    x4 = x3 + word_bits_col_w
    x5 = table_right

    c.setFillColor(Color(0.94, 0.94, 0.94))
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.7)
    c.rect(table_left, table_top - row_h, table_w, row_h, fill=1, stroke=1)

    for vx in (x1, x2, x3, x4):
        c.setStrokeColor(Color(0.45, 0.45, 0.45))
        c.setLineWidth(1.0)
        c.line(vx, table_bottom, vx, table_top)

    c.setStrokeColor(BORDER)
    c.setLineWidth(0.7)
    c.rect(table_left, table_bottom, table_w, table_top - table_bottom, fill=0, stroke=1)

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(TEXT)
    header_y = table_top - row_h / 2 - 3
    c.drawCentredString((x0 + x1) / 2, header_y, "page")
    c.drawCentredString((x1 + x2) / 2, header_y, "row")
    c.drawCentredString((x2 + x3) / 2, header_y, "column")
    c.drawCentredString((x3 + x4) / 2, header_y, "word")
    c.drawCentredString((x4 + x5) / 2, header_y, "actual word")

    block_size = 4.8 * mm
    block_gap = 1.1 * mm
    page_bits_w = 2 * block_size + block_gap
    triple_bits_w = 3 * block_size + 2 * block_gap
    checksum_rows = {
        12: {"page": [], "row": [], "col": [2], "word": [0, 1, 2]},
        15: {"page": [], "row": [], "col": [1, 2], "word": [0, 1, 2]},
        18: {"page": [], "row": [], "col": [0, 1, 2], "word": [0, 1, 2]},
        21: {"page": [], "row": [2], "col": [0, 1, 2], "word": [0, 1, 2]},
        24: {"page": [], "row": [1, 2], "col": [0, 1, 2], "word": [0, 1, 2]},
    }

    for i in range(rows):
        row_top = table_top - (i + 1) * row_h
        row_bottom = row_top - row_h
        row_mid = (row_top + row_bottom) / 2

        c.setStrokeColor(Color(0.82, 0.82, 0.82))
        c.setLineWidth(0.35)
        c.line(table_left, row_bottom, table_right, row_bottom)

        c.setFont("Helvetica", 7.2)
        c.setFillColor(Color(0.45, 0.45, 0.45))
        c.drawRightString(table_left - 2 * mm, row_mid - 2.4, str(i + 1))

        row_num = i + 1
        highlights = checksum_rows.get(row_num, {"page": [], "row": [], "col": [], "word": []})
        group_y = row_mid - block_size / 2
        draw_blank_blocks(c, x0 + (page_col_w - page_bits_w) / 2, group_y, 2,
                          size=block_size, gap=block_gap, highlight_indices=highlights["page"])
        draw_blank_blocks(c, x1 + (row_col_w - triple_bits_w) / 2, group_y, 3,
                          size=block_size, gap=block_gap, highlight_indices=highlights["row"])
        draw_blank_blocks(c, x2 + (col_col_w - triple_bits_w) / 2, group_y, 3,
                          size=block_size, gap=block_gap, highlight_indices=highlights["col"])
        draw_blank_blocks(c, x3 + (word_bits_col_w - triple_bits_w) / 2, group_y, 3,
                          size=block_size, gap=block_gap, highlight_indices=highlights["word"])


def main():
    with open(WORDS_FILE) as f:
        words = [line.strip() for line in f]
    assert len(words) == 2048, f"Expected 2048 words, got {len(words)}"

    c = canvas.Canvas(OUTPUT, pagesize=A4)

    draw_manual_page(c, words)
    c.showPage()

    draw_recording_page(c)
    c.showPage()

    title_y = PAGE_H - 10 * mm
    col_header_y = PAGE_H - MARGIN_TOP + 2 * mm

    for page in range(LOOKUP_PAGES):
        page_bits = format(page, "02b")

        page_blocks_x = MARGIN_RIGHT + 18 * mm
        page_blocks_y = title_y - 0.5 * mm

        c.setFont("Helvetica-Bold", TITLE_FONT_SIZE)
        c.setFillColor(Color(0, 0, 0))
        c.drawString(MARGIN_RIGHT, title_y, "BIP39")

        draw_bit_blocks(c, page_blocks_x, page_blocks_y, page_bits,
                        size=PAGE_BLOCK_SIZE, gap=PAGE_BLOCK_GAP, start_num=1,
                        show_positions=False, show_bits=True)

        after_blocks_x = page_blocks_x + 2 * (PAGE_BLOCK_SIZE + PAGE_BLOCK_GAP) + 3 * mm
        c.setFont("Helvetica", 7)
        c.setFillColor(SUBTLE)
        c.drawString(after_blocks_x, title_y,
                     "11 bits per word:  2 bits page, 3 bits row, 3 bits column, 3 bits word")

        bar_y = (title_y + col_header_y + COL_BLOCK_SIZE) / 2
        c.setStrokeColor(Color(0.45, 0.45, 0.45))
        c.setLineWidth(0.8)
        c.line(MARGIN_RIGHT, bar_y, LEFT_MARGIN + USABLE_W, bar_y)

        for col in range(COLS):
            x = LEFT_MARGIN + col * COL_W
            col_bits = format(col, "03b")
            blocks_x = x + (COL_W - COL_BLOCKS_W) / 2
            draw_bit_blocks(c, blocks_x, col_header_y, col_bits,
                            size=COL_BLOCK_SIZE, gap=COL_BLOCK_GAP, start_num=6,
                            show_positions=False, show_bits=True)

        sec_blocks_x = MARGIN_RIGHT
        for sec in range(SECTIONS):
            sec_bits = format(sec, "03b")
            section_top = PAGE_H - MARGIN_TOP - sec * SECTION_H

            for col in range(COLS):
                bg = SECTION_BG[sec] if col % 2 == 0 else darken(SECTION_BG[sec])
                col_x = LEFT_MARGIN + col * COL_W
                c.setFillColor(bg)
                c.rect(col_x, section_top - SECTION_H, COL_W, SECTION_H, fill=1, stroke=0)

            c.setStrokeColor(Color(1, 1, 1))
            c.setLineWidth(0.45)
            for boundary in range(2, COLS, 2):
                sep_x = LEFT_MARGIN + boundary * COL_W
                c.line(sep_x, section_top - SECTION_H, sep_x, section_top)

            c.setStrokeColor(Color(0.6, 0.6, 0.6))
            c.setLineWidth(0.4)
            c.line(LEFT_MARGIN, section_top, LEFT_MARGIN + USABLE_W, section_top)

            blocks_y = section_top - SECTION_H / 2 - SEC_BLOCK_SIZE / 2
            draw_bit_blocks(c, sec_blocks_x, blocks_y, sec_bits,
                            size=SEC_BLOCK_SIZE, gap=SEC_BLOCK_GAP, start_num=3,
                            show_positions=False, show_bits=True)

            for col in range(COLS):
                x = LEFT_MARGIN + col * COL_W
                for w in range(WORDS_PER_SECTION):
                    idx = page * 512 + sec * 64 + col * 8 + w
                    word = words[idx]
                    word_bits = format(w, "03b")
                    y = section_top - SECTION_LABEL_H - w * WORD_ROW_H

                    draw_bit_blocks(c, x + 0.9 * mm, y - 1.15 * mm, word_bits,
                                    size=BIT_BLOCK_SMALL, gap=BIT_BLOCK_SMALL_GAP, start_num=9,
                                    show_positions=False, show_bits=True)

                    c.setFont("Courier", FONT_SIZE)
                    c.setFillColor(Color(0.05, 0.05, 0.05))
                    c.drawString(x + 7.8 * mm, y - 0.9 * mm, word)

        c.showPage()

    c.save()
    print(f"Written {OUTPUT}")

    if shutil.which("pdftoppm"):
        for p in range(TOTAL_PAGES):
            page_num = p + 1
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
