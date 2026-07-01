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


def reconcile_takeoff(plans_windows: list, nathers_windows: list, basix_data: dict) -> dict:
    """
    Reconciles window schedules from Plans and NatHERS,
    cross-checks against BASIX, calculates confidence,
    and returns takeoff rows and consistency flags.
    """
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

    takeoff_rows = []
    flags = []

    matched_nathers_indices = set()

    def orientations_match(o1, o2):
        if not o1 or not o2:
            return True
        return o1.strip().upper() == o2.strip().upper()

    for plan_w in plans_windows:
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

        # Match strategy 1: By tag
        match_idx = -1
        for j, nat_w in enumerate(nathers_windows):
            if j in matched_nathers_indices:
                continue
            if str(nat_w.get("tag", "")).strip().upper() == str(tag).strip().upper():
                match_idx = j
                break

        # Match strategy 1.5: By location and dimensions (within 50 mm)
        if match_idx == -1:
            for j, nat_w in enumerate(nathers_windows):
                if j in matched_nathers_indices:
                    continue
                nh = nat_w.get("height")
                nw = nat_w.get("width")
                nat_loc = nat_w.get("location", "")
                if h and w and nh and nw and locations_match(loc, nat_loc):
                    if abs(h - nh) <= 50 and abs(w - nw) <= 50:
                        match_idx = j
                        break

        # Match strategy 2: By dimensions (within 50 mm)
        if match_idx == -1:
            for j, nat_w in enumerate(nathers_windows):
                if j in matched_nathers_indices:
                    continue
                nh = nat_w.get("height")
                nw = nat_w.get("width")
                if h and w and nh and nw:
                    if abs(h - nh) <= 50 and abs(w - nw) <= 50:
                        match_idx = j
                        break

        # Match strategy 3: Area-based greedy match (up to 25% diff)
        if match_idx == -1:
            best_idx = -1
            best_diff = None
            try:
                plan_area = (h * w) if h and w else None
            except Exception:
                plan_area = None
            if plan_area:
                for j, nat_w in enumerate(nathers_windows):
                    if j in matched_nathers_indices:
                        continue
                    nh = nat_w.get("height")
                    nw = nat_w.get("width")
                    if not nh or not nw:
                        continue
                    nat_area = nh * nw
                    diff = abs(plan_area - nat_area) / float(nat_area) if nat_area else 1.0
                    if diff <= 0.25:
                        if best_diff is None or diff < best_diff:
                            best_diff = diff
                            best_idx = j
            if best_idx != -1:
                match_idx = best_idx

        row_confidence  = 100.0
        matched_glazing = glazing
        matched_frame   = frame
        matched_u_value = ""
        matched_shgc    = ""
        matched_location = loc  # FIX #1: will be overridden by NatHERS location when matched
        matched_type    = w_type

        if match_idx != -1:
            matched_nathers_indices.add(match_idx)
            nat_w = nathers_windows[match_idx]

            # FIX #1: Use NatHERS room label as authoritative location
            nat_location = nat_w.get("location", "")
            if nat_location:
                matched_location = nat_location

            # Authoritative window type from NatHERS (elevations/certificates are source of truth for operability)
            nat_type = nat_w.get("type")
            if nat_type:
                matched_type = nat_type

            # 1. Dimension check
            nh = nat_w.get("height")
            nw = nat_w.get("width")
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

            # 2. Orientation check
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

            # FIX #7: Only flag type mismatch if the plan value is a real assertion
            # (not a hardcoded default like "fixed" or "window")
            n_type = nat_w.get("type")
            w_type_norm = w_type.lower().replace("_", " ").replace("-", " ").strip() if w_type else ""
            n_type_norm = n_type.lower().replace("_", " ").replace("-", " ").strip() if n_type else ""
            if (w_type_norm and n_type_norm
                    and w_type_norm != n_type_norm
                    and w_type_norm not in n_type_norm
                    and n_type_norm not in w_type_norm
                    and _plan_value_is_asserted(w_type, PLAN_DEFAULT_TYPE_STRINGS)):
                flags.append({
                    "flag_type": "opening_type_mismatch",
                    "item_ref": tag,
                    "category": _flag_category_label("opening_type_mismatch"),
                    "opening_id": tag,
                    "description": f"Type mismatch for {tag} ({matched_location}): Plans '{w_type}' vs NatHERS '{n_type}'.",
                    "severity": "Medium"
                })
                row_confidence -= 15.0

            # FIX #7: Only flag glazing mismatch if plan value is a real assertion
            n_glazing = nat_w.get("glazing")
            if (glazing and n_glazing
                    and glazing.lower() not in n_glazing.lower()
                    and n_glazing.lower() not in glazing.lower()
                    and _plan_value_is_asserted(glazing, PLAN_DEFAULT_GLAZING_STRINGS)):
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
            if (frame and n_frame 
                    and frame.lower() not in n_frame.lower() 
                    and n_frame.lower() not in frame.lower()
                    and _plan_value_is_asserted(frame, PLAN_DEFAULT_FRAME_STRINGS)):
                flags.append({
                    "flag_type": "frame_mismatch",
                    "item_ref": tag,
                    "category": _flag_category_label("frame_mismatch"),
                    "opening_id": tag,
                    "description": f"Frame mismatch for {tag} ({matched_location}): Plans '{frame}' vs NatHERS '{n_frame}'.",
                    "severity": "Medium"
                })
                row_confidence -= 10.0

            # FIX #2: Use NatHERS per-row glazing, U-value, SHGC (not plan defaults)
            matched_glazing = nat_w.get("glazing", glazing)
            matched_frame   = n_frame or frame
            matched_u_value = nat_w.get("u_value", "")
            matched_shgc    = nat_w.get("shgc", "")

            src_ref = f"{src_ref} / {nat_w.get('src_ref', 'NatHERS')}"
        else:
            # No NatHERS match found
            flags.append({
                "flag_type": "missing_in_nathers",
                "item_ref": tag,
                "category": _flag_category_label("missing_in_nathers"),
                "opening_id": tag,
                "description": f"{tag} found on plans ({matched_location}) but not in NatHERS schedule. Verify manually.",
                "severity": "Medium"
            })
            row_confidence -= 30.0

        # Standardize opening type label using matched authoritative type
        opening_type = "Window"
        type_lower = matched_type.lower() if matched_type else ""
        if "door" in type_lower or "bifold" in type_lower or "stacker" in type_lower:
            opening_type = "Door"
            if "bifold" in type_lower or "stacker" in type_lower:
                opening_type = "Bi-fold/Stacker Door"
        elif "louvre" in type_lower:
            opening_type = "Louvre"

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

        # U/SHGC display
        u_shgc_display = ""
        if matched_u_value and matched_u_value != "N/A":
            u_shgc_display = f"U: {matched_u_value}"
        if matched_shgc and matched_shgc != "N/A":
            u_shgc_display += (" / " if u_shgc_display else "") + f"SHGC: {matched_shgc}"
        if not u_shgc_display:
            u_shgc_display = "N/A"

        takeoff_rows.append({
            "location":     matched_location,   # FIX #1: NatHERS authoritative location
            "tag":          tag,
            "height":       h,
            "width":        w,
            "type":         matched_type,
            "opening_type": opening_type,
            "orientation":  orientation or "TBD",
            "glazing":      matched_glazing or "Per NatHERS Schedule",
            "u_value":      matched_u_value or "N/A",
            "shgc":         matched_shgc or "N/A",
            "u_shgc":       u_shgc_display,
            "frame":        matched_frame or "Aluminium",
            "quantity":     qty,
            "confidence":   row_confidence,
            "src_ref":      src_ref
        })

    # Add NatHERS-only items as takeoff rows (cert-verified, no plan cross-check)
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
            nat_frame = nat_w.get("frame_material") or nat_w.get("frame") or "Aluminium"
            nat_src = nat_w.get("src_ref", "NatHERS")

            # Determine opening type
            opening_type = "Window"
            type_lower = nat_type.lower() if nat_type else ""
            if "door" in type_lower or "bifold" in type_lower or "stacker" in type_lower:
                opening_type = "Door"
                if "bifold" in type_lower or "stacker" in type_lower:
                    opening_type = "Bi-fold/Stacker Door"
            elif "louvre" in type_lower:
                opening_type = "Louvre"

            # NatHERS-only rows start at 70% (certificate-verified, but unconfirmed on plans)
            nat_confidence = 70.0

            u_shgc_display = ""
            if nat_u and nat_u != "N/A":
                u_shgc_display = f"U: {nat_u}"
            if nat_shgc and nat_shgc != "N/A":
                u_shgc_display += (" / " if u_shgc_display else "") + f"SHGC: {nat_shgc}"
            if not u_shgc_display:
                u_shgc_display = "N/A"

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

    # FIX #6: BASIX aggregate cross-check — treat BASIX/NatHERS total as the anchor.
    # The calculated plan area is the suspect when there is a mismatch, not the certificate.
    try:
        total_plan_area = sum(
            calculate_window_area(r["height"], r["width"], r["quantity"])
            for r in takeoff_rows
            if r.get("height") and r.get("width")
        )
    except Exception:
        total_plan_area = 0.0

    basix_area = basix_data.get("total_glazing_area")

    if basix_area and total_plan_area > 0:
        discrepancy_pct = abs(total_plan_area - basix_area) / float(basix_area) * 100.0
        if discrepancy_pct > 10.0:
            # FIX #6: Flag wording now correctly identifies the plan total as the suspect
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

    # Overall confidence calculation with calibration penalty for missing/unmatched items
    unmatched_count = len([f for f in flags if f["flag_type"] in ("missing_in_plans", "missing_in_nathers")])
    if takeoff_rows:
        base_confidence = sum(r["confidence"] for r in takeoff_rows) / len(takeoff_rows)
        # Apply a penalty of 5.0% per unmatched/missing opening to calibrate to actual coverage
        overall_confidence = max(0.0, base_confidence - (unmatched_count * 5.0))
    else:
        overall_confidence = 0.0

    # Pass/fail logic: only Reject if confidence is critically low
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

    # Review Required: set to True if there are critical mismatches (High or Medium severity flags)
    critical_flags = [f for f in flags if f.get("severity") in ("High", "Medium")]
    if critical_flags:
        review_required = True
        review_reason = f"Job has {len(critical_flags)} critical consistency flags (High/Medium severity) requiring manual review."
    else:
        review_required = False
        review_reason = ""

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
