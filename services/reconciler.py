import math

def calculate_window_area(height_mm, width_mm, qty: int) -> float:
    """Calculates window area in square meters."""
    try:
        h = int(height_mm)
        w = int(width_mm)
    except (TypeError, ValueError):
        return 0.0
    if not h or not w:
        return 0.0
    return (h / 1000.0) * (w / 1000.0) * qty


def normalize_location(loc: str) -> str:
    """Normalize room location names for fuzzy matching."""
    if not loc:
        return ""
    loc = loc.lower().strip()
    replacements = {
        "bed 1": "bed1", "bedroom 1": "bed1", "bed1": "bed1", "br1": "bed1",
        "bed 2": "bed2", "bedroom 2": "bed2", "bed2": "bed2", "br2": "bed2",
        "bed 3": "bed3", "bedroom 3": "bed3", "bed3": "bed3", "br3": "bed3",
        "bed 4": "bed4", "bedroom 4": "bed4", "bed4": "bed4", "br4": "bed4",
        "bath": "bath", "bathroom": "bath", "ensuite": "bath", "ens": "bath", "en suite": "bath",
        "fam": "living", "family": "living", "living": "living", "lounge": "living",
        "din": "dining", "dining": "dining",
        "kit": "kitchen", "kitchen": "kitchen",
        "ver": "verandah", "verandah": "verandah", "veranda": "verandah", "porch": "verandah",
        "wir": "closet", "walk in robe": "closet", "wardrobe": "closet", "closet": "closet",
        "laundry": "laundry", "utility": "laundry",
        "garage": "garage", "entry": "entry", "patio": "patio", "study": "study",
    }
    for key, val in replacements.items():
        if key in loc:
            loc = loc.replace(key, val)
    return loc


def locations_match(loc1: str, loc2: str) -> bool:
    """Check if two location names match (fuzzy)."""
    n1 = normalize_location(loc1)
    n2 = normalize_location(loc2)
    return n1 == n2 or n1 in n2 or n2 in n1 or not n1 or not n2


def _flag_category_label(flag_type: str) -> str:
    """Convert internal flag_type to human-readable category for the Excel report."""
    labels = {
        "dimension_mismatch":    "Dimension Mismatch",
        "orientation_mismatch":  "Orientation Mismatch",
        "opening_type_mismatch": "Type Mismatch",
        "glazing_mismatch":      "Glazing Mismatch",
        "frame_mismatch":        "Frame Mismatch",
        "missing_in_nathers":    "Missing in NatHERS",
        "missing_in_plans":      "Missing in Plans",
        "basix_aggregate_mismatch": "BASIX Area Mismatch",
        "low_confidence":        "Low Confidence",
    }
    return labels.get(flag_type, flag_type.replace("_", " ").title())


# ---------------------------------------------------------------------------
# FIX #7: Values we should NOT assert from plans when the plan doesn't specify them.
# If these come from a hardcoded default in the extractor prompt, don't treat as fact.
# ---------------------------------------------------------------------------
PLAN_DEFAULT_GLAZING_STRINGS = {
    "double glazed clear", "double glazed", "double-glazed",
    "single glazed clear", "single glazed", "standard glazing",
    "nathers compliant", "nathers", "as per nathers", "per nathers",
    "nathers specification", "nathers requirements", "compliant",
    "nathers compliant glazing", "nathers glazing",
    "tbd", "unknown", "n/a", "none", "", "null"
}
PLAN_DEFAULT_TYPE_STRINGS = {
    "fixed", "window", "standard", "tbd", "unknown", "n/a", "none", "", "null"
}
PLAN_DEFAULT_FRAME_STRINGS = {
    "tbd", "unknown", "n/a", "none", "", "null"
}


def _plan_value_is_asserted(val: str, defaults: set) -> bool:
    """Return True only if the plan value is a real assertion (not a generic default)."""
    if not val:
        return False
    return val.strip().lower() not in defaults


def determine_frame_material(desc: str) -> str:
    """Derives frame material from product description, defaulting to Aluminium."""
    if not desc:
        return "Aluminium"
    desc_lower = desc.lower()
    if any(k in desc_lower for k in ["timber", "wood", "cedar", "mdf"]):
        return "Timber"
    if any(k in desc_lower for k in ["upvc", "pvc", "vinyl"]):
        return "uPVC"
    return "Aluminium"


def is_glazed_opening(r: dict) -> bool:
    """Returns True if the opening is glazed (not a solid timber/opaque door)."""
    op_type = str(r.get("opening_type", "")).lower()
    t_str = str(r.get("type", "")).lower()
    g_str = str(r.get("glazing", "")).lower()
    
    # Windows and Louvres are always glazed
    if "window" in op_type or "louvre" in op_type:
        return True
        
    # Opaque/solid doors are not glazed
    if any(k in t_str for k in ["solid", "opaque", "panel", "timber door", "wood door", "garage"]):
        return False
    if any(k in g_str for k in ["solid", "opaque", "panel", "timber", "wood"]):
        return False
        
    # If it's a sliding/bifold/stacker door, it's glazed
    if any(k in t_str for k in ["sliding", "bifold", "stacker", "bi-fold"]):
        return True
        
    # For other doors (like hinged doors), check if they have valid glazing
    glazing_val = r.get("glazing")
    if not glazing_val or g_str in ["none", "null", "unknown", "per nathers schedule", "tbd"]:
        return False
        
    return True


def normalize_glazing_category(glazing_str: str) -> dict:
    """Extract features from glazing description to compare semantically."""
    if not glazing_str:
        return {"type": "unknown", "low_e": False, "obscure": False, "laminated": False}
    s = glazing_str.lower()
    g_type = "unknown"
    if "triple" in s or " tg " in s or "/tg/" in s:
        g_type = "triple"
    elif "double" in s or " dg " in s or "/dg/" in s or "dg" in s or "/10/" in s or "/12/" in s or "/8/" in s or "/6/" in s or "/9/" in s:
        g_type = "double"
    elif "single" in s or " sg " in s or "/sg/" in s or "sg" in s:
        g_type = "single"

    low_e = "low e" in s or "low-e" in s or "lowe" in s or "cpclr" in s or "cpgry" in s or "smartglass" in s or "comfort" in s
    obscure = "obscure" in s or "obs" in s or "frosted" in s or "translucent" in s
    laminated = "lam" in s or "laminated" in s

    return {"type": g_type, "low_e": low_e, "obscure": obscure, "laminated": laminated}


def glazing_mismatch(p_glazing: str, n_glazing: str) -> bool:
    """Check if plan and NatHERS glazing specifications mismatch semantically."""
    if not p_glazing or not n_glazing:
        return False
    p_cat = normalize_glazing_category(p_glazing)
    n_cat = normalize_glazing_category(n_glazing)
    if p_cat["type"] != "unknown" and n_cat["type"] != "unknown":
        if p_cat["type"] != n_cat["type"]:
            return True
    if p_cat["low_e"] and not n_cat["low_e"]:
        return True
    if p_cat["obscure"] and not n_cat["obscure"]:
        return True
    if p_cat["laminated"] and not n_cat["laminated"]:
        return True
    return False


def classify_opening_type(matched_type: str, height: int, tag: str) -> str:
    """Classify the opening type based on operability, dimensions, and tags."""
    type_lower = matched_type.lower() if matched_type else ""
    tag_lower = str(tag).lower() if tag else ""
    
    # 1. First, check special louvre class
    if "louvre" in type_lower:
        return "Louvre"
        
    # 2. Check if it's explicitly a window type
    is_window_type = False
    if any(w in type_lower.replace("_", " ") for w in ["awning", "casement", "double hung", "fixed", "louvre"]):
        is_window_type = True
        
    is_door = False
    if not is_window_type:
        import re
        if "door" in type_lower:
            is_door = True
        elif "bifold" in type_lower or "stacker" in type_lower or "bi-fold" in type_lower:
            is_door = True
        elif re.match(r'^d\d+', tag_lower):
            is_door = True
        elif "alsd" in tag_lower or "csd" in tag_lower:
            is_door = True
        elif "sd" in tag_lower:
            # Avoid matching "asd" window tags unless height indicates a door (>= 2000)
            if "asd" in tag_lower:
                if height and height >= 2000:
                    is_door = True
            else:
                is_door = True
        elif height and height >= 2000 and ("sliding" in type_lower or "hinged" in type_lower):
            is_door = True

    if is_door:
        # Reserve Bi-fold/Stacker Door only for actual bifold/stacker
        if "bifold" in type_lower or "stacker" in type_lower or "bi-fold" in type_lower or "bifold" in tag_lower or "stacker" in tag_lower:
            return "Bi-fold/Stacker Door"
        return "Door"
        
    return "Window"



def orientations_match(o1: str, o2: str) -> bool:
    """Check if orientations match."""
    if not o1 or not o2:
        return True
    return o1.strip().upper() == o2.strip().upper()


def types_match(t1: str, t2: str) -> bool:
    """Check if types match."""
    if not t1 or not t2:
        return True
    t1_norm = t1.lower().replace("_", " ").replace("-", " ").strip()
    t2_norm = t2.lower().replace("_", " ").replace("-", " ").strip()
    return t1_norm == t2_norm or t1_norm in t2_norm or t2_norm in t1_norm


def calculate_match_score(plan_w: dict, nat_w: dict) -> float:
    """Calculate the match score between a plan window and a NatHERS window."""
    p_tag = str(plan_w.get("tag", "")).strip().upper()
    n_tag = str(nat_w.get("tag", "")).strip().upper()
    tags_match = (p_tag == n_tag) and p_tag != ""

    ph = plan_w.get("height")
    pw = plan_w.get("width")
    nh = nat_w.get("height")
    nw = nat_w.get("width")

    # Determine if either candidate is a door
    p_type = plan_w.get("type", "")
    n_type = nat_w.get("type", "")
    p_is_door = "door" in p_type.lower() or "door" in str(plan_w.get("opening_type", "")).lower() or plan_w.get("tag", "").lower().startswith("d")
    n_is_door = "door" in n_type.lower() or "door" in str(nat_w.get("opening_type", "")).lower() or nat_w.get("tag", "").lower().startswith("d")
    is_door_pair = p_is_door or n_is_door

    dim_diff_h = abs(ph - nh) if (ph is not None and nh is not None) else None
    dim_diff_w = abs(pw - nw) if (pw is not None and nw is not None) else None

    # Relax height tolerance for doors (standard door height varies: 2040mm vs 2100mm)
    height_tolerance = 100 if is_door_pair else 50

    dims_within_tolerance = False
    if dim_diff_h is not None and dim_diff_w is not None:
        if dim_diff_h <= height_tolerance and dim_diff_w <= 50:
            dims_within_tolerance = True

    # If tags don't match, they must have dimensions within tolerance to be paired
    if not tags_match and not dims_within_tolerance:
        return 0.0

    score = 0.0
    if tags_match:
        score += 100.0

    if dim_diff_h is not None and dim_diff_w is not None:
        if dim_diff_h <= 5 and dim_diff_w <= 5:
            score += 60.0
        elif dim_diff_h <= height_tolerance and dim_diff_w <= 50:
            score += 45.0

    p_loc = plan_w.get("location", "")
    n_loc = nat_w.get("location", "")
    if p_loc and n_loc and locations_match(p_loc, n_loc):
        score += 30.0

    p_orient = plan_w.get("orientation", "")
    n_orient = nat_w.get("orientation", "")
    if p_orient and n_orient and orientations_match(p_orient, n_orient):
        score += 20.0

    p_type = plan_w.get("type", "")
    n_type = nat_w.get("type", "")
    if p_type and n_type and types_match(p_type, n_type):
        score += 15.0

    return score


def reconcile_takeoff(plans_windows: list, nathers_windows: list, basix_data: dict, has_plans: bool = True, has_plans_file: bool = False) -> dict:
    """
    Reconciles window schedules from Plans and NatHERS,
    cross-checks against BASIX, calculates confidence,
    and returns takeoff rows and consistency flags.
    """
    takeoff_rows = []
    flags = []

    # 1. Handle No Plans case (D2)
    if not has_plans:
        for nat_w in (nathers_windows or []):
            nat_tag = nat_w.get("tag", "Unknown")
            nat_loc = nat_w.get("location", "")
            nat_h = nat_w.get("height")
            nat_ww = nat_w.get("width")
            nat_qty = nat_w.get("quantity", 1)
            nat_type = nat_w.get("type", "window")
            nat_orient = nat_w.get("orientation", "TBD")
            nat_glazing = nat_w.get("glazing", "Per NatHERS Schedule")
            nat_u = nat_w.get("u_value", "N/A")
            nat_shgc = nat_w.get("shgc", "N/A")
            opening_type = classify_opening_type(nat_type, nat_h, nat_tag)
            nat_frame = nat_w.get("frame_material") or nat_w.get("frame")
            if not nat_frame:
                nat_frame = "Aluminium" if opening_type != "Door" else None
            nat_src = nat_w.get("src_ref", "NatHERS")

            u_shgc_display = ""
            if nat_u and nat_u != "N/A":
                u_shgc_display = f"U: {nat_u}"
            if nat_shgc and nat_shgc != "N/A":
                u_shgc_display += (" / " if u_shgc_display else "") + f"SHGC: {nat_shgc}"
            if not u_shgc_display:
                u_shgc_display = "N/A"

            takeoff_rows.append({
                "location":     nat_loc,
                "tag":          nat_tag,
                "height":       nat_h,
                "width":        nat_ww,
                "type":         nat_type,
                "opening_type": opening_type,
                "orientation":  nat_orient or "TBD",
                "glazing":      nat_glazing,
                "u_value":      nat_u,
                "shgc":         nat_shgc,
                "u_shgc":       u_shgc_display,
                "frame":        nat_frame,
                "quantity":     nat_qty,
                "confidence":   100.0,
                "src_ref":      nat_src
            })

        description_str = "No floor plan documents were supplied in this submission. Glazing takeoff is based entirely on the NatHERS certificate schedule."
        if has_plans_file:
            description_str = "Floor plans were supplied, but no readable layout or schedule could be processed (e.g. image-only sheets). Glazing takeoff is based entirely on the NatHERS certificate schedule."

        flags.append({
            "flag_type": "info",
            "item_ref": "Plans",
            "category": "Info",
            "opening_id": "Plans",
            "description": description_str,
            "severity": "Low"
        })

        try:
            total_plan_area = sum(
                calculate_window_area(r["height"], r["width"], r["quantity"])
                for r in takeoff_rows
                if r.get("height") and r.get("width") and is_glazed_opening(r)
            )
        except Exception:
            total_plan_area = 0.0

        basix_area = basix_data.get("total_glazing_area")
        if basix_area and total_plan_area > 0:
            discrepancy_pct = abs(total_plan_area - basix_area) / float(basix_area) * 100.0
            if discrepancy_pct > 10.0:
                direction = "over-counting" if total_plan_area > basix_area else "under-counting"
                flags.append({
                    "flag_type": "basix_aggregate_mismatch",
                    "item_ref": "BASIX Glazing Total",
                    "category": _flag_category_label("basix_aggregate_mismatch"),
                    "opening_id": "BASIX Glazing",
                    "description": (
                        f"Extracted plan glazing area ({total_plan_area:.2f} m²) differs from "
                        f"BASIX certificate total ({basix_area:.2f} m²) by {discrepancy_pct:.1f}%. "
                        f"The BASIX/NatHERS certificate value ({basix_area:.2f} m²) is the verified anchor. "
                        f"Review the plan extraction for {direction} — possible phantom openings, "
                        f"excluded door types, or scanned-page misreads."
                    ),
                    "severity": "High"
                })

        critical_flags = [f for f in flags if f.get("severity") in ("High", "Medium")]
        review_required = bool(critical_flags)
        review_reason = f"Job has {len(critical_flags)} critical consistency flags (High/Medium severity) requiring manual review." if review_required else ""

        return {
            "rows":               takeoff_rows,
            "flags":              flags,
            "overall_confidence": 100.0,
            "is_rejected":        False,
            "rejection_reason":   "",
            "review_required":    review_required,
            "review_reason":      review_reason,
            "basix_details":      basix_data,
            "plan_glazing_area":  total_plan_area,
            "cert_glazing_area":  basix_area,
        }

    # Expand plans and NatHERS windows by quantity to match individual instances
    expanded_plans = []
    for pw in (plans_windows or []):
        qty = pw.get("quantity", 1)
        try:
            qty_int = int(qty)
        except Exception:
            qty_int = 1
        if qty_int <= 0:
            qty_int = 1
        for _ in range(qty_int):
            copy_pw = dict(pw)
            copy_pw["quantity"] = 1
            expanded_plans.append(copy_pw)
            
    expanded_nathers = []
    for nw in (nathers_windows or []):
        qty = nw.get("quantity", 1)
        try:
            qty_int = int(qty)
        except Exception:
            qty_int = 1
        if qty_int <= 0:
            qty_int = 1
        for _ in range(qty_int):
            copy_nw = dict(nw)
            copy_nw["quantity"] = 1
            expanded_nathers.append(copy_nw)

    plans_windows = expanded_plans
    nathers_windows = expanded_nathers

    # 2. Perform Scoring-Based Matching (D3)
    candidate_pairs = []
    for i, plan_w in enumerate(plans_windows):
        for j, nat_w in enumerate(nathers_windows):
            score = calculate_match_score(plan_w, nat_w)
            if score > 0:
                candidate_pairs.append((i, j, score))

    candidate_pairs.sort(key=lambda x: x[2], reverse=True)

    matched_plans_indices = set()
    matched_nathers_indices = set()
    plan_to_nathers_match = {}

    for i, j, score in candidate_pairs:
        if i in matched_plans_indices or j in matched_nathers_indices:
            continue
        matched_plans_indices.add(i)
        matched_nathers_indices.add(j)
        plan_to_nathers_match[i] = j

    # 3. Process matches and plan-only windows
    for i, plan_w in enumerate(plans_windows):
        tag      = plan_w.get("tag", "Unknown")
        loc      = plan_w.get("location", "")
        h        = plan_w.get("height")
        w        = plan_w.get("width")
        w_type   = plan_w.get("type", "window")
        qty      = plan_w.get("quantity", 1)
        orientation = plan_w.get("orientation")
        frame    = plan_w.get("frame")
        glazing  = plan_w.get("glazing")
        src_ref  = plan_w.get("src_ref", "Plans")

        match_idx = plan_to_nathers_match.get(i, -1)

        row_confidence  = 100.0
        matched_glazing = glazing
        matched_frame   = frame
        matched_u_value = ""
        matched_shgc    = ""
        matched_location = loc
        matched_type    = w_type
        matched_h       = h
        matched_w       = w

        if match_idx != -1:
            nat_w = nathers_windows[match_idx]

            # Use NatHERS room label as authoritative location
            nat_location = nat_w.get("location", "")
            if nat_location:
                matched_location = nat_location

            # Authoritative window type from NatHERS
            nat_type = nat_w.get("type")
            if nat_type:
                matched_type = nat_type

            # D9: Prefer certificate dimensions
            nh = nat_w.get("height")
            nw = nat_w.get("width")
            if nh:
                matched_h = nh
            if nw:
                matched_w = nw

            # Dimension check
            if h and w and nh and nw:
                if abs(h - nh) > 5 or abs(w - nw) > 5:
                    flags.append({
                        "flag_type": "dimension_mismatch",
                        "item_ref": tag,
                        "category": _flag_category_label("dimension_mismatch"),
                        "opening_id": tag,
                        "description": f"Dimension mismatch for {tag} ({matched_location}): Plans {h}H×{w}W vs NatHERS {nh}H×{nw}W.",
                        "severity": "High"
                    })
                    row_confidence -= 20.0

            # Orientation check
            n_orient = nat_w.get("orientation")
            if orientation and n_orient and not orientations_match(orientation, n_orient):
                flags.append({
                    "flag_type": "orientation_mismatch",
                    "item_ref": tag,
                    "category": _flag_category_label("orientation_mismatch"),
                    "opening_id": tag,
                    "description": f"Orientation mismatch for {tag} ({matched_location}): Plans '{orientation}' vs NatHERS '{n_orient}'.",
                    "severity": "High"
                })
                row_confidence -= 15.0
            elif not orientation and n_orient:
                orientation = n_orient

            # Type check
            if w_type and nat_type and not types_match(w_type, nat_type) and _plan_value_is_asserted(w_type, PLAN_DEFAULT_TYPE_STRINGS):
                flags.append({
                    "flag_type": "opening_type_mismatch",
                    "item_ref": tag,
                    "category": _flag_category_label("opening_type_mismatch"),
                    "opening_id": tag,
                    "description": f"Type mismatch for {tag} ({matched_location}): Plans '{w_type}' vs NatHERS '{nat_type}'.",
                    "severity": "Medium"
                })
                row_confidence -= 15.0

            # Glazing check (D6)
            n_glazing = nat_w.get("glazing")
            if glazing and n_glazing and _plan_value_is_asserted(glazing, PLAN_DEFAULT_GLAZING_STRINGS):
                if glazing_mismatch(glazing, n_glazing):
                    flags.append({
                        "flag_type": "glazing_mismatch",
                        "item_ref": tag,
                        "category": _flag_category_label("glazing_mismatch"),
                        "opening_id": tag,
                        "description": f"Glazing mismatch for {tag} ({matched_location}): Plans '{glazing}' vs NatHERS '{n_glazing}'.",
                        "severity": "Medium"
                    })
                    row_confidence -= 10.0

            # Frame check
            n_frame = nat_w.get("frame_material") or nat_w.get("frame")
            if frame and n_frame and _plan_value_is_asserted(frame, PLAN_DEFAULT_FRAME_STRINGS):
                if frame.lower().strip() != n_frame.lower().strip() and frame.lower() not in n_frame.lower() and n_frame.lower() not in frame.lower():
                    flags.append({
                        "flag_type": "frame_mismatch",
                        "item_ref": tag,
                        "category": _flag_category_label("frame_mismatch"),
                        "opening_id": tag,
                        "description": f"Frame mismatch for {tag} ({matched_location}): Plans '{frame}' vs NatHERS '{n_frame}'.",
                        "severity": "Medium"
                    })
                    row_confidence -= 10.0

            # Use NatHERS specifications, fallback to plans
            matched_glazing = n_glazing or glazing
            matched_frame   = n_frame or frame
            matched_u_value = nat_w.get("u_value", "")
            matched_shgc    = nat_w.get("shgc", "")

            src_ref = f"{src_ref} / {nat_w.get('src_ref', 'NatHERS')}"
        else:
            # Plans only
            temp_r = {
                "opening_type": classify_opening_type(matched_type, matched_h, tag),
                "type": matched_type,
                "glazing": glazing,
                "frame": frame
            }
            if is_glazed_opening(temp_r):
                flags.append({
                    "flag_type": "missing_in_nathers",
                    "item_ref": tag,
                    "category": _flag_category_label("missing_in_nathers"),
                    "opening_id": tag,
                    "description": f"{tag} found on plans ({matched_location}) but not in NatHERS schedule. Verify manually.",
                    "severity": "Medium"
                })
                row_confidence -= 30.0

        opening_type = classify_opening_type(matched_type, matched_h, tag)

        row_confidence = max(0.0, row_confidence)
        if row_confidence < 70.0:
            flags.append({
                "flag_type": "low_confidence",
                "item_ref": tag,
                "category": _flag_category_label("low_confidence"),
                "opening_id": tag,
                "description": f"{tag} ({matched_location}): Low confidence ({row_confidence:.0f}%) — verify specs manually.",
                "severity": "Low"
            })

        u_shgc_display = ""
        if matched_u_value and matched_u_value != "N/A":
            u_shgc_display = f"U: {matched_u_value}"
        if matched_shgc and matched_shgc != "N/A":
            u_shgc_display += (" / " if u_shgc_display else "") + f"SHGC: {matched_shgc}"
        if not u_shgc_display:
            u_shgc_display = "N/A"

        takeoff_rows.append({
            "location":     matched_location,
            "tag":          tag,
            "height":       matched_h,
            "width":        matched_w,
            "type":         matched_type,
            "opening_type": opening_type,
            "orientation":  orientation or "TBD",
            "glazing":      matched_glazing or "Per NatHERS Schedule",
            "u_value":      matched_u_value or "N/A",
            "shgc":         matched_shgc or "N/A",
            "u_shgc":       u_shgc_display,
            "frame":        matched_frame or ("Aluminium" if opening_type != "Door" else None),
            "quantity":     qty,
            "confidence":   row_confidence,
            "src_ref":      src_ref
        })

    # Add NatHERS-only items as takeoff rows
    for j, nat_w in enumerate(nathers_windows):
        if j not in matched_nathers_indices:
            nat_tag = nat_w.get("tag", "Unknown")
            nat_loc = nat_w.get("location", "")
            nat_h   = nat_w.get("height")
            nat_ww  = nat_w.get("width")
            nat_qty = nat_w.get("quantity", 1)
            nat_type = nat_w.get("type", "window")
            nat_orient = nat_w.get("orientation", "TBD")
            nat_glazing = nat_w.get("glazing", "Per NatHERS Schedule")
            nat_u   = nat_w.get("u_value", "N/A")
            nat_shgc = nat_w.get("shgc", "N/A")
            opening_type = classify_opening_type(nat_type, nat_h, nat_tag)
            nat_frame = nat_w.get("frame_material") or nat_w.get("frame")
            if not nat_frame:
                nat_frame = "Aluminium" if opening_type != "Door" else None
            nat_src = nat_w.get("src_ref", "NatHERS")
            nat_confidence = 70.0

            u_shgc_display = ""
            if nat_u and nat_u != "N/A":
                u_shgc_display = f"U: {nat_u}"
            if nat_shgc and nat_shgc != "N/A":
                u_shgc_display += (" / " if u_shgc_display else "") + f"SHGC: {nat_shgc}"
            if not u_shgc_display:
                u_shgc_display = "N/A"

            temp_r = {
                "opening_type": opening_type,
                "type": nat_type,
                "glazing": nat_glazing,
                "frame": nat_frame
            }
            if is_glazed_opening(temp_r):
                flags.append({
                    "flag_type": "missing_in_plans",
                    "item_ref": nat_tag,
                    "category": _flag_category_label("missing_in_plans"),
                    "opening_id": nat_tag,
                    "description": f"{nat_tag} ({nat_loc}) listed in NatHERS but not found on floor plans. Verify location on drawings.",
                    "severity": "Medium"
                })

            takeoff_rows.append({
                "location":     nat_loc,
                "tag":          nat_tag,
                "height":       nat_h,
                "width":        nat_ww,
                "type":         nat_type,
                "opening_type": opening_type,
                "orientation":  nat_orient or "TBD",
                "glazing":      nat_glazing,
                "u_value":      nat_u,
                "shgc":         nat_shgc,
                "u_shgc":       u_shgc_display,
                "frame":        nat_frame,
                "quantity":     nat_qty,
                "confidence":   nat_confidence,
                "src_ref":      nat_src
            })

    # 4. BASIX aggregate cross-check
    try:
        total_plan_area = sum(
            calculate_window_area(r["height"], r["width"], r["quantity"])
            for r in takeoff_rows
            if r.get("height") and r.get("width") and is_glazed_opening(r)
        )
    except Exception:
        total_plan_area = 0.0

    basix_area = basix_data.get("total_glazing_area")
    if basix_area and total_plan_area > 0:
        discrepancy_pct = abs(total_plan_area - basix_area) / float(basix_area) * 100.0
        if discrepancy_pct > 10.0:
            direction = "over-counting" if total_plan_area > basix_area else "under-counting"
            flags.append({
                "flag_type": "basix_aggregate_mismatch",
                "item_ref": "BASIX Glazing Total",
                "category": _flag_category_label("basix_aggregate_mismatch"),
                "opening_id": "BASIX Glazing",
                "description": (
                    f"Extracted plan glazing area ({total_plan_area:.2f} m²) differs from "
                    f"BASIX certificate total ({basix_area:.2f} m²) by {discrepancy_pct:.1f}%. "
                    f"The BASIX/NatHERS certificate value ({basix_area:.2f} m²) is the verified anchor. "
                    f"Review the plan extraction for {direction} — possible phantom openings, "
                    f"excluded door types, or scanned-page misreads."
                ),
                "severity": "High"
            })

    # 5. Calibrate overall confidence (D1)
    unmatched_count = len([f for f in flags if f["flag_type"] in ("missing_in_plans", "missing_in_nathers")])
    if takeoff_rows:
        base_confidence = sum(r["confidence"] for r in takeoff_rows) / len(takeoff_rows)
        # Apply a capped penalty of 2.0% per unmatched/missing opening (max penalty 20.0%)
        unmatched_penalty = min(20.0, unmatched_count * 2.0)
        overall_confidence = max(0.0, base_confidence - unmatched_penalty)
    else:
        overall_confidence = 0.0

    # 6. Pass/fail logic
    low_conf_rows = [r for r in takeoff_rows if r["confidence"] < 70.0]
    is_rejected = False
    rejection_reason = ""

    if overall_confidence < 50.0:
        is_rejected = True
        rejection_reason = f"Overall job confidence ({overall_confidence:.1f}%) is below the 50% quality threshold."
    elif len(takeoff_rows) >= 5 and (len(low_conf_rows) / len(takeoff_rows)) >= 0.25:
        is_rejected = True
        percent_low = (len(low_conf_rows) / len(takeoff_rows)) * 100.0
        rejection_reason = f"{percent_low:.1f}% of rows are below the 70% confidence limit (exceeds 25% tolerance)."

    critical_flags = [f for f in flags if f.get("severity") in ("High", "Medium")]
    if critical_flags:
        review_required = True
        review_reason = f"Job has {len(critical_flags)} critical consistency flags (High/Medium severity) requiring manual review."
    else:
        review_required = False
        review_reason = ""

    # Ensure sequential tags (e.g. W1, W2, D1, D2) are unique in the output
    seen_sequential_tags = {}
    for r in takeoff_rows:
        tag = r.get("tag", "")
        import re
        if re.match(r'^[wdWD]\d+$', tag):
            tag_upper = tag.upper()
            if tag_upper in seen_sequential_tags:
                seen_sequential_tags[tag_upper] += 1
                r["tag"] = f"{tag}-{seen_sequential_tags[tag_upper]}"
            else:
                seen_sequential_tags[tag_upper] = 1

    return {
        "rows":               takeoff_rows,
        "flags":              flags,
        "overall_confidence": overall_confidence,
        "is_rejected":        is_rejected,
        "rejection_reason":   rejection_reason,
        "review_required":    review_required,
        "review_reason":      review_reason,
        "basix_details":      basix_data,
        "plan_glazing_area":  total_plan_area,
        "cert_glazing_area":  basix_area,
    }

