import fitz
import os
import config

def classify_pdf(file_path: str) -> dict:
    """
    Classifies a PDF file as NatHERS, BASIX, Plans, Hybrid, or Unknown
    based on text analysis of the first few pages and keywords.
    """
    if not os.path.exists(file_path):
        return {"file_type": "Unknown", "pages": 0, "error": "File does not exist"}
        
    try:
        doc = fitz.open(file_path)
        page_count = len(doc)

        # Determine pages to sample (keep small and configurable)
        sample_limit = max(1, int(getattr(config, "CLASSIFY_SAMPLE_PAGES", 3)))
        pages_to_sample = [0]
        if sample_limit >= 2 and page_count > 2:
            mid = page_count // 2
            pages_to_sample.append(mid)
        if sample_limit >= 3 and page_count > 1:
            pages_to_sample.append(page_count - 1)

        # Trim to unique and within range
        pages_to_sample = [p for i, p in enumerate(pages_to_sample) if p >= 0 and p < page_count]
        pages_to_sample = list(dict.fromkeys(pages_to_sample))[:sample_limit]

        texts = []
        for i in pages_to_sample:
            try:
                texts.append(doc[i].get_text().lower())
            except Exception:
                texts.append("")

        full_sample_text = " ".join(texts)
        
        # Check for NatHERS keywords
        nathers_kws = ["nathers", "nationwide house energy rating scheme", "firstrate5", "bers pro", "hero energy", "star rating"]
        
        n_count = full_sample_text.count("nathers")
        b_count = full_sample_text.count("basix")
        
        has_nathers = n_count > 0 or any(kw in full_sample_text for kw in ["nationwide house energy rating scheme", "firstrate5", "bers pro", "hero energy", "star rating"])
        has_basix = b_count >= 3 or any(kw in full_sample_text for kw in ["building sustainability index", "planningportal.nsw.gov.au"])
        
        # Check for Plans keywords
        plans_kws = ["drawing title", "ground floor plan", "elevations", "site plan", "section a", "architectural plans", "do not scale"]
        has_plans = any(kw in full_sample_text for kw in plans_kws)
        
        # Check for Colour Schedule keywords
        colour_kws = ["colour schedule", "color schedule", "finishes schedule", "selections", "external finishes"]
        has_colour = any(kw in full_sample_text for kw in colour_kws)
        
        # Determine classification
        file_type = "Unknown"
        
        if has_nathers and has_basix:
            if n_count > 4 * b_count:
                file_type = "NatHERS"
            elif b_count > 4 * n_count:
                file_type = "BASIX"
            else:
                file_type = "Hybrid"
        elif has_nathers:
            file_type = "NatHERS"
        elif has_basix:
            file_type = "BASIX"
        elif has_colour:
            file_type = "Colour Schedule"
        elif has_plans:
            file_type = "Plans"
        
        # Fallback to filename heuristic if text classification is Unknown or weak
        if file_type == "Unknown" or (file_type == "Plans" and not has_plans and len(full_sample_text.strip()) < 100):
            base_name = os.path.basename(file_path).lower()
            if any(k in base_name for k in ("plan", "drawing", "elevation", "site")):
                if "stamped plans" in base_name or "nathers stamped" in base_name:
                    file_type = "Plans"
                elif any(k in base_name for k in ("nathers", "nat-hers", "energy", "bers")) and page_count <= 15 and not any(p in base_name for p in ("stamped", "drawing")):
                    file_type = "NatHERS"
                else:
                    file_type = "Plans"
            elif any(k in base_name for k in ("nathers", "nat-hers", "energy", "bers")):
                file_type = "NatHERS"
            elif "basix" in base_name:
                file_type = "BASIX"
            elif any(k in base_name for k in ("colour", "color", "finish", "selection")):
                file_type = "Colour Schedule"
            elif page_count >= 10:
                file_type = "Plans"
            else:
                file_type = "Plans"  # Default assumption for construction PDFs
        
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
