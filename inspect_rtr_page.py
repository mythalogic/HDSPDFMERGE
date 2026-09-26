"""
One-off diagnostic: dump what PyMuPDF sees on the first RTR page of a PDF -
raster images (get_image_info) and vector drawings (get_drawings), with
bounding boxes. Tells us whether the barcode/QR are images (my code's
assumption) or vector paths (needs a different detection approach).

Usage: python inspect_rtr_page.py "path\to\Picking_Slips_Sequenced_....pdf"
"""
import sys
import fitz

path = sys.argv[1]
doc = fitz.open(path)

target = None
for i, page in enumerate(doc):
    if "RTR Distribution" in (page.get_text() or ""):
        target = i
        break

if target is None:
    print("No page containing 'RTR Distribution' found.")
    sys.exit(1)

page = doc[target]
print(f"Page {target + 1} of {len(doc)} | page size: {page.rect.width:.1f} x {page.rect.height:.1f} pt\n")

images = page.get_image_info()
print(f"=== get_image_info(): {len(images)} raster image(s) ===")
for info in images:
    b = info["bbox"]
    w, h = b[2] - b[0], b[3] - b[1]
    aspect = w / h if h else 0
    print(f"  bbox=({b[0]:.1f},{b[1]:.1f},{b[2]:.1f},{b[3]:.1f}) "
          f"size={w:.1f}x{h:.1f} aspect={aspect:.2f}")

drawings = page.get_drawings()
print(f"\n=== get_drawings(): {len(drawings)} vector drawing(s) ===")
seen = set()
for d in drawings:
    r = d["rect"]
    w, h = r.width, r.height
    if w < 3 or h < 3:
        continue  # skip hairlines/borders
    key = (round(r.x0), round(r.y0), round(w), round(h))
    if key in seen:
        continue
    seen.add(key)
    aspect = w / h if h else 0
    print(f"  bbox=({r.x0:.1f},{r.y0:.1f},{r.x1:.1f},{r.y1:.1f}) "
          f"size={w:.1f}x{h:.1f} aspect={aspect:.2f}")

doc.close()