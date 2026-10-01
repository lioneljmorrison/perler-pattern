#!/usr/bin/env python3
"""Extract the bead grids from the Sailor Moon PDF into pattern.json and viewer.html.

The PDF is a chat transcript: it holds six partial text grids plus prose, not a
full-canvas pattern. Each grid uses its own legend (the same letter can mean
different colors in different grids), so every section carries its own legend
that maps symbols to entries in the shared palette.

Usage: python3 build_pattern.py   (requires poppler's `pdftotext`)
"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
PDF = ROOT / "Sailor Moon Perler Bead Pattern.pdf"

# Master Color Key from the PDF (hex values as given there), plus Hot Pink,
# which the per-section legends list separately from Magenta.
PALETTE = {
    "lightBlue":   {"name": "Light Blue",            "role": "Sky & water base",            "hex": "#0099D8"},
    "white":       {"name": "White",                 "role": "Highlights, aura, catchlights", "hex": "#FFFFFF"},
    "yellow":      {"name": "Yellow / Pastel Yellow", "role": "Primary hair highlight",      "hex": "#FEE135"},
    "cheddar":     {"name": "Cheddar / Orange",      "role": "Hair midtone warmth",         "hex": "#F58220"},
    "magenta":     {"name": "Magenta",               "role": "Hair core shadow / bang spikes", "hex": "#E0115F"},
    "hotPink":     {"name": "Hot Pink",              "role": "Lash accents / pink shadow",  "hex": "#FF3EA5"},
    "peach":       {"name": "Peach",                 "role": "Skin midtone",                "hex": "#F5B895"},
    "cream":       {"name": "Cream / Light Peach",   "role": "Skin highlight",              "hex": "#FDEBD0"},
    "lightPink":   {"name": "Light Pink",            "role": "Skin blush / iris reflection", "hex": "#F8B9D4"},
    "midnight":    {"name": "Midnight / Blueberry",  "role": "Right silhouette / deep navy", "hex": "#0B1B3D"},
    "plum":        {"name": "Dark Purple / Plum",    "role": "Eye contour, lashes, outlines", "hex": "#301934"},
    "turquoise":   {"name": "Turquoise / Mint",      "role": "Iris glow (midtone)",         "hex": "#40E0D0"},
    "pastelGreen": {"name": "Pastel Green / Sour Apple", "role": "Iris sparkle",            "hex": "#76FF7A"},
    "cranberry":   {"name": "Bright Red / Cranberry", "role": "Fingernails & lip accent",   "hex": "#C41E3A"},
}
# Hot Pink isn't in the PDF's hex table; this value is approximate.
PALETTE["hotPink"]["note"] = "Not in the PDF's hex table; approximate value."


def base(color, why):
    """'.' meaning 'background or skin base, depending on section'. The color is our inference."""
    return {"color": color, "inferred": True, "note": why}


def c(color, note=None):
    entry = {"color": color}
    if note:
        entry["note"] = note
    return entry


# One entry per grid, in the order they appear in the PDF.
SECTIONS = [
    {
        "id": "left-eye",
        "title": "Left Eye Focal Grid",
        "description": "The prominent eye on the left side, from the upper lash arc down through the lower lash spikes.",
        "declaredSize": {"cols": 24, "rows": 14},
        "placement": "Board (2,2), roughly rows 030–044 / board columns 05–28 (from the prose).",
        "legend": {
            ".": base("peach", "Legend says 'Background / Skin Base'; skin is the likely surround here."),
            "K": c("plum", "Dark Iris / Shadow: Dark Blue, Blueberry, or Dark Purple"),
            "M": c("hotPink", "Accent Shadow / Lash Spikes: Hot Pink or Magenta"),
            "W": c("white"),
            "T": c("turquoise"),
            "G": c("pastelGreen"),
            "P": c("lightPink", "Iris Reflection"),
        },
        "padWith": ".",
    },
    {
        "id": "hand-thumb",
        "title": "Foreground Hand & Breaking Thumb",
        "description": "The hand, with the thumb hanging past the bottom edge of the main canvas.",
        "declaredSize": {"cols": 22, "rows": 24},
        "placement": "Bottom-left third; rows 19–24 hang below the canvas edge.",
        "legend": {
            ".": base("lightBlue", "Legend says 'Background / Skin Base'; the hand sits on the blue field."),
            "K": c("plum", "Dark Iris / Shadow: Dark Blue, Blueberry, or Dark Purple"),
            "M": c("hotPink", "Accent Shadow: Hot Pink or Magenta"),
            "S": c("peach", "Hand Skin Base"),
            "H": c("cream", "Skin Highlight: Cream / White"),
            "O": c("cranberry", "In this legend O is Nail Polish: Bright Red / Cranberry"),
        },
        "padWith": ".",
        "canvasEdgeAfterRow": 18,
    },
    {
        "id": "right-eye",
        "title": "Right Eye & Shadow Block",
        "description": "The angled right eye where it meets the deep shadow field on the right edge of the frame.",
        "declaredSize": {"cols": 24, "rows": 14},
        "placement": "Board (2,3), with the shadow block running into Board (2,4).",
        "legend": {
            ".": base("peach", "Legend says 'Background / Skin Base'; skin is the likely surround here."),
            "B": c("midnight", "In this legend B is Solid Deep Shadow: Dark Blue / Blueberry / Dark Purple"),
            "K": c("plum", "Dark Iris / Eyelash Contour: Midnight Blue / Plum"),
            "M": c("hotPink", "Lash Accent / Pink Shadow"),
            "W": c("white"),
            "T": c("turquoise"),
            "G": c("pastelGreen"),
            "P": c("lightPink", "Not in this section's legend; carried over from the left-eye legend."),
        },
        "padWith": ".",
    },
    {
        "id": "hair-cluster",
        "title": "Hair Dithering & Bangs Cluster",
        "description": "Upper-left quadrant above the eyes: yellow strands, warm orange, and magenta split lines.",
        "declaredSize": {"cols": 24, "rows": 14},
        "placement": "Upper-left quadrant (exact position not given).",
        "legend": {
            ".": base("lightBlue", "Legend says 'Background / Skin Base'; sky is the likely surround at the hair edge."),
            "Y": c("yellow"),
            "O": c("cheddar", "In this legend O is Hair Midtone: Cheddar / Orange"),
            "A": c("magenta", "Hair Core Shadow Line"),
            "M": c("hotPink", "Not in this section's legend; carried over from the earlier legend (Hot Pink / Magenta)."),
        },
        "padWith": ".",
    },
    {
        "id": "board-1-2",
        "title": "Board (1,2): Crown & Bang Core",
        "description": "Top-center board: the hair crown, bang roots, and magenta strand lines.",
        "declaredSize": {"cols": 28, "rows": 28},
        "placement": "Rows 001–028, columns 029–056.",
        "legend": {
            "B": c("lightBlue"),
            "W": c("white"),
            "Y": c("yellow"),
            "O": c("cheddar"),
            "A": c("magenta"),
        },
        "padWith": None,
    },
    {
        "id": "board-4-2",
        "title": "Board (4,2): Hand, Fingers & Overhang",
        "description": "Bottom-center board: the finger reaching down-left and the thumb extension past the canvas baseline.",
        "declaredSize": {"cols": 28, "rows": 36},
        "placement": "Rows 085–120, columns 029–056; rows 113–120 hang below the canvas baseline.",
        "legend": {
            ".": c(None, "Transparent / not on this board"),
            "B": c("lightBlue"),
            "K": c("plum", "Dark Purple / Plum / Midnight"),
            "S": c("peach"),
            "R": c("cranberry"),
        },
        "padWith": None,
        "canvasEdgeAfterRow": 112,
    },
]

# Prose-only guidance for the 4×4 board layout (no bead-level data in the PDF).
BOARDS = [
    {"board": "1,1", "summary": "Top-left hair cluster. Cols 01–10 solid sky (B); cols 11–28 hair edge with a white/blue dithered halo, Y/O checkerboard inside."},
    {"board": "1,2", "summary": "Crown & bang roots.", "section": "board-1-2"},
    {"board": "1,3", "summary": "Rows 001–015 solid sky. A white diagonal from (row 16, col 01) to (row 28, col 20) marks the head edge; dithered Y, O and scattered A below."},
    {"board": "1,4", "summary": "Solid Light Blue sky corner."},
    {"board": "2,1", "summary": "Cols 01–08 solid sky; cols 09–28 bang tips shifting from Y/O into light pink and peach over the skin."},
    {"board": "2,2", "summary": "Left eye (rows 030–044) and nose bridge; rows 045–056 peach/cream checkerboard with light-pink blush.", "section": "left-eye"},
    {"board": "2,3", "summary": "Right eye (rows 032–046, cols 04–22); cols 23–28 solid midnight shadow block.", "section": "right-eye"},
    {"board": "2,4", "summary": "Cols 01–10 solid midnight; cols 11–28 back to solid Light Blue."},
    {"board": "3,1", "summary": "Upper half cheek dither (peach/pink); lower half hand entering, outlined plum/midnight, filled peach with cream highlights."},
    {"board": "3,2", "summary": "Nose base and mouth (scattered pink/magenta); back of the hand and knuckles running diagonally down, cream on the index tendon."},
    {"board": "3,3", "summary": "Jawline upper-left; solid Light Blue field lower-right."},
    {"board": "3,4", "summary": "Solid Light Blue."},
    {"board": "4,1", "summary": "Slender diagonal peach fingers with 1-bead plum/midnight outlines on blue; 2×2 cranberry nails around rows 098–104."},
    {"board": "4,2", "summary": "Fingers and thumb overhang (rows 113–120, cols 35–48).", "section": "board-4-2"},
    {"board": "4,3", "summary": "Solid Light Blue."},
    {"board": "4,4", "summary": "Solid Light Blue."},
]

ROW_RE = re.compile(r"^\s*Row\s+(\d+):\s+(.*)$")


def extract_rows():
    text = subprocess.run(
        ["pdftotext", "-layout", str(PDF), "-"], capture_output=True, text=True, check=True
    ).stdout
    blocks, prev = [], None
    for line in text.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        n = int(m.group(1))
        # Drop trailing annotations like "[Canvas Bottom Edge]".
        tokens = re.sub(r"\[.*?\]", "", m.group(2)).split()
        if prev is None or n != prev + 1:
            blocks.append([])
        blocks[-1].append({"n": n, "beads": "".join(tokens)})
        prev = n
    return blocks


def build():
    blocks = extract_rows()
    assert len(blocks) == len(SECTIONS), f"expected {len(SECTIONS)} grids, found {len(blocks)}"

    sections = []
    for spec, rows in zip(SECTIONS, blocks):
        nums = [r["n"] for r in rows]
        assert nums == list(range(nums[0], nums[0] + len(nums))), f"{spec['id']}: rows not contiguous"
        assert len(rows) == spec["declaredSize"]["rows"], f"{spec['id']}: row count mismatch"
        symbols = set("".join(r["beads"] for r in rows))
        missing = symbols - spec["legend"].keys()
        assert not missing, f"{spec['id']}: symbols without legend entry: {missing}"

        widths = sorted({len(r["beads"]) for r in rows})
        width = widths[-1]
        notes = []
        if widths != [spec["declaredSize"]["cols"]]:
            notes.append(
                f"Declared {spec['declaredSize']['cols']} columns; rows in the PDF are "
                f"{', '.join(map(str, widths))} beads wide. Shorter rows are padded on the right with "
                + ("'.' (assumed background)." if spec["padWith"] else "empty cells (unknown).")
            )
        sections.append({
            **{k: v for k, v in spec.items() if k != "padWith"},
            "width": width,
            "height": len(rows),
            "firstRow": nums[0],
            "padWith": spec["padWith"],
            "rows": rows,
            "notes": notes,
        })

    return {
        "title": "Sailor Moon Perler Bead Pattern",
        "source": PDF.name,
        "about": (
            "Partial grids extracted from an AI chat transcript. The PDF does not contain a "
            "full-canvas pattern: it gives six focal-area grids plus prose for the rest."
        ),
        "canvas": {
            "declared": [
                {"cols": 104, "rows": 116, "note": "First answer; ~122 rows at the thumb tip."},
                {"cols": 112, "rows": 112, "note": "Later 4×4 board plan with 28×28 boards; thumb extends to row 120."},
            ],
            "boardSize": 28,
            "boardGrid": {"cols": 4, "rows": 4},
        },
        "rowFormat": "Each row's 'beads' string has one character per bead; look it up in the section's legend. "
                     "Rows shorter than 'width' are padded on the right with 'padWith' (null = empty/unknown).",
        "palette": PALETTE,
        "boards": BOARDS,
        "sections": sections,
    }


# One letter per palette color for the full-canvas previews ('.' = unspecified).
PREVIEW_KEY = {
    "B": "lightBlue", "W": "white", "Y": "yellow", "O": "cheddar", "A": "magenta",
    "H": "hotPink", "S": "peach", "F": "cream", "P": "lightPink", "D": "midnight",
    "K": "plum", "T": "turquoise", "G": "pastelGreen", "R": "cranberry",
}
LETTER = {v: k for k, v in PREVIEW_KEY.items()}

# Where grids land on the 112×120 board plan (1-based top-left), from the PDF's prose.
# The hand-thumb and hair-cluster grids have no stated position, so they're left out.
PLACEMENTS = {
    "board-1-2": (1, 29),
    "board-4-2": (85, 29),
    "left-eye":  (30, 33),   # Board (2,2), board cols 05–28
    "right-eye": (32, 60),   # Board (2,3), board col 04
}

# Solid fills the prose states explicitly: (row0, row1, col0, col1, color), inclusive, 1-based.
SOLID_FILLS = [
    (1, 28, 1, 10, "lightBlue"),     # Board (1,1) cols 01–10
    (1, 15, 57, 84, "lightBlue"),    # Board (1,3) rows 001–015
    (1, 28, 85, 112, "lightBlue"),   # Board (1,4)
    (29, 56, 1, 8, "lightBlue"),     # Board (2,1) cols 01–08
    (29, 56, 79, 84, "midnight"),    # Board (2,3) cols 23–28
    (29, 56, 85, 94, "midnight"),    # Board (2,4) cols 01–10
    (29, 56, 95, 112, "lightBlue"),  # Board (2,4) cols 11–28
    (57, 84, 85, 112, "lightBlue"),  # Board (3,4)
    (85, 112, 57, 112, "lightBlue"), # Boards (4,3) and (4,4)
]


def pdf_composite(sections):
    """Lay every bead the PDF actually specifies onto the 112×120 board plan."""
    rows, cols = 120, 112
    grid = [["."] * cols for _ in range(rows)]
    for r0, r1, c0, c1, color in SOLID_FILLS:
        for r in range(r0 - 1, r1):
            for c in range(c0 - 1, c1):
                grid[r][c] = LETTER[color]
    by_id = {s["id"]: s for s in sections}
    for sid, (top, left) in PLACEMENTS.items():
        s = by_id[sid]
        for i, row in enumerate(s["rows"]):
            for j, sym in enumerate(row["beads"]):
                entry = s["legend"][sym]
                # Skip '.' cells: off-board, or a guessed base color we shouldn't paint over.
                if entry.get("color") is None or entry.get("inferred"):
                    continue
                grid[top - 1 + i][left - 1 + j] = LETTER[entry["color"]]
    lines = ["".join(r) for r in grid]
    known = sum(ch != "." for ln in lines for ch in ln)
    return {
        "title": "Following the PDF",
        "description": (
            "Every bead the PDF actually specifies, placed where its prose says it goes: the four "
            "positioned grids plus the solid fills it spells out. Hatched areas are only described "
            "loosely (e.g. 'dither Y and O') or not at all. The hand and hair-cluster grids have "
            "no stated position and are not placed."
        ),
        "width": cols, "height": rows, "canvasEdgeAfterRow": 112,
        "specifiedPercent": round(100 * known / (rows * cols)),
        "rows": lines,
    }


def photo_preview():
    """Map the photo in the PDF onto beads. The photo is tiny, so this is only a rough look."""
    from PIL import Image
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdfimages", "-png", "-f", "1", "-l", "1", str(PDF), f"{tmp}/img"], check=True)
        im = Image.open(f"{tmp}/img-000.png").convert("RGB")
    # The bead piece occupies this box in the 82×84 photo (found by its saturated pixels).
    piece = im.crop((18, 14, 66, 69))
    cols, rows = 104, 121  # The PDF's first estimate: 104 wide, ~122 at the thumb tip.
    piece = piece.resize((cols, rows), Image.BICUBIC)

    pal = [(LETTER[k], tuple(int(v["hex"][i:i + 2], 16) for i in (1, 3, 5))) for k, v in PALETTE.items()]

    def nearest(px):
        r, g, b = px
        best = min(pal, key=lambda p: 2 * (r - p[1][0]) ** 2 + 4 * (g - p[1][1]) ** 2 + 3 * (b - p[1][2]) ** 2)
        return best[0]

    lines = ["".join(nearest(piece.getpixel((x, y))) for x in range(cols)) for y in range(rows)]
    return {
        "title": "From the photo",
        "description": (
            f"The PDF's photo mapped to the nearest bead color at {cols}×{rows}. The photo is only "
            f"{im.size[0]}×{im.size[1]} pixels (the piece itself ~48×56), so each pixel covers about "
            "four beads: right overall look, no fine detail."
        ),
        "width": cols, "height": rows,
        "rows": lines,
    }


def main():
    pattern = build()
    pattern["previewKey"] = PREVIEW_KEY
    pattern["previews"] = [pdf_composite(pattern["sections"]), photo_preview()]
    (ROOT / "pattern.json").write_text(json.dumps(pattern, indent=2) + "\n")
    template = (ROOT / "viewer.template.html").read_text()
    # Embed so viewer.html works when opened straight from disk (fetch fails on file://).
    embedded = json.dumps(pattern).replace("</", "<\\/")
    (ROOT / "viewer.html").write_text(template.replace("/*PATTERN_JSON*/null", embedded))
    for s in pattern["sections"]:
        print(f"{s['id']:14} {s['width']:>3}×{s['height']:<3} {'; '.join(s['notes'])}")


if __name__ == "__main__":
    main()
