"""Quick smoke test for all ARIVO components."""
import sys

print("=" * 60)
print("ARIVO — Component Verification")
print("=" * 60)

# 1. LangGraph compilation
try:
    from arivo.agents.graph import compiled_graph
    print("[OK] LangGraph compiled:", type(compiled_graph).__name__)
except Exception as e:
    print(f"[FAIL] LangGraph: {e}")
    sys.exit(1)

# 2. Mock Veeva client
try:
    from arivo.tools.veeva_client import list_change_controls, authenticate
    auth = authenticate()
    print(f"[OK] Veeva auth: session={auth['sessionId'][:20]}...")
    ccs = list_change_controls()
    print(f"[OK] Change controls: {[cc['change_control_id'] for cc in ccs]}")
except Exception as e:
    print(f"[FAIL] Veeva client: {e}")
    sys.exit(1)

# 3. SUPAC rules engine
try:
    from arivo.tools.regulatory_rules import classify_supac, classify_ema
    result = classify_supac("Site Change", "Semisolid - Cream", "Transfer to different city")
    print(f"[OK] SUPAC: Level {result['level']} -> {result['filing_type']}")
    ema = classify_ema(result["filing_type"])
    print(f"[OK] EMA: {ema['variation_type']}")
except Exception as e:
    print(f"[FAIL] Regulatory rules: {e}")
    sys.exit(1)

# 4. E2B XML builder
try:
    from arivo.tools.e2b_builder import build_e2b_xml
    from arivo.tools.e2b_validator import validate_e2b_xml
    test_report = {
        "safety_report": {
            "case_id": "TEST-001",
            "report_type": "1",
            "seriousness": "Non-Serious",
            "patient": {"age": 45, "sex": "M"},
            "reactions": [{"meddra_pt": "Headache", "meddra_code": "10019211", "outcome": "Recovered"}],
            "drugs": [{"name": "Test Drug", "dose": "10mg", "characterization": "1"}],
            "narrative_summary": "Test narrative",
        }
    }
    xml = build_e2b_xml(test_report)
    validation = validate_e2b_xml(xml)
    print(f"[OK] E2B XML: {len(xml)} chars, valid={validation['valid']}")
    if validation["errors"]:
        print(f"     Errors: {validation['errors']}")
    if validation["warnings"]:
        print(f"     Warnings: {validation['warnings']}")
except Exception as e:
    print(f"[FAIL] E2B builder: {e}")
    sys.exit(1)

# 5. Dossier templates
try:
    from arivo.tools.dossier_templates import get_module_2_3_template
    template = get_module_2_3_template()
    print(f"[OK] M4Q(R2) templates loaded ({len(template)} chars)")
except Exception as e:
    print(f"[FAIL] Dossier templates: {e}")
    sys.exit(1)

# 6. FastAPI app
try:
    from arivo.api.app import app
    print(f"[OK] FastAPI app: {app.title} v{app.version}")
except Exception as e:
    print(f"[FAIL] FastAPI app: {e}")
    sys.exit(1)

print("=" * 60)
print("ALL CHECKS PASSED")
print("=" * 60)
