# FenX PDF Takeoff — Resolved Edge Cases & Issues

**Project:** FenX Window & Door Takeoff POC  
**Period:** July 2026  
**Prepared By:** FenX Development Team  
**Status:** All issues resolved, tested, and verified ✅

> This document lists every known edge case that was identified during client testing rounds and explains what was fixed. If any item is missing or needs further clarification, please flag it and we will address it in the next cycle.

---

## Section 1 — Critical Issues (Business Impact)

---

### EC-01 | Multi-Building / Job Separation
**Status:** ✅ Resolved  
**Severity:** 🔴 Critical

**Problem:**  
When files from more than one building were uploaded together (e.g. plans for Project A with NatHERS certificate for Project B), the tool merged them into a single takeoff without any warning. Confidence score actually *increased* as more mismatched files were added, because openings matched within each building's own document set.

**Example:**  
- Uploading Grafton Street plans + Zillie Close NatHERS certificate → merged into one takeoff with 82.6% confidence and no warning.

**Fix Applied:**  
- Each uploaded file's address is now extracted from PDF text content **and** the filename.
- The system performs a **double-layered address match** (fuzzy token matching + substring backstop) against the NatHERS certificate address.
- If any mismatch is detected, the job is immediately **Rejected** with a clear `"Document Mismatch"` message before any extraction begins.
- Multiple NatHERS certificates in a single upload are also immediately rejected with `"Multiple jobs detected"`.

**Test Result:**  
Uploading Grafton Street plans + Zillie Close NatHERS → System output:  
`Rejected: Document Mismatch — plans file does not match NatHERS address (Tokens: ['grafton'] vs ['zillie', '1808'])`

---

### EC-02 | Confidence Score Was Misleading
**Status:** ✅ Resolved  
**Severity:** 🔴 Critical

**Problem:**  
Confidence score was measuring "matchability" instead of "correctness". Adding more mismatched files caused the score to *increase* rather than decrease, giving a false sense of accuracy.

**Example:**  
- 57% → 56.5% → 67.7% → 82.6% as more unrelated files were added, despite correctness decreasing.

**Fix Applied:**  
- Confidence is now penalised based on:
  - Unmatched openings (Missing in Plans, Missing in NatHERS)
  - TBD fields (location, orientation, frame)
  - Dimension mismatches (scaled by magnitude)
  - Missing certificate / plans
- Maximum penalty capped at 20% per unmatched opening to prevent false rejections.

---

### EC-03 | Duplicate File Doubles Openings
**Status:** ✅ Resolved  
**Severity:** 🔴 Critical

**Problem:**  
Uploading the same file twice caused all openings to be counted double in the takeoff, with no warning to the user.

**Fix Applied:**  
- MD5 content-hash deduplication implemented at upload stage.
- If an identical file is uploaded again, it is silently skipped and a `"Duplicate File Skipped"` note is added to the consistency report.

---

### EC-04 | Empty Result at 100% When No Plans Provided
**Status:** ✅ Resolved  
**Severity:** 🔴 Critical

**Problem:**  
If no plans were uploaded (only NatHERS certificate), the system would produce an empty takeoff with 100% confidence — no openings, no flags, no warning.

**Fix Applied:**  
- Certificate-absent guard implemented: if no NatHERS certificate is found in the upload, the job is immediately `Rejected` with message: `"No NatHERS certificate provided — cannot produce a schedule."`
- If plans are absent but certificate present, the system now outputs NatHERS-only data with a single informational note: `"No floor plans provided — takeoff based on certificate only."`

---

## Section 2 — Extraction & Document Classification Issues

---

### EC-05 | Garage Doors Included in Takeoff
**Status:** ✅ Resolved  
**Severity:** 🟡 Medium

**Problem:**  
Garage sectional lift doors, panel lift doors, and roller doors were being extracted and included in the window/door takeoff schedule, which is out of scope.

**Fix Applied:**  
- `is_opaque_door` filter updated to drop only garage-type doors.
- Regular solid external doors (entry, laundry, verandah) are retained.

---

### EC-06 | Internal Passage Doors Extracted
**Status:** ✅ Resolved  
**Severity:** 🟡 Medium

**Problem:**  
Internal bedroom, bathroom, linen, and wardrobe doors (typically labelled `820d`) were being included in the takeoff — they should only appear if on an external wall.

**Fix Applied:**  
- LLM prompt now explicitly instructs extraction of `820d` only when located at an external wall (entry, laundry exit, porch/verandah).
- Post-extraction filter added: any `820d` or `720d` door with `location=TBD` and `type=hinged` is excluded with a log entry: `[Plans] Excluded internal hinged door`.

---

### EC-07 | External Entry / Laundry Doors Missing
**Status:** ✅ Resolved  
**Severity:** 🟡 Medium

**Problem:**  
Entry doors and laundry exit doors were being excluded from the takeoff, even though they are valid external openings that require NatHERS energy compliance data.

**Fix Applied:**  
- External hinged doors are now explicitly included in extraction scope.
- Solid (non-glazed) external doors get `glazing = null`, `u_value = "N/A"`, `shgc = "N/A"` — correct for solid doors.
- Solid doors are excluded from glazed area calculations.

---

### EC-08 | Skylight / Roof Window Not Detected
**Status:** ✅ Resolved  
**Severity:** 🟡 Medium

**Problem:**  
Skylights and roof windows were not being extracted from NatHERS certificates. The system only looked for the standard `"window schedule"` pages and ignored `"roof window schedule"` and `"skylight schedule"` pages entirely.

**Fix Applied:**  
- NatHERS parser updated to detect and process `"roof window schedule"` and `"skylight schedule"` pages.
- Skylights are classified as opening type `"Skylight"` (separate from `"Window"`).
- Skylights are included in `is_glazed_opening` checks so they carry full glazing performance data.

---

### EC-09 | Skylight U-value / SHGC Returns "N/A"
**Status:** ✅ Resolved  
**Severity:** 🟡 Medium

**Problem:**  
Even when skylights were detected, their U-value and SHGC showed as `"N/A"` because product codes like `GEN-04-003a` or `GEN-04-005a` failed to match the specification catalog (which stored them as `GEN-04-003` and `GEN-04-005`).

**Fix Applied:**  
- Implemented **3-stage fuzzy specification matching**:
  1. Exact match (direct key lookup)
  2. Alphanumeric normalisation match (strips hyphens, spaces, case)
  3. Letter-suffix fallback (strips trailing letter e.g. `a` from `GEN-04-003a` → matches `GEN-04-003`)

---

### EC-10 | Wrong Floor Plan Pages Selected for Extraction
**Status:** ✅ Resolved  
**Severity:** 🟡 Medium

**Problem:**  
The page selection algorithm was incorrectly excluding valid floor plan sheets. For example, Grafton Street's first floor plan was excluded because a construction note on the page contained the word `"elevations"` — which was in the unconditional exclusion list.

**Fix Applied:**  
- Removed `"elevations"` from the unconditional exclusion phrase list.
- Construction notes referencing elevations are common on floor plan sheets and should not exclude the page.
- Tiered page selection logic now correctly identifies floor plan pages through title matching, room keyword detection, and fallback heuristics.

---

### EC-11 | Room Attribution Wrong (All Windows → Same Room)
**Status:** ✅ Resolved  
**Severity:** 🟡 Medium

**Problem:**  
All extracted windows from the NatHERS schedule were being assigned to the same room (the last room parsed), rather than their correct individual rooms.

**Fix Applied:**  
- Per-row room attribution logic implemented in NatHERS parser.
- Each window now carries the room label that appeared immediately before it in the NatHERS window schedule.

---

## Section 3 — Reconciliation & Matching Issues

---

### EC-12 | Tag-Only Matching Too Strict
**Status:** ✅ Resolved  
**Severity:** 🟡 Medium

**Problem:**  
Matching was purely based on window tag strings. If the NatHERS certificate used tag `1118` and the plans used `1118` with a 5mm dimension difference, it would fail to match and generate a false "missing" flag.

**Fix Applied:**  
- Replaced tag-only matching with a **multi-attribute scoring system**:
  - Tags (exact and partial)
  - Dimensions (within 50mm tolerance)
  - Location (room name)
  - Opening type
  - Orientation
- An opening only needs to score above a threshold to be matched, even if tags differ slightly.

---

### EC-13 | Dimension Mismatch — All Same Severity
**Status:** ✅ Resolved  
**Severity:** 🟡 Medium

**Problem:**  
A 10mm dimension difference and a 500mm dimension difference were both flagged at the same severity level, making the report hard to prioritise.

**Fix Applied:**  
- Dimension mismatch severity now scaled by magnitude:
  - Difference ≤ 50mm → Low severity (likely rounding)
  - Difference 50–200mm → Medium severity
  - Difference > 200mm → High severity

---

### EC-14 | Frame Material Taken from Wall Framing
**Status:** ✅ Resolved  
**Severity:** 🟡 Medium

**Problem:**  
The system was reading the wall construction framing material (e.g. `"FRAME TYPE: Timber"` from construction notes) and assigning it as the window frame material.

**Fix Applied:**  
- LLM prompt explicitly instructs: "DO NOT extract wall framing material as window frame material."
- Frame material is only extracted if explicitly mentioned in the window/door description or specification.

---

### EC-15 | Obscure Glazing Flagged as Mismatch
**Status:** ✅ Resolved  
**Severity:** 🟢 Low

**Problem:**  
If the NatHERS certificate listed a window as `"obscure"` glazing (used for privacy, e.g. bathroom windows), the reconciler raised a mismatch flag — even though this is a perfectly valid and expected glazing type.

**Fix Applied:**  
- Obscure glazing is now handled as a Low-severity informational note: `"Obscure glazing noted — verify privacy glazing is as specified."`
- No longer raises a mismatch flag.

---

### EC-16 | Glazed Area Calculation Includes Solid Doors
**Status:** ✅ Resolved  
**Severity:** 🟡 Medium

**Problem:**  
When calculating total glazed area for BASIX compliance comparison, solid external doors (entry, laundry) were being included in the glazed area sum — inflating the total incorrectly.

**Fix Applied:**  
- Solid doors (`is_glazed = False`) are now explicitly excluded from glazed area calculations.
- Only actual glazed openings (windows, glazed doors, skylights) count towards the glazed area.

---

## Section 4 — TBD Field & Quality Flag Issues

---

### EC-17 | TBD Orientation Not Reducing Confidence
**Status:** ✅ Resolved  
**Severity:** 🟡 Medium

**Problem:**  
Jobs with external doors where orientation was `TBD` were still showing 97.5% overall confidence with no warning flag — giving a false pass result.

**Fix Applied:**  
- TBD field checks now apply to **all openings** (glazed and solid).
- If any opening has `location = TBD`, `orientation = TBD`, or `frame = null/TBD`:
  - A Medium-severity flag is raised.
  - Row confidence is deducted by 15%.
  - Overall job confidence drops accordingly and status changes to `Review Required`.

---

### EC-18 | Null Frame Material Not Flagged
**Status:** ✅ Resolved  
**Severity:** 🟢 Low

**Problem:**  
Openings where frame material was null or empty produced no warning, even though a frame material is required for compliance schedules.

**Fix Applied:**  
- Null or empty frame material now raises a Low-severity flag: `"Frame material not specified — verify before ordering."`
- Row confidence is reduced by a small penalty.

---

## Section 5 — Document Validation Issues

---

### EC-19 | BASIX Address Mismatch Not Detected
**Status:** ✅ Resolved  
**Severity:** 🔴 Critical

**Problem:**  
If a BASIX certificate for a different property was uploaded alongside the NatHERS certificate, the system processed them together as if they belonged to the same job.

**Fix Applied:**  
- BASIX file's address is extracted and fuzzy-matched against the NatHERS certificate address.
- Mismatch → job immediately `Rejected` with `"Document Mismatch: BASIX certificate does not match NatHERS address."`

---

### EC-20 | Plans Address Mismatch Not Detected
**Status:** ✅ Resolved  
**Severity:** 🔴 Critical

**Problem:**  
If plans for a different project were mixed in with the NatHERS certificate, extraction proceeded silently — producing a meaningless merged takeoff.

**Fix Applied:**  
- Plans file address is extracted and matched against NatHERS certificate address.
- Mismatch → job immediately `Rejected` with `"Document Mismatch: Plans file does not match NatHERS address."`

---

### EC-21 | Scanned PDFs Have No Text → Address Match Fails
**Status:** ✅ Resolved  
**Severity:** 🟡 Medium

**Problem:**  
Some PDFs (especially older scanned drawings) contain no searchable text layer, causing address token extraction to return empty — which would then skip address validation entirely (no backstop).

**Fix Applied:**  
- Address tokens are now extracted from **both** the PDF text content **and** the filename.
- Example: `74_Grafton_Street-251113a.pdf` → extracts `grafton` as a street token even if PDF text is empty.
- Added a substring-level backstop (`address_matches_project`) as a fallback when fuzzy tokens are too sparse.

---

## Section 6 — Output & Reporting Issues

---

### EC-22 | Consistency Report Had Blank Item Ref & Category
**Status:** ✅ Resolved  
**Severity:** 🟢 Low

**Problem:**  
In the Excel Consistency Report tab, the "Item Ref" and "Flag Category" columns were blank for many flags, making it difficult to understand which opening was flagged and why.

**Fix Applied:**  
- Each flag now contains a properly populated `item_ref` (e.g. `"W1"`, `"D2"`, `"1118"`) and `category` (e.g. `"Dimension Mismatch"`, `"TBD Field"`, `"Missing in Plans"`).

---

### EC-23 | Skylight Rows Not Visually Distinguished in Excel
**Status:** ✅ Resolved  
**Severity:** 🟢 Low

**Problem:**  
Skylights appeared as regular window rows in the Excel takeoff sheet with no visual distinction, making them easy to miss during manual QA.

**Fix Applied:**  
- Skylight rows now display with a **soft pastel yellow background** in the Excel takeoff sheet.
- Opening type column shows `"Skylight"` (not `"Window"`).

---

### EC-24 | Rejected Jobs Produce No Excel Output
**Status:** ✅ Resolved  
**Severity:** 🟢 Low

**Problem:**  
When a job was rejected (e.g. low confidence, mismatch), no Excel file was produced. Users had no downloadable record of why the job failed.

**Fix Applied:**  
- Rejected jobs now always generate an Excel file.
- The Consistency Report tab shows all flags and the rejection reason clearly.
- Users can still download the report for their records.

---

## Summary Table

| ID | Issue | Severity | Status |
|---|---|---|---|
| EC-01 | Multi-building job separation | 🔴 Critical | ✅ Fixed |
| EC-02 | Confidence score misleading | 🔴 Critical | ✅ Fixed |
| EC-03 | Duplicate file doubles openings | 🔴 Critical | ✅ Fixed |
| EC-04 | Empty result at 100% confidence | 🔴 Critical | ✅ Fixed |
| EC-05 | Garage doors included in takeoff | 🟡 Medium | ✅ Fixed |
| EC-06 | Internal passage doors extracted | 🟡 Medium | ✅ Fixed |
| EC-07 | External entry/laundry doors missing | 🟡 Medium | ✅ Fixed |
| EC-08 | Skylight/roof window not detected | 🟡 Medium | ✅ Fixed |
| EC-09 | Skylight U-value/SHGC = N/A | 🟡 Medium | ✅ Fixed |
| EC-10 | Wrong floor plan pages selected | 🟡 Medium | ✅ Fixed |
| EC-11 | Room attribution wrong | 🟡 Medium | ✅ Fixed |
| EC-12 | Tag-only matching too strict | 🟡 Medium | ✅ Fixed |
| EC-13 | All dimension mismatches same severity | 🟡 Medium | ✅ Fixed |
| EC-14 | Frame material from wall framing | 🟡 Medium | ✅ Fixed |
| EC-15 | Obscure glazing flagged as mismatch | 🟢 Low | ✅ Fixed |
| EC-16 | Glazed area includes solid doors | 🟡 Medium | ✅ Fixed |
| EC-17 | TBD orientation not reducing confidence | 🟡 Medium | ✅ Fixed |
| EC-18 | Null frame not flagged | 🟢 Low | ✅ Fixed |
| EC-19 | BASIX address mismatch not detected | 🔴 Critical | ✅ Fixed |
| EC-20 | Plans address mismatch not detected | 🔴 Critical | ✅ Fixed |
| EC-21 | Scanned PDF → no text → address match fails | 🟡 Medium | ✅ Fixed |
| EC-22 | Blank item ref & category in report | 🟢 Low | ✅ Fixed |
| EC-23 | Skylights not distinguished in Excel | 🟢 Low | ✅ Fixed |
| EC-24 | Rejected jobs produce no Excel output | 🟢 Low | ✅ Fixed |

---

**Total Issues Resolved: 24**  
🔴 Critical: 6 | 🟡 Medium: 13 | 🟢 Low: 5

---

*If any edge case is missing or requires further clarification, please flag it and the team will address it in the next iteration.*
