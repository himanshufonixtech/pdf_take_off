import fitz
import os
import json
import base64
import urllib.request
import urllib.error
import asyncio
import aiohttp
import config

# ---------------------------------------------------------------------------
# OpenAI helpers (unchanged from original)
# ---------------------------------------------------------------------------

def call_openai_chat(model: str, messages: list, response_format: str = "json_object") -> str:
    """Direct HTTP request helper to call the OpenAI Chat API."""
    url = f"{config.get_openai_api_base_url().rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.get_openai_api_key()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1
    }
    if response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            res_data = json.loads(res.read().decode('utf-8'))
            return res_data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as he:
        error_body = he.read().decode('utf-8')
        raise RuntimeError(f"OpenAI API error {he.code}: {error_body}")
    except Exception as e:
        raise RuntimeError(f"OpenAI connection error: {e}")


async def _async_post_openai(session: aiohttp.ClientSession, payload: dict) -> dict:
    url = f"{config.get_openai_api_base_url().rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.get_openai_api_key()}",
        "Content-Type": "application/json"
    }
    async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)) as resp:
        resp.raise_for_status()
        return await resp.json()


def call_openai_chat_concurrent(requests_payloads: list) -> list:
    """Send multiple OpenAI chat requests concurrently."""
    async def _runner(payloads):
        async with aiohttp.ClientSession() as session:
            tasks = [_async_post_openai(session, p) for p in payloads]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return results

    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(asyncio.run, _runner(requests_payloads))
            return future.result(timeout=120)
    else:
        return asyncio.run(_runner(requests_payloads))


# ---------------------------------------------------------------------------
# FIX #4 & #5: Opaque / non-glazing door exclusion keywords
# Garage doors (BRD Section 4.2: explicitly OUT OF SCOPE)
# ---------------------------------------------------------------------------
OPAQUE_DOOR_KEYWORDS = [
    "garage", "sectional", "panel lift", "roller door", "roller",
    "solid core", "solid timber", "solid door", "opaque door",
    "csi classic", "panel door", "hinged solid"
]

def _is_opaque_door(tag: str, w_type: str, location: str) -> bool:
    """Returns True if this opening is an opaque/garage door that should be excluded."""
    combined = f"{tag} {w_type} {location}".lower()
    return any(kw in combined for kw in OPAQUE_DOOR_KEYWORDS)


# ---------------------------------------------------------------------------
# NatHERS Extraction — FIX #1 (room attribution), #2 (per-row U/SHGC), #4 (glazed doors)
# ---------------------------------------------------------------------------

def extract_nathers_data(file_path: str) -> list:
    """
    Locates the window schedule pages in a NatHERS certificate
    and extracts window/door list with per-row room labels and glazing products.
    """
    doc = fitz.open(file_path)
    page_numbers_set = set()
    schedule_text = ""
    try:
        last_matched_is_schedule = False
        for i, page in enumerate(doc):
            text = page.get_text()
            text_lower = text.lower()
            
            is_schedule_start = False
            is_performance = False
            is_continuation = False
            
            # 1. Match window schedule pages
            if "window and glazed door schedule" in text_lower or "window schedule" in text_lower:
                # Skip checklist pages or general explanatory/glossary pages
                if "checklist" not in text_lower and "genuine certificate check" not in text_lower and "explanatory notes" not in text_lower:
                    # Skip pages that only have roof window schedule without main window schedule
                    if not ("roof window schedule" in text_lower and "window and glazed door schedule" not in text_lower):
                        is_schedule_start = True
                
            # 2. Match window performance description pages (often split/overflowing onto preceding page)
            if "window and glazed door type and performance" in text_lower or "glazing type and performance" in text_lower or "window description" in text_lower:
                if "checklist" not in text_lower and "genuine certificate check" not in text_lower and "explanatory notes" not in text_lower:
                    is_performance = True

            # 3. Match continuation pages
            if not is_schedule_start and not is_performance and last_matched_is_schedule:
                has_headers = any(kw in text_lower for kw in ["window no.", "height [mm]", "width [mm]", "opening %", "orientation", "window id"])
                if has_headers and "checklist" not in text_lower and "genuine certificate check" not in text_lower and "explanatory notes" not in text_lower:
                    is_continuation = True
                    
            # Check if schedule has ended on this page
            has_ended = any(kw in text_lower for kw in [
                "external wall type", "external wall schedule", "floor type", "floor schedule", 
                "ceiling type", "ceiling penetrations", "roof type", "solar diagrams", "explanatory notes"
            ])
            
            if is_schedule_start or is_performance or is_continuation:
                page_numbers_set.add(i + 1)
                last_matched_is_schedule = (is_schedule_start or is_continuation)
            else:
                last_matched_is_schedule = False
                
            if has_ended:
                last_matched_is_schedule = False

        page_numbers = sorted(list(page_numbers_set))
        for p in page_numbers:
            page_text = doc[p - 1].get_text()
            schedule_text += f"\n--- PAGE {p} ---\n" + page_text

        if not schedule_text:
            return []

        # FIX #1: Prompt now explicitly asks for room/location and separates catalog from instances
        # FIX #2: Glazing lookup resolved in Python by extracting the specifications catalog and doing a dictionary join
        # FIX #4: Include glazed doors (sliding, bifold, etc.) and exclude opaque doors
        prompt = """You are an expert construction estimating AI. Extract both the window specification catalog and the window schedule from the NatHERS certificate text.

Return a JSON object with exactly two keys: "glazing_types" and "windows". Return ONLY valid JSON.

1. "glazing_types": Extract all window type specifications from the 'Window and glazed door type and performance' table (usually labeled Custom* windows or Default* windows).
Each object in the "glazing_types" list must have:
- glazing_id: the window/glazing ID string (e.g. "SSW-025-305", "SSW-025-304", "A&L-012-306")
- description: the full window description text (e.g. "150 Series Thermal Star Awning...")
- u_value: the maximum U-value (float, e.g. 5.7)
- shgc: the SHGC (float, e.g. 0.67)

2. "windows": Extract all window and glazed door instances from the 'Window and glazed door schedule' table.
Include BOTH windows and glazed doors (sliding doors, stacker doors, bifold doors, etc.).
Do NOT include opaque/solid doors or garage doors.
Each object in the "windows" list must have:
- location: room/location name EXACTLY as in the schedule table (e.g. "BED 1", "LOUNGE", "STUDY")
- tag: window number/code (e.g. "W1", "W2", "D1", "D2", "1806", "1118", "Opening 12"). This is the label uniquely identifying the opening instance (from the 'Window no.' or 'Window number' column). Do NOT set this to the glazing/product ID like 'ALM-001-01 A' or 'ALM-002-01 A'.
- height: height in mm (integer)
- width: width in mm (integer)
- type: window type (e.g. "awning", "sliding", "sliding door")
- orientation: compass orientation (e.g. "SSE", "NNW", "ENE")
- glazing: the Window ID / Glazing code matching the glazing_id in the specification catalog (e.g. "ALM-001-01 A", "ALM-002-01 A", "SSW-025-304").
- quantity: quantity (integer)

CRITICAL: If a page does not contain the respective table, return an empty list for that key. Do not hallucinate or invent dummy entries.
"""

        per_page_texts = []
        for p in page_numbers:
            page_text = doc[p - 1].get_text()
            per_page_texts.append((p, f"--- PAGE {p} ---\n" + page_text))

        payloads = []
        for pnum, ptext in per_page_texts:
            messages = [
                {"role": "system", "content": "You are a helpful construction takeoff assistant. Always output valid JSON only."},
                {"role": "user", "content": f"{prompt}\n\nNatHERS page {pnum} text content:\n{ptext}"}
            ]
            payload = {
                "model": config.get_openai_model(),
                "messages": messages,
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }
            payloads.append(payload)

        try:
            results = call_openai_chat_concurrent(payloads)
            if results and all(isinstance(r, Exception) for r in results):
                raise results[0]
            all_windows = []
            all_glazing = {}
            pages_str = ", ".join(f"p.{p}" for p in page_numbers)
            
            for res in results:
                if isinstance(res, Exception):
                    continue
                try:
                    content = res["choices"][0]["message"]["content"]
                    data = json.loads(content)
                    
                    # Store glazing specs
                    for g in data.get("glazing_types", []):
                        g_id = g.get("glazing_id")
                        if g_id:
                            all_glazing[g_id.strip().upper()] = {
                                "u_value": g.get("u_value"),
                                "shgc": g.get("shgc"),
                                "glazing": g.get("description", g_id)
                            }
                            
                    # Gather window rows
                    all_windows.extend(data.get("windows", []))
                except Exception:
                    continue
            
            # Map specifications to window instances
            reconciled_windows = []
            for w in all_windows:
                if not w.get("src_ref"):
                    w["src_ref"] = f"NatHERS {pages_str}"
                
                # Exclude opaque/garage doors
                if _is_opaque_door(
                    str(w.get("tag", "")),
                    str(w.get("type", "")),
                    str(w.get("location", ""))
                ):
                    continue
                    
                glazing_id = str(w.get("glazing", "")).strip().upper()
                if glazing_id in all_glazing:
                    w["u_value"] = all_glazing[glazing_id]["u_value"]
                    w["shgc"] = all_glazing[glazing_id]["shgc"]
                    w["glazing"] = all_glazing[glazing_id]["glazing"]
                    w["frame_material"] = "Aluminium" if "aluminium" in all_glazing[glazing_id]["glazing"].lower() else "Timber"
                else:
                    found = False
                    for key, spec in all_glazing.items():
                        if key in glazing_id or glazing_id in key:
                            w["u_value"] = spec["u_value"]
                            w["shgc"] = spec["shgc"]
                            w["glazing"] = spec["glazing"]
                            w["frame_material"] = "Aluminium" if "aluminium" in spec["glazing"].lower() else "Timber"
                            found = True
                            break
                    if not found:
                        w["u_value"] = w.get("u_value", "N/A")
                        w["shgc"] = w.get("shgc", "N/A")
                        w["glazing"] = w.get("glazing", "Per NatHERS Schedule")
                        w["frame_material"] = w.get("frame_material", "Aluminium")
                
                reconciled_windows.append(w)
            return reconciled_windows
            
        except Exception:
            # Fallback single request
            messages = [
                {"role": "system", "content": "You are a helpful construction takeoff assistant. Always output valid JSON only."},
                {"role": "user", "content": f"{prompt}\n\nNatHERS text content:\n{schedule_text}"}
            ]
            response_str = call_openai_chat(config.get_openai_model(), messages, "json_object")
            data = json.loads(response_str)
            pages_str = ", ".join(f"p.{p}" for p in page_numbers)
            
            all_glazing = {}
            for g in data.get("glazing_types", []):
                g_id = g.get("glazing_id")
                if g_id:
                    all_glazing[g_id.strip().upper()] = {
                        "u_value": g.get("u_value"),
                        "shgc": g.get("shgc"),
                        "glazing": g.get("description", g_id)
                    }
                    
            windows = data.get("windows", [])
            result = []
            for w in windows:
                if not w.get("src_ref"):
                    w["src_ref"] = f"NatHERS {pages_str}"
                if _is_opaque_door(
                    str(w.get("tag", "")),
                    str(w.get("type", "")),
                    str(w.get("location", ""))
                ):
                    continue
                    
                glazing_id = str(w.get("glazing", "")).strip().upper()
                if glazing_id in all_glazing:
                    w["u_value"] = all_glazing[glazing_id]["u_value"]
                    w["shgc"] = all_glazing[glazing_id]["shgc"]
                    w["glazing"] = all_glazing[glazing_id]["glazing"]
                    w["frame_material"] = "Aluminium" if "aluminium" in all_glazing[glazing_id]["glazing"].lower() else "Timber"
                else:
                    found = False
                    for key, spec in all_glazing.items():
                        if key in glazing_id or glazing_id in key:
                            w["u_value"] = spec["u_value"]
                            w["shgc"] = spec["shgc"]
                            w["glazing"] = spec["glazing"]
                            w["frame_material"] = "Aluminium" if "aluminium" in spec["glazing"].lower() else "Timber"
                            found = True
                            break
                    if not found:
                        w["u_value"] = w.get("u_value", "N/A")
                        w["shgc"] = w.get("shgc", "N/A")
                        w["glazing"] = w.get("glazing", "Per NatHERS Schedule")
                        w["frame_material"] = w.get("frame_material", "Aluminium")
                result.append(w)
            return result
    finally:
        try:
            doc.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# BASIX Extraction (unchanged logic, minor cleanup)
# ---------------------------------------------------------------------------

def extract_basix_data(file_path: str) -> dict:
    """Extracts glazing commitment aggregates and certificate details from BASIX."""
    doc = fitz.open(file_path)
    basix_text = ""
    page_numbers = []
    per_page_texts = []

    for i, page in enumerate(doc):
        text = page.get_text()
        if any(x in text.lower() for x in ["glazing", "commitment", "certificate number"]):
            basix_text += f"\n--- PAGE {i+1} ---\n" + text
            page_numbers.append(i + 1)
            per_page_texts.append((i + 1, text))

    doc.close()

    if not basix_text:
        return {"commitments": [], "cert_number": None}

    prompt = """Extract glazing commitments, certificate numbers, and general properties from the BASIX certificate text below.
Return a JSON object with:
- cert_number: BASIX certificate number (string, e.g. "1825211S")
- project_name: site or project address / client details if mentioned
- nathers_reference: the NatHERS certificate number or reference mentioned (string or null)
- water_score: the Water score (e.g. "40" or "Pass")
- energy_score: the Energy score (e.g. "50")
- thermal_pass: boolean or string indicating if Thermal Comfort passed
- total_glazing_area: total glazing area in sqm if specified (float or null)
- frame_totals: a summary of frames used if specified
- commitments: a list of glazing/window constraints (array of strings)

Return ONLY valid JSON."""

    if len(per_page_texts) == 1:
        pnum, ptext = per_page_texts[0]
        messages = [
            {"role": "system", "content": "You are a helpful construction takeoff assistant. Always output valid JSON only."},
            {"role": "user", "content": f"{prompt}\n\nBASIX page {pnum} text content:\n{ptext}"}
        ]
        try:
            response_str = call_openai_chat(config.get_openai_model(), messages, "json_object")
            return json.loads(response_str)
        except Exception:
            return {"commitments": [], "cert_number": None}

    payloads = []
    for pnum, ptext in per_page_texts:
        msgs = [
            {"role": "system", "content": "You are a helpful construction takeoff assistant. Always output valid JSON only."},
            {"role": "user", "content": f"{prompt}\n\nBASIX page {pnum} text content:\n{ptext}"}
        ]
        payloads.append({
            "model": config.get_openai_model(),
            "messages": msgs,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        })

    try:
        results = call_openai_chat_concurrent(payloads)
        if results and all(isinstance(r, Exception) for r in results):
            raise results[0]
        merged_data = {"commitments": [], "cert_number": None, "total_glazing_area": None}
        for res in results:
            if isinstance(res, Exception):
                continue
            try:
                content = res["choices"][0]["message"]["content"]
                data = json.loads(content)
                if data.get("cert_number") and not merged_data["cert_number"]:
                    merged_data["cert_number"] = data["cert_number"]
                if data.get("total_glazing_area") and not merged_data["total_glazing_area"]:
                    merged_data["total_glazing_area"] = data["total_glazing_area"]
                if data.get("commitments"):
                    merged_data["commitments"].extend(data["commitments"])
            except Exception:
                continue
        return merged_data
    except Exception:
        pass

    messages = [
        {"role": "system", "content": "You are a helpful construction takeoff assistant. Always output valid JSON only."},
        {"role": "user", "content": f"{prompt}\n\nBASIX text content:\n{basix_text}"}
    ]
    response_str = call_openai_chat(config.get_openai_model(), messages, "json_object")
    return json.loads(response_str)


# ---------------------------------------------------------------------------
# Plans Extraction
# FIX #3: Tighter page filter excludes elevations/sections/details
# FIX #4: Exclude garage/opaque doors from plans extraction
# FIX #3b: Cross-check extracted tags against NatHERS to suppress phantoms
# ---------------------------------------------------------------------------

# Pages to exclude — these contain window symbols but are NOT floor plans
PLAN_PAGE_EXCLUSION_KEYWORDS = [
    "elevation", "section", "detail", "specification", "schedule",
    "site plan", "location plan", "demolition", "services", "electrical",
    "wet area", "hydraulic", "window schedule", "door schedule",
    "window & door schedule", "legend", "notes", "general notes"
]

# Tags that look like generic placeholder/detail callouts — not real floor plan items
PHANTOM_TAG_PATTERNS = [
    "dh1809", "as0912", "sd2115",  # round-number generic callouts
]


def _is_floor_plan_page(text: str) -> bool:
    """Returns True if this page is likely a floor plan (not elevation/section/detail)."""
    text_lower = text.lower()

    # Must have floor plan indicators
    has_floor_plan = "floor plan" in text_lower or any(
        room in text_lower for room in ["bedroom", "bed ", "kitchen", "living", "family", "garage", "laundry", "bathroom", "ensuite"]
    )
    if not has_floor_plan:
        return False

    # Must NOT be an elevation, section, or detail page
    for kw in PLAN_PAGE_EXCLUSION_KEYWORDS:
        if kw in text_lower and "floor plan" not in text_lower:
            return False

    return True


def get_page_drawing_title(page) -> str:
    """Attempts to locate the drawing title near the 'DRAWING TITLE' marker."""
    rects = page.search_for("DRAWING TITLE")
    if not rects:
        return ""
    title_rect = rects[0]
    blocks = page.get_text("blocks")
    best_text = ""
    best_dist = float('inf')
    
    for b in blocks:
        text = b[4].strip()
        if not text:
            continue
        if "drawing title" in text.lower() or "rider boulevard" in text.lower():
            continue
            
        bx0, by0, bx1, by1 = b[0], b[1], b[2], b[3]
        dx = max(0, title_rect.x0 - bx1, bx0 - title_rect.x1)
        dy = max(0, title_rect.y0 - by1, by0 - title_rect.y1)
        dist = dx + dy
        
        if dist < 200 and dist < best_dist:
            if bx0 >= title_rect.x0 - 20 and by0 >= title_rect.y0 - 20:
                best_dist = dist
                best_text = text
                
    return best_text.replace("\n", " ").strip()


def extract_plans_data(file_path: str, nathers_tags: set = None) -> list:
    """
    Locates floor plan pages and extracts window/door tags.
    Excludes elevation/section/detail pages.
    Cross-checks extracted tags against NatHERS to suppress phantom openings.

    Args:
        nathers_tags: set of tag strings from NatHERS (used to filter phantoms).
                      If None, no cross-check is performed.
    """
    doc = fitz.open(file_path)
    floor_plan_indices = []

    for i, page in enumerate(doc):
        text_lower = page.get_text().lower()
        
        # 1. Advanced page drawing title extraction from layout text patterns
        page_title = ""
        lines = [line.strip() for line in text_lower.split("\n") if line.strip()]
        # First try to find "design" title layout pattern (most specific)
        for idx, line in enumerate(lines):
            if line == "design" and idx + 2 < len(lines):
                page_title = lines[idx + 2]
                break
        
        # If not found, try to find "drawing title" or "sheet title" layout patterns
        if not page_title:
            for idx, line in enumerate(lines):
                if ("drawing title" in line or "sheet title" in line) and idx + 1 < len(lines):
                    page_title = lines[idx + 1]
                    break
                
        # Fallback to the coordinate-based title if layout patterns didn't yield anything
        if not page_title:
            coord_title = get_page_drawing_title(page)
            if coord_title:
                page_title = coord_title.lower()
                
        # 2. Exclude details/standard/spec sheets based on parsed page title
        EXCLUDE_TITLE_KWS = [
            "elevation", "section", "detail", "specification", "legend", "note", "cover sheet",
            "slab layout", "slab setout", "slab plan", "bracing plan", "joist layout", "joist plan",
            "floor framing", "roof framing", "drainage plan", "drainage layout", "services plan",
            "concept plan", "site plan", "location plan", "demolition", "electrical plan", "electrical layout",
            "bath/wc/ensuite", "laundry / kitchen", "internal elevation", "landscape plan", "floor details",
            "wet area details", "kitchen details", "laundry details", "standard details", "termite", "joist",
            "stormwater", "sediment", "drawing register", "window schedule", "door schedule", "finishes schedule",
            "general notes"
        ]
        
        is_excluded = False
        if page_title:
            if any(kw in page_title for kw in EXCLUDE_TITLE_KWS):
                is_excluded = True
            if page_title == "standard":
                is_excluded = True
                
        if is_excluded:
            continue
            
        # 3. Inclusion check if title is explicitly a floor plan
        INCLUSION_TITLE_KWS = [
            "floor plan", "ground floor", "first floor", "upper floor", "lower floor",
            "wet area plan", "kitchen plan"
        ]
        if page_title and any(kw in page_title for kw in INCLUSION_TITLE_KWS):
            floor_plan_indices.append(i)
            continue
            
        # 3.5. Unconditional text-based trade sheet check
        UNCONDITIONAL_EXCLUSION_PHRASES = [
            "electrical plan", "electrical layout", "slab layout", "slab plan", "slab setout",
            "bracing plan", "joist layout", "floor framing", "roof framing", "drainage plan",
            "drainage layout", "services plan", "concept plan", "joist plan", "site plan",
            "location plan", "demolition plan", "section plan", "elevations"
        ]
        is_trade_sheet = False
        for phrase in UNCONDITIONAL_EXCLUSION_PHRASES:
            if phrase in text_lower:
                is_trade_sheet = True
                break
        if is_trade_sheet:
            continue

        # 4. Fallback when title is unknown or not explicitly inclusion/exclusion: check for rooms
        has_rooms = any(room in text_lower for room in [
            "bedroom", "bed ", "kitchen", "living", "family", "garage",
            "bathroom", "ensuite", "laundry", "alfresco", "porch"
        ])
        if not has_rooms:
            continue
            
        # Fallback text exclusions for pages with rooms but potentially no clear title
        PLAN_PAGE_EXCLUSION_KEYWORDS = [
            "elevation", "section", "detail", "specification", "schedule",
            "site plan", "location plan", "demolition", "services", "electrical",
            "wet area", "hydraulic", "window schedule", "door schedule",
            "window & door schedule", "legend", "notes", "general notes"
        ]
        
        fallback_excluded = False
        for kw in PLAN_PAGE_EXCLUSION_KEYWORDS:
            if kw in text_lower:
                if text_lower.count(kw) > 2 and "floor plan" not in text_lower:
                    fallback_excluded = True
                    break
                    
        if not fallback_excluded:
            floor_plan_indices.append(i)

    # Fallback: if still nothing found, take any page with room words (liberal)
    if not floor_plan_indices:
        for i, page in enumerate(doc):
            text = page.get_text().lower()
            if any(room in text for room in ["bedroom", "kitchen", "living", "family room", "bathroom"]):
                floor_plan_indices.append(i)

    if not floor_plan_indices:
        doc.close()
        return []


    prompt = """Analyze the floor plan text from page {page_num} of the architectural plans.
Identify ALL windows and GLAZED doors (e.g., sliding doors, bifold doors, stacker doors, French doors with glazing, etc.).

AUSTRALIAN WINDOW CODES CONVENTION:
In Australian construction drawings, openings are often labeled with a code representing their dimensions and operability rather than a simple sequential tag (like W1). For example:
- "18-09AAW-DG-LOW E" or "DH1809" or "1809" represents a window of Height = 1800 mm and Width = 900 mm.
- "15-18" or "AS1515" or "1518" represents Height = 1500 mm and Width = 1800 mm.
- "21-18ASD-DG" or "SD2118" represents Height = 2100 mm and Width = 1800 mm.
- "1806", "1118", "1115", "1006", "1105", "1117", "1818", "1124" are 4-digit window size tags. The first two digits represent the height in decimeters (e.g. 18 = 1800mm, 11 = 1100mm, 10 = 1000mm) and the next two represent the width in decimeters (e.g. 06 = 600mm, 18 = 1800mm, 15 = 1500mm, 05 = 500mm, 17 = 1700mm, 24 = 2400mm).
If such code is the main label identifying the window, extract the code itself as the "tag" (e.g. "AS0912", "1806", "1118", "1115", "1006", "15-18AAW") and parse the correct height and width in mm from it. Do NOT skip them as general wall dimensions!

PREFER SIZE CODES OR STANDARD TAGS CONSISTENTLY:
If the drawing layout represents windows using catalog size codes (like DH1809, AS0912, AS1515, SD2124), ALWAYS extract the size code itself as the "tag" of the opening (e.g. "DH1809", "AS1515"). If standard sequential tags (like W1, W2) are also present on the page (for example in a symbol legend or a notes box), DO NOT mix them. Extract the main layout identifier (the size code) for the layout drawings.

CRITICAL EXCLUSIONS:
- DO NOT include garage doors, sectional doors, solid/opaque doors, or roller doors.
- DO NOT include standard internal passage doors, hinged timber/wood doors, bedroom doors, toilet/bathroom doors, linen doors, or wardrobe doors. These are typically solid doors labeled with dimensions like "2040H 820W" or "2040H 720W" and DO NOT have window/glazed door tag numbers.
- DO NOT extract openings from stamp notes, drawing title block labels, legends, or text notes that list general window specifications or refer to other certificates (e.g., "NatHERS Stamped Plans: W1, W2..." or general specifications table). Extract openings ONLY from the actual room labels and floor plan drawings layout.

Extract every window and external glazed door label you see in the text. 
Typically, each opening label consists of:
1. A product or design code prefix (e.g., DS1827, DS1806, DSD2115, DAD2121, DA2112SP).
2. The window/door tag itself (e.g., W1, W2, W3, ..., W11, D1, D2, AS0912, 1806, 18-09AAW).
3. The dimensions (e.g., 1800H x 2650W or 2057H x 1210W).

Return a JSON object with a key "openings" containing a list. Return ONLY valid JSON.

Fields per object:
- tag: the exact window/door tag label or size/type code (e.g. "W1", "W2", "W10", "D1", "D2", "AS0912", "1806", "15-18AAW"). Make sure to use the tag or size code (like AS0912) and NOT the product code (like DS1827) if they are separate.
- height: height in mm as integer (e.g., 1800, 2057). If the tag or label contains the size code (e.g., "1806" or "DH1809" or "15-18"), extract the height from it (1800, 1800, 1500).
- width: width in mm as integer (e.g., 2650, 1210). If the tag or label contains the size code (e.g., "1806" or "DH1809" or "15-18"), extract the width from it (600, 900, 1800).
- type: opening type (e.g. "sliding", "awning", "fixed", "sliding door", "bifold", "stacker door", "louvre", "hinged door")
- quantity: quantity (integer, default 1)
- location: room name if you can guess it from proximity, otherwise make a best estimate or set to "TBD". Do NOT omit the opening if location is unclear.
- frame: frame material if mentioned (e.g. "Aluminium", "Timber")
- glazing: glass type if mentioned
- src_ref: "Plans p.{page_num}"

CRITICAL: Only extract openings that actually have a designated window or glazed door tag or size code (like W1-W11, D1, D2, AS0912, 1806, 15-18) in the plans. Do NOT invent, reuse, or hallucinate tags (like W1, W2) for untagged internal doors or openings. If no standard W/D tags are present, extract the size code label (e.g. "AS0912", "1806") as the tag.
CRITICAL QUANTITY & DUPLICATE INSTANCE RULE: The page text often has multiple instances of the same window tag or size code (e.g., "1806" or "DH1809" appearing multiple times in different parts of the text). You MUST extract EVERY SINGLE INSTANCE as a separate item in the "openings" list. If a tag appears 4 times in the page text, you MUST return 4 separate items in your list, each with quantity=1 and its correct room/location. Do NOT group them or collapse them into a single item."""

    payloads = []
    payload_metadata = []

    for idx in floor_plan_indices:
        page = doc[idx]
        page_text = page.get_text()
        text_lower = page_text.lower()
        has_rooms = any(room in text_lower for room in ["bedroom", "kitchen", "living", "family", "garage", "laundry", "bath", "ensuite"])
        has_text_layer = len(page_text.strip()) > 500 and has_rooms
        page_num = idx + 1

        if has_text_layer:
            messages = [
                {"role": "system", "content": "You are a helpful construction takeoff assistant. Always output valid JSON only."},
                {"role": "user", "content": f"{prompt.format(page_num=page_num)}\n\nFloor Plan Page Text:\n{page_text}"}
            ]
            payload = {
                "model": config.get_openai_model(),
                "messages": messages,
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }
            payloads.append(payload)
            payload_metadata.append({"page_num": page_num, "strategy": "text"})
        else:
            # Vision fallback
            pix = page.get_pixmap(dpi=150)
            temp_img_path = os.path.join(os.path.dirname(file_path), f"temp_floor_plan_{page_num}.jpg")
            pix.save(temp_img_path)

            try:
                with open(temp_img_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            finally:
                try:
                    os.remove(temp_img_path)
                except Exception:
                    pass

            messages = [
                {"role": "system", "content": "You are a helpful construction takeoff assistant. Always output valid JSON only."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt.format(page_num=page_num)},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ]
            payload = {
                "model": config.get_openai_vision_model(),
                "messages": messages,
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }
            payloads.append(payload)
            payload_metadata.append({"page_num": page_num, "strategy": "vision"})

    doc.close()

    if not payloads:
        return []

    windows_data = []
    raw_openings = []
    try:
        results = call_openai_chat_concurrent(payloads)
        if results and all(isinstance(r, Exception) for r in results):
            raise results[0]
        for res, meta in zip(results, payload_metadata):
            if isinstance(res, Exception):
                print(f"Error extracting floor plan data for page {meta['page_num']}: {res}")
                continue
            try:
                content = res["choices"][0]["message"]["content"]
                data = json.loads(content)
                page_openings = data.get("openings", [])
                
                import re
                size_code_pattern = re.compile(r'^(?:[a-zA-Z]{2,4})?\d{4}$|^\d{2}-\d{2}')
                standard_tag_pattern = re.compile(r'^[wdWD]\d{1,2}$')
                
                size_code_count = 0
                for op in page_openings:
                    tag = str(op.get("tag", "")).strip()
                    if size_code_pattern.search(tag):
                        size_code_count += 1
                        
                has_size_codes = size_code_count >= 3
                
                for opening in page_openings:
                    tag = str(opening.get("tag", "")).strip()
                    w_type = str(opening.get("type", "")).lower()
                    location = str(opening.get("location", "")).lower()
                    
                    if has_size_codes and standard_tag_pattern.match(tag):
                        print(f"[Plans] Suppressed standard tag '{tag}' because page has size codes.")
                        continue

                    # FIX #4: Exclude opaque/garage doors from plans too
                    if _is_opaque_door(tag, w_type, location):
                        print(f"[Plans] Excluded opaque/garage door: tag={tag}, type={w_type}, location={location}")
                        continue

                    raw_openings.append(opening)
            except Exception as e:
                print(f"Error parsing response for page {meta['page_num']}: {e}")
                
        # Self-calibrated phantom suppression check
        has_overlap = False
        if nathers_tags and len(nathers_tags) > 0 and raw_openings:
            plan_tags_set = {str(op.get("tag", "")).strip().upper() for op in raw_openings}
            overlap = nathers_tags.intersection(plan_tags_set)
            overlap_ratio = len(overlap) / len(plan_tags_set) if plan_tags_set else 0.0
            # Require at least 2 matching tags AND at least 30% of the plan tags to match
            if len(overlap) >= 2 and overlap_ratio >= 0.30:
                has_overlap = True
                print(f"[Plans] Substantial tag overlap detected with NatHERS: {overlap} (ratio: {overlap_ratio:.2f}). Enabling phantom filtering.")
            else:
                print(f"[Plans] Low or no tag overlap detected: {overlap} (ratio: {overlap_ratio:.2f}). Skipping phantom filtering.")
                
        for opening in raw_openings:
            tag = str(opening.get("tag", "")).strip()
            if nathers_tags and len(nathers_tags) > 0 and has_overlap:
                tag_upper = tag.upper()
                h = opening.get("height")
                w = opening.get("width")
                in_nathers = tag_upper in nathers_tags
                orientation = opening.get("orientation", "")
                has_tbd_orientation = not orientation or orientation.upper() == "TBD"

                # Phantom heuristic: TBD orientation, not in NatHERS
                if not in_nathers and has_tbd_orientation:
                    print(f"[Plans] Suppressed likely phantom: tag={tag}, orientation=TBD, not in NatHERS")
                    continue
                    
            windows_data.append(opening)
    except Exception as e:
        print(f"Error in concurrent floor plan extraction: {e}")
        raise e

    return windows_data
