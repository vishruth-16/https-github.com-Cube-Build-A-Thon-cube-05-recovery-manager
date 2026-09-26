import csv
from pathlib import Path
from typing import Dict, List
from collections import defaultdict

class TenancyViolationError(Exception):
    pass

class OperationalEvidenceStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._upstream_by_unit: Dict[str, Dict[str, List[dict]]] = defaultdict(lambda: defaultdict(list))
        self._fee_reports: Dict[str, List[dict]] = defaultdict(list)
        self._load_fee_reports()
        self._load_upstream_records()

    def _load_fee_reports(self):
        fee_file = self.data_dir / "fee_report_sample.csv"
        if not fee_file.exists():
            return

        with open(fee_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                org_id = row.get("org_id")
                if org_id:
                    self._fee_reports[org_id].append(row)

    def _load_upstream_records(self):
        upstream_dir = self.data_dir / "upstream"
        if not upstream_dir.exists():
            return

        for csv_path in upstream_dir.glob("*.csv"):
            manager_type = csv_path.stem.replace("_sample", "")
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    org_id = row.get("org_id")
                    unit_id = row.get("unit_id")
                    if not org_id or not unit_id:
                        continue
                    
                    row["source_manager"] = manager_type
                    self._upstream_by_unit[org_id][unit_id].append(row)

    def get_unit_evidence(self, org_id: str, unit_id: str) -> List[dict]:
        if org_id not in self._upstream_by_unit:
            return []
        return self._upstream_by_unit[org_id].get(unit_id, [])

    def get_fee_charges(self, org_id: str) -> List[dict]:
        return self._fee_reports.get(org_id, [])
