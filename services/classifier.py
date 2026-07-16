import fitz
import os
import config

def classify_pdf(file_path: str) -> dict:
    """
    Classifies a PDF file as NatHERS, BASIX, Plans, Hybrid, or Unknown
    based on page geometry (aspect ratio, sizes) and structural/header signatures.
    """
    if not os.path.exists(file_path):
        return {"file_type": "Unknown", "pages": 0, "error": "File does not exist"}
        
    try:
        doc = fitz.open(file_path)
        page_count = len(doc)

        # Sample first page, middle page, and last page
        sample_limit = max(1, int(getattr(config, "CLASSIFY_SAMPLE_PAGES", 3)))
        pages_to_sample = [0]
        if sample_limit >= 2 and page_count > 2:
            pages_to_sample.append(page_count // 2)
        if sample_limit >= 3 and page_count > 1:
            pages_to_sample.append(page_count - 1)

        pages_to_sample = sorted(list(set([p for p in pages_to_sample if 0 <= p < page_count])))[:sample_limit]

        texts = []
        is_landscape_large = False
        
        # Check geometries of sampled pages
        for p_idx in pages_to_sample:
            page = doc[p_idx]
            rect = page.rect
            w, h = rect.width, rect.height
            # Large landscape pages (typically A3 or larger drawings)
            if w > h and w > 700:
                is_landscape_large = True
            
            try:
                texts.append(page.get_text().lower())
            except Exception:
                texts.append("")

        full_sample_text = " ".join(texts)
        
        # Clean text for strict signature matching
        clean_text = " ".join(full_sample_text.split())

        # 1. Structural Certificate Header Checks
        # NatHERS Certificates: require certified software name OR the formal nationwide header.
        # "nathers certificate" alone is NOT sufficient as it appears on stamped plan sheets.
        has_nathers_header = (
            "nationwide house energy rating scheme" in clean_text
            or "bers pro" in clean_text
            or "firstrate5" in clean_text
            or "hero energy rating" in clean_text
            or "hero v" in clean_text
            or (
                # NatHERS cert with window schedule + star rating is unambiguous
                "window and glazed door schedule" in clean_text
                and "star rating" in clean_text
            )
        )
        
        # BASIX Certificates: require a clear official structural identifier pair.
        # A plan with a BASIX stamp only has 'basix certificate' text but NOT the
        # official NSW Planning Portal URL or an explicit 'certificate number' anchor.
        has_basix_header = (
            # Full structural pattern: official title + official URL or cert number
            ("basix certificate" in clean_text or "building sustainability index" in clean_text)
            and (
                "planningportal.nsw.gov.au" in clean_text
                or "certificate number:" in clean_text
                or "basix commitments" in clean_text
            )
        )

        # 2. Structural Plans / Drawings Check (large landscape sheets or drawing keywords)
        has_plans_keywords = any(kw in clean_text for kw in [
            "drawing title", "do not scale", "ground floor plan", "site plan", 
            "elevations", "floor plan", "construction notes", "architectural plans"
        ])

        file_type = "Unknown"

        # Apply classification rules — certificate headers FIRST (strongest signal),
        # then geometry as tiebreaker when no cert signatures are found.
        # This prevents A4-landscape BASIX/NatHERS certs from being wrongly caught
        # by the "large landscape = Plans" geometry rule.
        if has_nathers_header and has_basix_header:
            file_type = "Hybrid"
        elif has_nathers_header:
            file_type = "NatHERS"
        elif has_basix_header:
            file_type = "BASIX"
        elif is_landscape_large:
            # Large landscape with no cert signatures = Plans (drawing set).
            # Even if they reference BASIX/NatHERS in notes, geometry wins here.
            file_type = "Plans"
        elif has_plans_keywords:
            file_type = "Plans"

        if file_type == "Unknown":
            base_name = os.path.basename(file_path).lower()
            if "basix" in base_name:
                file_type = "BASIX"
            elif any(k in base_name for k in ("nathers", "nat-hers", "energy", "bers")):
                file_type = "NatHERS"
            elif any(k in base_name for k in ("plan", "drawing", "elevation", "site")):
                file_type = "Plans"
            elif page_count >= 5:
                # Long files without certificate signatures are usually drawing sets
                file_type = "Plans"
            else:
                file_type = "Plans" # Default fallback for construction context

        doc.close()
        return {
            "file_type": file_type,
            "pages": page_count,
            "has_text": len(full_sample_text.strip()) > 0
        }
    except Exception as e:
        return {
            "file_type": "Unknown",
            "pages": 0,
            "error": str(e)
        }

