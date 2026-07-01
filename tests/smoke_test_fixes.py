import sys
sys.path.insert(0, '.')
from services.extractor import extract_nathers_data, extract_plans_data, extract_basix_data, _is_opaque_door
from services.reconciler import reconcile_takeoff, _flag_category_label
from services.excel_generator import generate_takeoff_excel

print('All imports OK')

# Test opaque door detection
assert _is_opaque_door('GD1', 'sectional', 'garage') == True
assert _is_opaque_door('W1', 'sliding', 'bedroom') == False
assert _is_opaque_door('D2', 'sliding door', 'kitchen') == False
print('Opaque door filter: OK')

# Test flag category labels
assert _flag_category_label('dimension_mismatch') == 'Dimension Mismatch'
assert _flag_category_label('basix_aggregate_mismatch') == 'BASIX Area Mismatch'
print('Flag category labels: OK')

# Reconciler mock test
nathers = [
    {'tag': 'W1', 'location': 'Study', 'height': 1200, 'width': 900, 'type': 'awning', 'orientation': 'N', 'glazing': 'SSW-025-304', 'u_value': 4.1, 'shgc': 0.53, 'frame_material': 'Aluminium', 'quantity': 1, 'src_ref': 'NatHERS p.5'},
    {'tag': 'D2', 'location': 'Kitchen/Family', 'height': 2100, 'width': 2140, 'type': 'sliding door', 'orientation': 'NNW', 'glazing': 'SSW-025-305', 'u_value': 5.7, 'shgc': 0.67, 'frame_material': 'Aluminium', 'quantity': 1, 'src_ref': 'NatHERS p.5'},
]
plans = [
    {'tag': 'W1', 'location': 'Garage', 'height': 1200, 'width': 900, 'type': 'awning', 'orientation': 'N', 'quantity': 1, 'src_ref': 'Plans p.3'},
]
basix = {'total_glazing_area': 36.90, 'cert_number': '1825211S', 'commitments': []}

result = reconcile_takeoff(plans, nathers, basix)

w1_row = next(r for r in result['rows'] if r['tag'] == 'W1')
assert w1_row['location'] == 'Study', f"Expected 'Study', got '{w1_row['location']}'"
print(f"FIX #1 Room attribution: PASS (W1 = {w1_row['location']})")

assert str(w1_row['u_value']) == '4.1', f"Expected 4.1, got {w1_row['u_value']}"
print(f"FIX #2 Per-row U-value: PASS (W1 u_value = {w1_row['u_value']})")

d2_flags = [f for f in result['flags'] if 'D2' in str(f.get('item_ref',''))]
assert len(d2_flags) > 0, 'D2 should be flagged as missing in plans'
print('FIX #4 D2 glazed door flagged: PASS')

for f in result['flags']:
    assert f.get('item_ref'), f'item_ref blank in flag: {f}'
    assert f.get('category'), f'category blank in flag: {f}'
print('FIX #8 Item Ref + Category populated: PASS')

basix_flag = next((f for f in result['flags'] if f['flag_type'] == 'basix_aggregate_mismatch'), None)
if basix_flag:
    assert 'anchor' in basix_flag['description'], 'BASIX flag should say certificate is the anchor'
    print('FIX #6 BASIX flag direction: PASS')

print()
print('All checks PASSED')
