import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from services.classifier import classify_pdf
from services.reconciler import (
    reconcile_takeoff,
    calculate_match_score,
    classify_opening_type,
    normalize_location,
    locations_match,
)

PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "shred_pdf")
OUTPUTS_DIR = config.OUTPUTS_DIR

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

results = []


def pdf_path(*parts):
    return os.path.join(PDF_DIR, *parts)


def skip_if_no_pdf(path):
    if not os.path.exists(path):
        print("  SKIP - PDF not found: " + path)
        return True
    return False


def skip_if_no_api_key():
    if not config.get_openai_api_key():
        print("  SKIP - OPENAI_API_KEY not set")
        return True
    return False


def run_test(name, fn):
    print("[TEST] " + name)
    try:
        status = fn()
        if status == SKIP:
            print("  -> SKIPPED")
            results.append((name, SKIP, ""))
        else:
            print("  -> PASSED")
            results.append((name, PASS, ""))
    except AssertionError as e:
        print("  -> FAILED: " + str(e))
        results.append((name, FAIL, str(e)))
    except Exception as e:
        import traceback
        print("  -> ERROR: " + str(e))
        traceback.print_exc()
        results.append((name, FAIL, str(e)))


# ============================================================
# UNIT TESTS -- Classifier (no LLM)
# ============================================================

def test_classify_grafton_plans():
    path = pdf_path("74graftson", "74 Grafton Street-251113a (1).pdf")
    if skip_if_no_pdf(path): return SKIP
    r = classify_pdf(path)
    assert r["file_type"] == "Plans", "Expected Plans, got " + r["file_type"]


def test_classify_grafton_nathers():
    path = pdf_path("74graftson", "psetna4j3j (1).pdf")
    if skip_if_no_pdf(path): return SKIP
    r = classify_pdf(path)
    assert r["file_type"] == "NatHERS", "Expected NatHERS, got " + r["file_type"]


def test_classify_ulm_plan_not_basix():
    """Ulm plan has BASIX keyword in drawing notes but is large landscape -- must classify as Plans."""
    path = pdf_path("Ulm", "AI - 18Ulm Plan.pdf")
    if skip_if_no_pdf(path): return SKIP
    r = classify_pdf(path)
    assert r["file_type"] == "Plans", (
        "Ulm plan misclassified as " + r["file_type"] +
        ". Geometry-first logic must classify large landscape sheets as Plans."
    )


def test_classify_ulm_nathers():
    path = pdf_path("Ulm", "AI - 18Ulm NatHERS.pdf")
    if skip_if_no_pdf(path): return SKIP
    r = classify_pdf(path)
    assert r["file_type"] == "NatHERS", "Expected NatHERS, got " + r["file_type"]


def test_classify_mclachlan_plan_not_hybrid():
    """McLachlan plan has both NatHERS and BASIX in notes but large landscape -- must be Plans."""
    path = pdf_path("Mclachalan", "AI - 5 McLachlan Plan.pdf")
    if skip_if_no_pdf(path): return SKIP
    r = classify_pdf(path)
    assert r["file_type"] == "Plans", (
        "McLachlan plan misclassified as " + r["file_type"] + " (expected Plans)."
    )


def test_classify_thrive_basix():
    path = pdf_path("Thrive", "AI - THRIVE BASIX.pdf")
    if skip_if_no_pdf(path): return SKIP
    r = classify_pdf(path)
    assert r["file_type"] == "BASIX", "Expected BASIX, got " + r["file_type"]


def test_classify_lot207_combined():
    path = pdf_path("Lot207", "AI - Lot207 Geraldton BASIX & NatHERS.pdf")
    if skip_if_no_pdf(path): return SKIP
    r = classify_pdf(path)
    assert r["file_type"] in ("Hybrid", "NatHERS", "BASIX"), (
        "Lot207 combined cert classified unexpectedly as " + r["file_type"]
    )


def test_classify_ayre_plan():
    path = pdf_path("Ayre", "AI - AYRE Plan.pdf")
    if skip_if_no_pdf(path): return SKIP
    r = classify_pdf(path)
    assert r["file_type"] == "Plans", "Expected Plans, got " + r["file_type"]


def test_classify_ayre_nathers():
    path = pdf_path("Ayre", "AI - AYRE NatHERS.PDF")
    if skip_if_no_pdf(path): return SKIP
    r = classify_pdf(path)
    assert r["file_type"] == "NatHERS", "Expected NatHERS, got " + r["file_type"]


def test_classify_zillie_nathers():
    path = pdf_path("zillie", "11439 (Lot 1808 Zillie Close Dubbo - NatHERS Cert) 20260113130631648.pdf")
    if skip_if_no_pdf(path): return SKIP
    r = classify_pdf(path)
    assert r["file_type"] == "NatHERS", "Expected NatHERS, got " + r["file_type"]


def test_classify_t001732_basix():
    path = pdf_path("T001732", "T001732 - Basix.pdf")
    if skip_if_no_pdf(path): return SKIP
    r = classify_pdf(path)
    assert r["file_type"] == "BASIX", "Expected BASIX, got " + r["file_type"]


# ============================================================
# UNIT TESTS -- Reconciler logic (no LLM)
# ============================================================

def test_reconcile_plan_primary_dimensions():
    """Plan dimensions must win when plans and NatHERS differ (SOW 3.1, BRD M5.1.001)."""
    plan_w = {"tag": "W1", "height": 1200, "width": 900, "type": "awning", "location": "Bed 1", "quantity": 1}
    nat_w  = {"tag": "W1", "height": 1100, "width": 850, "type": "awning", "location": "BED 1",
              "orientation": "N", "glazing": "SSW-025-304", "u_value": 3.2, "shgc": 0.4, "quantity": 1}
    result = reconcile_takeoff([plan_w], [nat_w], {})
    rows = result["rows"]
    assert len(rows) == 1, "Expected 1 row"
    assert rows[0]["height"] == 1200, "Expected plan height 1200, got " + str(rows[0]["height"])
    assert rows[0]["width"]  == 900,  "Expected plan width 900, got "   + str(rows[0]["width"])
    dim_flags = [f for f in result["flags"] if f["flag_type"] == "dimension_mismatch"]
    assert dim_flags, "Expected dimension_mismatch flag when dims differ"


def test_reconcile_tagless_dimension_matching():
    """BERS Pro style: no matching tags but same room + similar dims should score > 0."""
    plan_w = {"tag": "1806", "height": 1800, "width": 600, "type": "awning", "location": "Kitchen", "quantity": 1}
    nat_w  = {"tag": "Opening 5", "height": 1800, "width": 620, "type": "awning", "location": "KITCHEN",
              "orientation": "N", "glazing": "SG-Generic-01", "u_value": 4.0, "shgc": 0.5, "quantity": 1}
    score = calculate_match_score(plan_w, nat_w)
    assert score > 0, "Expected score > 0 for tagless same-room similar-dims pair, got " + str(score)


def test_reconcile_no_nathers_fallback():
    """has_nathers=False: rows get N/A for u_value/shgc, review_required=True, not rejected."""
    plan_windows = [
        {"tag": "W1", "height": 1800, "width": 900, "type": "awning", "location": "Bed 1",
         "orientation": "N", "quantity": 1, "src_ref": "Plans p.2"},
        {"tag": "W2", "height": 1200, "width": 600, "type": "awning", "location": "Kitchen",
         "orientation": "E", "quantity": 1, "src_ref": "Plans p.2"},
    ]
    result = reconcile_takeoff(plan_windows, [], {}, has_nathers=False)
    rows = result["rows"]
    assert len(rows) == 2, "Expected 2 rows, got " + str(len(rows))
    for row in rows:
        assert row["u_value"] == "N/A", "Expected N/A u_value, got " + str(row["u_value"])
        assert row["shgc"]    == "N/A", "Expected N/A shgc, got "    + str(row["shgc"])
    nf = [f for f in result["flags"] if f["flag_type"] == "no_nathers_fallback"]
    assert nf, "Expected no_nathers_fallback flag in flags"
    assert result["review_required"] is True,  "Expected review_required=True"
    assert result["is_rejected"]     is False, "Plans-only job must NOT be rejected"


def test_reconcile_multi_nathers_merged():
    """Merged NatHERS from two dwellings: all openings should match without missing flags."""
    plan_windows = [
        {"tag": "W1", "height": 1800, "width": 900, "type": "awning", "location": "Bed 1", "quantity": 1},
        {"tag": "W3", "height": 1200, "width": 600, "type": "awning", "location": "Kitchen", "quantity": 1},
    ]
    nat_windows = [
        {"tag": "W1", "height": 1800, "width": 900, "type": "awning", "location": "BED 1",
         "orientation": "N", "glazing": "A", "u_value": 3.2, "shgc": 0.4, "quantity": 1},
        {"tag": "W3", "height": 1200, "width": 600, "type": "awning", "location": "KITCHEN",
         "orientation": "E", "glazing": "B", "u_value": 4.1, "shgc": 0.5, "quantity": 1},
    ]
    result = reconcile_takeoff(plan_windows, nat_windows, {})
    rows = result["rows"]
    assert len(rows) == 2, "Expected 2 matched rows, got " + str(len(rows))
    missing = [f for f in result["flags"] if f["flag_type"] in ("missing_in_plans", "missing_in_nathers")]
    assert not missing, "Unexpected missing flags: " + str(missing)


def test_reconcile_zero_rows_confidence():
    result = reconcile_takeoff([], [], {})
    assert result["overall_confidence"] == 0.0, (
        "Expected 0.0% confidence with no rows, got " + str(result["overall_confidence"])
    )


def test_reconcile_room_name_priority():
    """Plan room name should override NatHERS thermal zone label."""
    plan_w = {"tag": "W5", "height": 1500, "width": 1200, "type": "awning", "location": "Living Room", "quantity": 1}
    nat_w  = {"tag": "W5", "height": 1500, "width": 1200, "type": "awning",
              "location": "Night Time Zone 1", "orientation": "S",
              "glazing": "SG-01", "u_value": 4.0, "shgc": 0.5, "quantity": 1}
    result = reconcile_takeoff([plan_w], [nat_w], {})
    rows = result["rows"]
    assert len(rows) == 1
    assert rows[0]["location"] == "Living Room", (
        "Expected plan room name 'Living Room', got '" + rows[0]["location"] + "'"
    )


def test_classify_opening_type_window():
    assert classify_opening_type("awning",  1200, "W1") == "Window"
    assert classify_opening_type("sliding", 900,  "W5") == "Window"


def test_classify_opening_type_door():
    assert classify_opening_type("sliding door", 2100, "D1")   == "Door"
    assert classify_opening_type("hinged door",  2040, "820d") == "Door"


def test_classify_opening_type_bifold():
    assert classify_opening_type("bifold",       2400, "BD1") == "Bi-fold/Stacker Door"
    assert classify_opening_type("stacker door", 2400, "D3")  == "Bi-fold/Stacker Door"


def test_normalize_location_fn():
    assert normalize_location("BEDROOM 1") == normalize_location("Bed 1")
    assert normalize_location("Family")    == normalize_location("Living")
    assert locations_match("Kitchen", "KIT")


# ============================================================
# INTEGRATION TESTS (require LLM + real PDFs)
# ============================================================

def test_integration_grafton_full_pipeline():
    if skip_if_no_api_key(): return SKIP
    from services.extractor import extract_nathers_data, extract_plans_data
    from services.excel_generator import generate_takeoff_excel

    plans_path   = pdf_path("74graftson", "74 Grafton Street-251113a (1).pdf")
    nathers_path = pdf_path("74graftson", "psetna4j3j (1).pdf")
    if skip_if_no_pdf(plans_path) or skip_if_no_pdf(nathers_path): return SKIP

    nat_windows = extract_nathers_data(nathers_path)
    assert len(nat_windows) > 0, "Expected NatHERS openings, got 0"
    print("  NatHERS openings: " + str(len(nat_windows)))

    nat_tags    = {str(w.get("tag", "")).strip().upper() for w in nat_windows}
    plan_windows = extract_plans_data(plans_path, nathers_tags=nat_tags)
    print("  Plans openings:   " + str(len(plan_windows)))

    result = reconcile_takeoff(plan_windows, nat_windows, {})
    assert len(result["rows"]) > 0, "Reconciliation produced 0 rows"
    print("  Rows: " + str(len(result["rows"])) + "  Confidence: " + str(round(result["overall_confidence"], 1)) + "%")

    excel_path = os.path.join(OUTPUTS_DIR, "test_grafton_output.xlsx")
    generate_takeoff_excel(result, excel_path, "74 Grafton Street", "Single Dwelling")
    assert os.path.exists(excel_path)
    print("  Excel saved OK: " + excel_path)


def test_integration_ulm_classification_and_extraction():
    """Ulm plan with BASIX in notes must classify as Plans and produce an extraction."""
    if skip_if_no_api_key(): return SKIP
    from services.extractor import extract_nathers_data, extract_plans_data

    plans_path   = pdf_path("Ulm", "AI - 18Ulm Plan.pdf")
    nathers_path = pdf_path("Ulm", "AI - 18Ulm NatHERS.pdf")
    if skip_if_no_pdf(plans_path) or skip_if_no_pdf(nathers_path): return SKIP

    c = classify_pdf(plans_path)
    assert c["file_type"] == "Plans", "Ulm plan misclassified as " + c["file_type"]

    nat_windows  = extract_nathers_data(nathers_path)
    nat_tags     = {str(w.get("tag", "")).strip().upper() for w in nat_windows}
    plan_windows = extract_plans_data(plans_path, nathers_tags=nat_tags)
    print("  NatHERS: " + str(len(nat_windows)) + "  Plans: " + str(len(plan_windows)))

    result = reconcile_takeoff(plan_windows, nat_windows, {}, has_plans=len(plan_windows) >= 3)
    print("  Rows: " + str(len(result["rows"])) + "  Confidence: " + str(round(result["overall_confidence"], 1)) + "%")


def test_integration_no_nathers_plans_only():
    """Plans-only submission (no NatHERS): must produce Review Required, rows with N/A glazing."""
    if skip_if_no_api_key(): return SKIP
    from services.extractor import extract_plans_data

    plans_path = pdf_path("Ayre", "AI - AYRE Plan.pdf")
    if skip_if_no_pdf(plans_path): return SKIP

    plan_windows = extract_plans_data(plans_path, nathers_tags=set())
    print("  Plans openings: " + str(len(plan_windows)))

    result = reconcile_takeoff(plan_windows, [], {}, has_nathers=False)
    assert result["is_rejected"]     is False, "Plans-only job must not be rejected"
    assert result["review_required"] is True,  "Plans-only job must require review"
    for row in result["rows"]:
        assert row["u_value"] == "N/A"
        assert row["shgc"]    == "N/A"
    nf = [f for f in result["flags"] if f["flag_type"] == "no_nathers_fallback"]
    assert nf, "Expected no_nathers_fallback info flag"
    print("  Rows: " + str(len(result["rows"])) + "  Review Required: " + str(result["review_required"]))


def test_integration_zillie_multi_dwelling():
    """Zillie: multi-dwelling NatHERS certificate -- system must not reject and must produce rows."""
    if skip_if_no_api_key(): return SKIP
    from services.extractor import extract_nathers_data

    nathers_path = pdf_path("zillie", "11439 (Lot 1808 Zillie Close Dubbo - NatHERS Cert) 20260113130631648.pdf")
    if skip_if_no_pdf(nathers_path): return SKIP

    nat_windows = extract_nathers_data(nathers_path)
    assert len(nat_windows) > 0, "Expected openings from Zillie multi-dwelling NatHERS"
    print("  NatHERS openings: " + str(len(nat_windows)))

    result = reconcile_takeoff([], nat_windows, {}, has_plans=False)
    assert len(result["rows"]) > 0, "Expected takeoff rows for Zillie multi-dwelling submission"
    print("  Rows: " + str(len(result["rows"])) + "  Confidence: " + str(round(result["overall_confidence"], 1)) + "%")


# ============================================================
# Test registry & runner
# ============================================================

UNIT_TESTS = [
    ("Classifier: Grafton Plans -> Plans",                       test_classify_grafton_plans),
    ("Classifier: Grafton NatHERS -> NatHERS",                   test_classify_grafton_nathers),
    ("Classifier: Ulm Plan (BASIX notes) -> Plans",              test_classify_ulm_plan_not_basix),
    ("Classifier: Ulm NatHERS -> NatHERS",                       test_classify_ulm_nathers),
    ("Classifier: McLachlan Plan (dual keywords) -> Plans",      test_classify_mclachlan_plan_not_hybrid),
    ("Classifier: Thrive BASIX -> BASIX",                        test_classify_thrive_basix),
    ("Classifier: Lot207 combined cert -> Hybrid/NatHERS/BASIX", test_classify_lot207_combined),
    ("Classifier: Ayre Plan -> Plans",                           test_classify_ayre_plan),
    ("Classifier: Ayre NatHERS -> NatHERS",                      test_classify_ayre_nathers),
    ("Classifier: Zillie NatHERS -> NatHERS",                    test_classify_zillie_nathers),
    ("Classifier: T001732 BASIX -> BASIX",                       test_classify_t001732_basix),
    ("Reconciler: Plan-primary dimensions win",                  test_reconcile_plan_primary_dimensions),
    ("Reconciler: Tagless dimension matching (BERS Pro)",         test_reconcile_tagless_dimension_matching),
    ("Reconciler: No-NatHERS fallback path",                     test_reconcile_no_nathers_fallback),
    ("Reconciler: Multi-NatHERS merged (multi-dwelling)",        test_reconcile_multi_nathers_merged),
    ("Reconciler: 0 rows = 0% confidence",                       test_reconcile_zero_rows_confidence),
    ("Reconciler: Plan room name over thermal zone",             test_reconcile_room_name_priority),
    ("Reconciler: classify_opening_type -> Window",              test_classify_opening_type_window),
    ("Reconciler: classify_opening_type -> Door",                test_classify_opening_type_door),
    ("Reconciler: classify_opening_type -> Bi-fold/Stacker",     test_classify_opening_type_bifold),
    ("Reconciler: normalize_location fuzzy match",               test_normalize_location_fn),
]

INTEGRATION_TESTS = [
    ("Integration: Grafton full pipeline",                       test_integration_grafton_full_pipeline),
    ("Integration: Ulm classification + extraction",             test_integration_ulm_classification_and_extraction),
    ("Integration: No-NatHERS plans-only fallback",              test_integration_no_nathers_plans_only),
    ("Integration: Zillie multi-dwelling NatHERS",               test_integration_zillie_multi_dwelling),
]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run FenX PDF Takeoff pipeline tests")
    parser.add_argument("--unit-only",        action="store_true", help="Run only unit tests (no LLM)")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    args = parser.parse_args()

    print("=" * 70)
    print("FenX PDF Takeoff -- Pipeline Test Suite")
    print("=" * 70)
    print()

    tests_to_run = []
    if not args.integration_only:
        tests_to_run.extend(UNIT_TESTS)
    if not args.unit_only:
        tests_to_run.extend(INTEGRATION_TESTS)

    for name, fn in tests_to_run:
        run_test(name, fn)

    print()
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    passed  = [r for r in results if r[1] == PASS]
    failed  = [r for r in results if r[1] == FAIL]
    skipped = [r for r in results if r[1] == SKIP]

    for name, status, msg in results:
        icon   = "OK" if status == PASS else ("XX" if status == FAIL else "--")
        detail = "  --  " + msg if msg else ""
        print("  [" + icon + "]  " + name + detail)

    print()
    total_str = (
        "Total: " + str(len(results)) +
        "  |  Passed: " + str(len(passed)) +
        "  |  Failed: " + str(len(failed)) +
        "  |  Skipped: " + str(len(skipped))
    )
    print("  " + total_str)
    print("=" * 70)

    if failed:
        sys.exit(1)
    else:
        print()
        print("All tests passed (or skipped)!")
        sys.exit(0)
