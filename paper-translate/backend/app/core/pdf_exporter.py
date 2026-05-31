"""Export translated PDF with bilingual annotations.

Reads the original PDF and overlays translated text blocks on each page
using PyMuPDF (fitz).  Translations appear as yellow-highlighted annotations
positioned near their corresponding original text.
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Overlay style constants
HIGHLIGHT_COLOR = (1.0, 1.0, 0.65, 0.55)  # Light yellow, semi-transparent
TEXT_COLOR = (0.1, 0.1, 0.1)  # Near-black
FONT_SIZE_FACTOR = 0.85  # Translation text slightly smaller than original


def export_bilingual_pdf(
    source_pdf_path: str,
    pages_data: List[Dict[str, Any]],
    output_path: str,
) -> int:
    """Create a bilingual PDF by overlaying translations on the original.

    Args:
        source_pdf_path: Path to the original PDF file.
        pages_data: List of page dicts from the translation result,
            each containing 'page_number' and 'translated_blocks'.
        output_path: Where to save the exported PDF.

    Returns:
        File size in bytes of the generated PDF.
    """
    doc = fitz.open(source_pdf_path)

    for page_data in pages_data:
        page_num = page_data["page_number"]  # 1-indexed
        translated_blocks = page_data.get("translated_blocks", [])

        if not translated_blocks:
            continue

        # fitz pages are 0-indexed
        page_idx = page_num - 1
        if page_idx < 0 or page_idx >= len(doc):
            logger.warning(f"Skipping out-of-range page {page_num}")
            continue

        page = doc[page_idx]

        for block in translated_blocks:
            text = block.get("text", "").strip()
            if not text or block.get("block_type") == "formula":
                continue

            bbox = block.get("bbox")
            if not bbox or len(bbox) != 4:
                continue

            # bbox is (x0, y0, x1, y1) in PDF points
            x0, y0, x1, y1 = bbox
            orig_font_size = block.get("font_size", 12)
            font_size = orig_font_size * FONT_SIZE_FACTOR

            # Calculate the position for the translation overlay.
            # Place it directly below the original text block.
            rect = fitz.Rect(x0, y1, x1, y1 + _calc_translation_height(page, text, font_size, x1 - x0))

            # Draw a semi-transparent yellow background
            page.draw_rect(
                rect,
                color=None,
                fill=HIGHLIGHT_COLOR,
            )

            # Insert translation text
            # Use 'helv' (Helvetica) for reliable CJK/English rendering
            try:
                # Try inserting with font size auto-fit
                text_rect = fitz.Rect(rect.x0 + 3, rect.y0 + 1, rect.x1 - 3, rect.y1 - 1)
                rc = page.insert_textbox(
                    text_rect,
                    text,
                    fontsize=font_size,
                    fontname="helv",
                    color=TEXT_COLOR,
                    align=0,  # Left-aligned
                    render_mode=0,
                )
                if rc.y1 < rect.y1 and rc.y0 > rect.y0:
                    # Text fitted — nothing more to do
                    pass
                else:
                    # Text didn't fully fit; expand rect and try once more
                    expanded = fitz.Rect(rect.x0, rect.y1, rect.x1, rect.y1 + rect.height * 0.5)
                    page.draw_rect(expanded, color=None, fill=HIGHLIGHT_COLOR)
                    page.insert_textbox(
                        fitz.Rect(expanded.x0 + 3, expanded.y0 + 1, expanded.x1 - 3, expanded.y1 - 1),
                        text,
                        fontsize=font_size * 0.9,
                        fontname="helv",
                        color=TEXT_COLOR,
                        align=0,
                    )
            except Exception as e:
                logger.warning(f"Failed to insert text on page {page_num}: {e}")

    doc.save(output_path, deflate=True, garbage=3)
    file_size = Path(output_path).stat().st_size
    doc.close()
    return file_size


def _calc_translation_height(
    page: fitz.Page,
    text: str,
    font_size: float,
    width: float,
) -> float:
    """Estimate the height needed for a translation text block.

    Args:
        page: The PyMuPDF page (for resolution reference).
        text: The translation text.
        font_size: Desired font size.
        width: Available width in points.

    Returns:
        Estimated height in points.
    """
    if width <= 0:
        return font_size * 2

    # Rough estimate: each CJK char is ~font_size wide,
    # each Latin char is ~font_size * 0.55 wide.
    # Average them for mixed text.
    avg_char_width = font_size * 0.6
    chars_per_line = max(1, int(width / avg_char_width))
    num_lines = max(1, (len(text) + chars_per_line - 1) // chars_per_line)

    # Add padding
    return num_lines * font_size * 1.3 + 4
