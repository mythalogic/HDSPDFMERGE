"""
Run Separator Module for HDS Route Sequencer
Builds the one-page "Tab Flag" divider pdf_merger.py drops into the merged
PDF at every run/route boundary, plus the customer classification (pallet /
high-priority) that both the divider and the merged PDF's highlight pass
key off of - one place for "which customers are flagged", so the count on
the divider can never drift from what's actually highlighted on the dockets.
"""

from datetime import datetime
from typing import List

import fitz  # PyMuPDF

from models import PageInfo

# Highlight colors, as RGB floats 0-1. Reused for both the annotation
# highlight on docket pages (pdf_merger.py) and the matching swatch here.
PALLET_HIGHLIGHT_COLOR = (0.3, 0.6, 1.0)          # blue
HIGH_PRIORITY_HIGHLIGHT_COLOR = (0.8, 0.25, 0.1)  # blood orange


def normalize_customer(name: str) -> str:
    """Case/whitespace-insensitive key for matching customer names."""
    return " ".join(name.upper().split())


# Customers to always flag, in every file, regardless of company.
PALLET_CUSTOMERS = {normalize_customer(n) for n in [
    "IGA MT EVELYN SUPERMARKET   #596007 (PALLET)",
    "Champions IGA Bacchus Marsh (PALLET)",
    "Champions IGA Maddingley(PALLET)",
    "FOODWORKS BACCHUS MARSH (PALLET)",
    "KRISPY KREME T4 MELBOURNE AIRPORT",
    "SOUL ORIGIN MELBOURNE AIRPORT T4",
    "VIRGIN LOUNGE MELBOURNE",
    "VIRGIN LOUNGE MELBOURNE - BEYOND",
    "SUPA IGA ROMSEY PLUS LIQUOR",
    "MAXI FOODS SUPERMARKET UPPER FERNTR",
    "COCKATOO IGA PLUS LIQUOR",
]}

# Checked before PALLET_CUSTOMERS, so it wins on overlap.
HIGH_PRIORITY_CUSTOMERS = {normalize_customer(n) for n in [
    "EARL PRODUCTIONS",
    "GEORGE ST CAFE",
    "HARVEST BLEND",
    "GARDENWORLD CAFE(DOUBLE CHECK)",
    "THE DART AND MARLIN",
    "QT MELBOURNE (DOUBLE CHECK)",
    "AUCTION ROOM CAFE(NO-CRATES)",
    "THE RIDDELLS CREEK (FOODWORKS)",
    "HEATHERHILL CELLARS",
    "CARGO EATERY AND BEER GARDEN(DOUBLE CHECK)",
    "BERTH RESTAURANT AND EVENTS(DOUBLE CHECK)",
    "POSTMASTER HOTEL(DOUBLE CHECK)",
    "MOUNT MACEDON HOTEL(DOUBLE CHECK)",
    "CARNEGIE IGA PLUS LIQUOR",
    "IGA MONTROSE PLUS LIQUOR 62379016",
    
]}


def compute_run_stats(route: int, run_pages: List[PageInfo]) -> dict:

    """
    Tally the stats shown on a run separator page for one route.

    "Drops" are main (non-continuation) pages with a delivery number -
    continuation pages ride along with their drop and aren't counted again.
    """
    drops = [p for p in run_pages if not p.is_continuation and p.delivery is not None]
    return {
        "route": route,
        "lac_drops": sum(1 for p in drops if p.company == "LAC"),
        "rtr_drops": sum(1 for p in drops if p.company == "RTR"),
        "total_drops": len(drops),
        "pallet_count": sum(1 for p in drops if p.customer
                           and normalize_customer(p.customer) in PALLET_CUSTOMERS),
        "high_priority_count": sum(1 for p in drops if p.customer
                                  and normalize_customer(p.customer) in HIGH_PRIORITY_CUSTOMERS),
        "page_count": len(run_pages),
    }


def build_separator_page(stats: dict, width: float, height: float) -> bytes:
    """
    Render a one-page run-separator divider ("Tab Flag"): a black edge tab
    carrying the run number so it shows up while a stack is being riffled,
    and a stats block (route, LAC/RTR drop split, pallet and high-priority
    counts swatched in the same colors those customers get highlighted in
    on the docket pages, and a total). Sized to match the mediabox of the
    page it precedes, so it fits the stack.
    """
    doc = fitz.open()
    page = doc.new_page(width=width, height=height)

    bar_w = width * 0.14
    bar = fitz.Rect(width - bar_w, 0, width, height)
    page.draw_rect(bar, color=None, fill=(0.08, 0.07, 0.06))
    page.insert_textbox(
        bar, str(stats["route"]), fontsize=38, fontname="hebo",
        color=(1, 1, 1), align=fitz.TEXT_ALIGN_CENTER, rotate=90,
    )

    margin = width * 0.09
    x0, x1 = margin, width - bar_w - margin * 0.5
    y = height * 0.12

    page.insert_text((x0, y), f"RUN {stats['route']}", fontsize=10,
                    fontname="hebo", color=(0.45, 0.42, 0.36))
    y += 32

    rows = [
        ("ROUTE", str(stats["route"]), None),
        ("LAC DROPS", str(stats["lac_drops"]), None),
        ("RTR DROPS", str(stats["rtr_drops"]), None),
        ("PALLET", str(stats["pallet_count"]), PALLET_HIGHLIGHT_COLOR),
        ("HIGH PRIORITY", str(stats["high_priority_count"]), HIGH_PRIORITY_HIGHLIGHT_COLOR),
    ]
    for label, value, swatch in rows:
        label_x = x0
        if swatch:
            page.draw_rect(fitz.Rect(x0, y - 9, x0 + 9, y), color=None, fill=swatch)
            label_x = x0 + 15
        page.insert_text((label_x, y), label, fontsize=11, fontname="cour", color=(0.2, 0.19, 0.16))
        page.insert_text((x1 - 30, y), value, fontsize=11, fontname="hebo", color=(0.1, 0.09, 0.07))
        page.draw_line((x0, y + 7), (x1, y + 7), color=(0.85, 0.82, 0.75), width=0.6)
        y += 30

    page.draw_line((x0, y - 4), (x1, y - 4), color=(0.08, 0.07, 0.06), width=1.3)
    y += 20
    page.insert_text((x0, y), "TOTAL DROPS", fontsize=12, fontname="hebo", color=(0.08, 0.07, 0.06))
    page.insert_text((x1 - 34, y), str(stats["total_drops"]), fontsize=14,
                    fontname="hebo", color=(0.08, 0.07, 0.06))

    page.insert_text(
        (x0, height - 22),
        f"{stats['page_count']} PAGES · {datetime.now().strftime('%d %b %Y %H:%M')}",
        fontsize=8, fontname="cour", color=(0.5, 0.47, 0.4),
    )

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def build_separator_pdf_page(pages: List[PageInfo], route: int, width: float, height: float) -> bytes:
    """Convenience wrapper: tally `route`'s stats from `pages` and render the divider in one call."""
    run_pages = [p for p in pages if p.route == route]
    stats = compute_run_stats(route, run_pages)
    return build_separator_page(stats, width, height)