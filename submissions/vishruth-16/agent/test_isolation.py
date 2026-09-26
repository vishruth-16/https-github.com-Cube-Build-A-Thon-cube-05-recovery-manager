import sys
from pathlib import Path

# Add agent directory to python path
sys.path.append(str(Path(__file__).parent))
from storage import OperationalEvidenceStore

def find_repo_data_dir() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        candidate = parent / "data"
        if candidate.exists() and (candidate / "fee_report_sample.csv").exists():
            return candidate
    raise FileNotFoundError("Could not locate the 'data' directory in repository hierarchy.")

def test_tenancy_isolation():
    data_dir = find_repo_data_dir()
    print(f"Loading data from: {data_dir}")
    store = OperationalEvidenceStore(data_dir=data_dir)

    # 1. Verify alpha can see its own unit UNIT-0002
    alpha_prep = store.get_unit_evidence("org_demo_alpha", "UNIT-0002")
    assert len(alpha_prep) > 0, "Failed: org_demo_alpha should have records for UNIT-0002"
    assert alpha_prep[0]["org_id"] == "org_demo_alpha"
    print(f"✓ Found {len(alpha_prep)} record(s) for UNIT-0002 under org_demo_alpha.")

    # 2. Verify bravo cannot see alpha's records
    bravo_leak = store.get_unit_evidence("org_demo_bravo", "UNIT-0002")
    assert len(bravo_leak) == 0, "CRITICAL TENANCY LEAK: org_demo_bravo accessed org_demo_alpha data!"
    print("✓ Cross-tenant query blocked: org_demo_bravo sees 0 rows for UNIT-0002.")

    # 3. Verify fee report tenancy
    alpha_fees = store.get_fee_charges("org_demo_alpha")
    bravo_fees = store.get_fee_charges("org_demo_bravo")
    assert len(alpha_fees) > 0, "Failed: org_demo_alpha fee reports missing"
    for fee in bravo_fees:
        assert fee["org_id"] == "org_demo_bravo", "Fee tenancy leak detected"
    print(f"✓ Fee reports isolated: alpha has {len(alpha_fees)}, bravo has {len(bravo_fees)}.")

    print("\nPASS: Tenancy isolation strictly enforced (Engineering Rule 1).")

if __name__ == "__main__":
    test_tenancy_isolation()
