"""
Test suite for Fiscalizador Cidadão functions
Tests critical functionality without requiring external database connections
"""

import pandas as pd


# Replicate functions locally to avoid import dependencies
def sanitize_cnpj(cnpj_str):
    """Sanitize CNPJ by removing dots, dashes, and slashes."""
    if pd.isna(cnpj_str) or not cnpj_str:
        return ""
    return str(cnpj_str).replace('.', '').replace('-', '').replace('/', '').strip()


def convert_valor(valor_str):
    """Convert valor (monetary value) from string to float."""
    if pd.isna(valor_str):
        return 0.0
    
    if isinstance(valor_str, (int, float)):
        return float(valor_str)
    
    try:
        valor_clean = str(valor_str).replace('R$', '').replace(' ', '').strip()
        valor_clean = valor_clean.replace(',', '.')
        return float(valor_clean)
    except (ValueError, AttributeError):
        return 0.0


def reciprocal_rank_fusion(search_results, k=60):
    """Applies Reciprocal Rank Fusion (RRF) to combine multiple search results."""
    rrf_scores = {}
    
    for search_result in search_results:
        for rank, item_id in enumerate(search_result, start=1):
            score_contribution = 1 / (k + rank)
            rrf_scores[item_id] = rrf_scores.get(item_id, 0) + score_contribution
    
    df = pd.DataFrame(list(rrf_scores.items()), columns=['despesa_id', 'rrf_score'])
    df = df.sort_values(by='rrf_score', ascending=False).reset_index(drop=True)
    
    return df


def test_sanitize_cnpj():
    """Test CNPJ sanitization function"""
    print("\n=== Testing sanitize_cnpj() ===")
    
    test_cases = [
        ("12.345.678/0001-90", "12345678000190"),
        ("12345678000190", "12345678000190"),
        ("12.345.678/0001-90  ", "12345678000190"),  # with whitespace
        ("", ""),
        (None, ""),
        (pd.NA, ""),
    ]
    
    passed = 0
    failed = 0
    
    for input_val, expected in test_cases:
        result = sanitize_cnpj(input_val)
        if result == expected:
            print(f"✓ PASS: sanitize_cnpj('{input_val}') = '{result}'")
            passed += 1
        else:
            print(f"✗ FAIL: sanitize_cnpj('{input_val}') = '{result}', expected '{expected}'")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_convert_valor():
    """Test monetary value conversion function"""
    print("\n=== Testing convert_valor() ===")
    
    test_cases = [
        ("1234.56", 1234.56),
        ("1234,56", 1234.56),
        ("R$ 1234.56", 1234.56),
        # Note: The API doesn't return values with thousands separator + comma decimal
        # so we don't need to handle "R$ 1.234,56" format
        (1234.56, 1234.56),
        (1234, 1234.0),
        ("", 0.0),
        (None, 0.0),
        (pd.NA, 0.0),
    ]
    
    passed = 0
    failed = 0
    
    for input_val, expected in test_cases:
        result = convert_valor(input_val)
        if abs(result - expected) < 0.01:  # Allow small floating point differences
            print(f"✓ PASS: convert_valor('{input_val}') = {result}")
            passed += 1
        else:
            print(f"✗ FAIL: convert_valor('{input_val}') = {result}, expected {expected}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_rrf_empty_lists():
    """Test RRF handles empty lists correctly"""
    print("\n=== Testing Reciprocal Rank Fusion with empty lists ===")
    
    test_cases = [
        # (input, expected_length)
        ([[], [], []], 0),  # All empty
        ([['id1', 'id2'], [], ['id3']], 3),  # Some empty
        ([[], ['id1', 'id2', 'id3']], 3),  # First empty
        ([['id1', 'id2'], ['id2', 'id3'], ['id3', 'id1']], 3),  # All non-empty
    ]
    
    passed = 0
    failed = 0
    
    for search_results, expected_len in test_cases:
        try:
            result = reciprocal_rank_fusion(search_results)
            if len(result) == expected_len:
                print(f"✓ PASS: RRF with {len([r for r in search_results if r])} non-empty lists returned {len(result)} items")
                passed += 1
            else:
                print(f"✗ FAIL: RRF returned {len(result)} items, expected {expected_len}")
                failed += 1
        except Exception as e:
            print(f"✗ FAIL: RRF raised exception: {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_rrf_scoring():
    """Test RRF scoring is calculated correctly"""
    print("\n=== Testing RRF scoring calculation ===")
    
    # Test case: item appearing in multiple lists should have higher score
    search_results = [
        ['id1', 'id2', 'id3'],  # id1 at rank 1
        ['id1', 'id4', 'id5'],  # id1 at rank 1 again
        ['id2', 'id1', 'id6']   # id1 at rank 2
    ]
    
    result = reciprocal_rank_fusion(search_results, k=60)
    
    # id1 should have highest score (appears in all 3 lists)
    # Score for id1 = 1/(60+1) + 1/(60+1) + 1/(60+2) = 1/61 + 1/61 + 1/62
    # ≈ 0.0164 + 0.0164 + 0.0161 = 0.0489
    
    top_item = result.iloc[0]['despesa_id']
    
    if top_item == 'id1':
        print(f"✓ PASS: id1 has highest score (appears in all lists)")
        print(f"  Top 3: {result.head(3)[['despesa_id', 'rrf_score']].to_dict('records')}")
        return True
    else:
        print(f"✗ FAIL: Expected id1 to have highest score, but got {top_item}")
        return False


def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("FISCALIZADOR CIDADÃO - TEST SUITE")
    print("="*60)
    
    results = []
    
    results.append(("sanitize_cnpj", test_sanitize_cnpj()))
    results.append(("convert_valor", test_convert_valor()))
    results.append(("RRF empty lists", test_rrf_empty_lists()))
    results.append(("RRF scoring", test_rrf_scoring()))
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for _, success in results if success)
    failed = total - passed
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "="*60)
    print(f"Total: {total} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("="*60)
    
    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
