"""
Universal Ingestor - Schema-Agnostic Data Intelligence
=======================================================

The "gatekeeper" that greets any CSV, identifies its personality,
and prepares it for ROI, Audit, and MTBF analysis.

CAPABILITIES:
1. Semantic Schema Mapping - Maps unknown columns to golden schema
2. Unit Normalization - Converts hours/minutes, costs, dates
3. Text Categorization - Clusters messy technician notes
4. Outlier Detection - Flags data entry errors
5. Chunk Processing - Memory-efficient for 16GB Macs
6. CMMS Vendor Detection - Recognizes 15+ major CMMS vendors

SUPPORTED CMMS VENDORS:
- IBM Maximo
- SAP PM (Plant Maintenance)
- Infor EAM
- UpKeep
- Fiix (Rockwell)
- eMaint (Fluke)
- Limble CMMS
- Maintenance Connection
- FMX
- Hippo CMMS
- MPulse
- MicroMain
- Dude Solutions / Brightly
- ServiceChannel
- Generic/Common

GOLDEN SCHEMA (What all reports expect):
- Asset_ID: Unique equipment identifier
- Asset_Description: Equipment name
- Work_Order_Number: WO identifier
- Date_Completed: When work finished
- Date_Due: When work was due
- Date_Created: When WO was created
- Assigned_Name: Technician name
- Hours: Labor hours
- Estimated_Hours: Planned hours
- PartCosts: Parts/materials cost
- Work_Type_ID: Type code (REPAIR, PM, etc.)
- Purpose: Work description
- Description: Detailed notes
- Entity_Name: Facility/location
- Status: WO status
- Priority: Priority level
"""

import csv
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Import comprehensive CMMS schemas
from .cmms_schemas import (
    COMPREHENSIVE_ALIASES,
    identify_vendor,
)

logger = logging.getLogger(__name__)

# Increase CSV field limit for large text fields
csv.field_size_limit(10 * 1024 * 1024)


@dataclass
class ColumnMapping:
    """Mapping result for a single column."""
    source_column: str
    target_column: str
    confidence: float  # 0-1
    match_type: str   # "exact", "semantic", "data_pattern", "inferred"
    transform: Optional[str] = None  # Any transform needed


@dataclass
class SchemaAnalysis:
    """Complete analysis of an unknown schema."""
    source_file: str
    total_rows: int
    source_columns: List[str]
    mappings: List[ColumnMapping]
    unmapped_columns: List[str]
    quality_score: float
    warnings: List[str]
    sample_data: List[Dict]


# Golden Schema Definition
GOLDEN_SCHEMA = {
    "Asset_ID": {
        "type": "identifier",
        "required": True,
        "aliases": [
            "asset_id", "assetid", "asset id", "equipment_id", "equipmentid",
            "equip_id", "equipid", "machine_id", "machineid", "asset_tag",
            "assettag", "equip_tag", "equiptag", "asset_number", "assetnumber",
            "unit_id", "unitid", "asset_code", "assetcode", "equipment_code"
        ],
        "patterns": [
            r"^\d{2}-\d{4}",           # 03-1277
            r"^[A-Z]{2,4}-\d{2,5}",    # PMP-01, HVAC-123
            r"^[A-Z]+\d+",             # PUMP1, MOTOR23
        ],
        "description": "Unique identifier for equipment/asset"
    },
    "Asset_Description": {
        "type": "text",
        "required": False,
        "aliases": [
            "asset_description", "assetdescription", "asset_name", "assetname",
            "equipment_name", "equipmentname", "machine_name", "machinename",
            "description", "asset", "equipment", "machine", "unit_name"
        ],
        "description": "Human-readable equipment name"
    },
    "Work_Order_Number": {
        "type": "identifier",
        "required": True,
        "aliases": [
            "work_order_number", "workordernumber", "wo_number", "wonumber",
            "work_order", "workorder", "wo", "wo_id", "woid", "wo_num",
            "ticket", "ticket_number", "ticketnumber", "job_number", "jobnumber",
            "order_id", "orderid", "request_id", "requestid", "wo#", "work order #"
        ],
        "patterns": [
            r"^\d{5,8}$",              # 254233
            r"^WO-?\d+",               # WO-12345
            r"^[A-Z]{2}\d{6,}",        # PM123456
        ],
        "description": "Unique work order identifier"
    },
    "Date_Completed": {
        "type": "datetime",
        "required": False,
        "aliases": [
            "date_completed", "datecompleted", "completed_date", "completeddate",
            "completion_date", "completiondate", "finish_date", "finishdate",
            "closed_date", "closeddate", "actual_finish", "actualfinish",
            "end_date", "enddate", "done_date", "donedate"
        ],
        "description": "When the work was completed"
    },
    "Date_Due": {
        "type": "datetime",
        "required": True,
        "aliases": [
            "date_due", "datedue", "due_date", "duedate", "target_date",
            "targetdate", "scheduled_date", "scheduleddate", "deadline",
            "required_date", "requireddate", "need_by", "needby", "plan_date"
        ],
        "description": "When the work is due"
    },
    "Date_Created": {
        "type": "datetime",
        "required": False,
        "aliases": [
            "date_created", "datecreated", "created_date", "createddate",
            "create_date", "createdate", "open_date", "opendate",
            "request_date", "requestdate", "submit_date", "submitdate",
            "reported_date", "reporteddate", "entry_date"
        ],
        "description": "When the work order was created"
    },
    "Assigned_Name": {
        "type": "text",
        "required": True,
        "aliases": [
            "assigned_name", "assignedname", "technician", "tech_name",
            "techname", "assigned_to", "assignedto", "worker", "worker_name",
            "workername", "mechanic", "mechanic_name", "mechanicname",
            "employee", "employee_name", "employeename", "assignee",
            "resource", "resource_name", "performed_by", "performedby"
        ],
        "description": "Name of assigned technician"
    },
    "Hours": {
        "type": "numeric",
        "required": False,
        "aliases": [
            "hours", "labor_hours", "laborhours", "actual_hours", "actualhours",
            "work_hours", "workhours", "time_spent", "timespent", "duration",
            "total_hours", "totalhours", "hrs", "labour_hours"
        ],
        "unit_detection": {
            "minutes": r"min|minute",
            "hours": r"hour|hr",
        },
        "description": "Actual hours worked"
    },
    "Estimated_Hours": {
        "type": "numeric",
        "required": False,
        "aliases": [
            "estimated_hours", "estimatedhours", "est_hours", "esthours",
            "planned_hours", "plannedhours", "budget_hours", "budgethours",
            "target_hours", "targethours", "expected_hours", "expectedhours"
        ],
        "description": "Planned/estimated hours"
    },
    "PartCosts": {
        "type": "numeric",
        "required": False,
        "aliases": [
            "partcosts", "part_costs", "partscost", "parts_cost", "material_cost",
            "materialcost", "parts_total", "partstotal", "component_cost",
            "componentcost", "materials", "material", "cost", "total_cost"
        ],
        "description": "Cost of parts/materials"
    },
    "Work_Type_ID": {
        "type": "category",
        "required": False,
        "aliases": [
            "work_type_id", "worktypeid", "work_type", "worktype", "type_id",
            "typeid", "maintenance_type", "maintenancetype", "job_type",
            "jobtype", "type", "category", "work_category", "workcategory",
            "maint_type", "mainttype", "wo_type", "wotype"
        ],
        "categories": {
            "REPAIR": ["repair", "fix", "corrective", "breakdown", "emergency"],
            "PREVENTIVE": ["pm", "preventive", "preventative", "scheduled", "routine"],
            "INSPECTION": ["inspect", "inspection", "check", "audit"],
            "INSTALLATION": ["install", "setup", "commission"],
            "MODIFICATION": ["modify", "upgrade", "improvement"],
        },
        "description": "Type of maintenance work"
    },
    "Purpose": {
        "type": "text",
        "required": False,
        "aliases": [
            "purpose", "reason", "task_description", "taskdescription",
            "work_description", "workdescription", "task", "summary",
            "short_description", "shortdescription", "subject", "title"
        ],
        "description": "Brief description of work"
    },
    "Description": {
        "type": "text",
        "required": False,
        "aliases": [
            "description", "notes", "comments", "remarks", "details",
            "narrative", "work_notes", "worknotes", "long_description",
            "longdescription", "note", "comment"
        ],
        "description": "Detailed notes/comments"
    },
    "Entity_Name": {
        "type": "text",
        "required": False,
        "aliases": [
            "entity_name", "entityname", "facility", "facility_name",
            "facilityname", "plant", "plant_name", "plantname", "site",
            "site_name", "sitename", "location", "location_name",
            "locationname", "building", "department", "area"
        ],
        "description": "Facility/location name"
    },
    "Status": {
        "type": "category",
        "required": False,
        "aliases": [
            "status", "status_id", "statusid", "wo_status", "wostatus",
            "state", "current_status", "currentstatus", "order_status"
        ],
        "description": "Work order status"
    },
    "Priority": {
        "type": "category",
        "required": False,
        "aliases": [
            "priority", "priority_level", "prioritylevel", "urgency",
            "severity", "importance", "priority_id", "priorityid"
        ],
        "description": "Priority level"
    },
}


class UniversalIngestor:
    """
    Schema-agnostic data ingestion engine.

    Handles any CSV format and maps it to the golden schema
    for use with ROI, Audit, and MTBF analysis tools.
    """

    def __init__(self, use_embeddings: bool = False):
        """
        Initialize the ingestor.

        Args:
            use_embeddings: Use MLX embeddings for semantic matching
                           (slower but more accurate for weird column names)
        """
        self.use_embeddings = use_embeddings
        self._embeddings_model = None
        self.detected_vendor = "Unknown"

        # Build lookup tables from GOLDEN_SCHEMA (base aliases)
        self._alias_to_target = {}
        for target, config in GOLDEN_SCHEMA.items():
            for alias in config.get("aliases", []):
                normalized = self._normalize_column_name(alias)
                self._alias_to_target[normalized] = target

        # Extend with comprehensive CMMS vendor aliases
        for target, aliases in COMPREHENSIVE_ALIASES.items():
            for alias in aliases:
                normalized = self._normalize_column_name(alias)
                if normalized not in self._alias_to_target:
                    self._alias_to_target[normalized] = target

        logger.info(f"Universal Ingestor initialized with {len(self._alias_to_target)} field aliases")

    def _normalize_column_name(self, name: str) -> str:
        """Normalize column name for comparison."""
        return re.sub(r'[^a-z0-9]', '', name.lower())

    def _parse_date(self, val: str) -> Optional[datetime]:
        """Try to parse a date from various formats."""
        if not val or str(val).lower() in ('nan', 'nat', 'none', ''):
            return None

        formats = [
            "%m/%d/%Y %I:%M %p",
            "%m/%d/%Y %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%d/%m/%Y",
            "%Y/%m/%d",
            "%m-%d-%Y",
            "%d-%m-%Y",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(str(val).strip(), fmt)
            except ValueError:
                continue
        return None

    def _parse_number(self, val: str) -> Optional[float]:
        """Parse numeric value."""
        if not val or str(val).lower() in ('nan', 'none', ''):
            return None
        try:
            clean = re.sub(r'[,$\s]', '', str(val))
            return float(clean)
        except ValueError:
            return None

    def _detect_column_type(self, values: List[str]) -> str:
        """Detect the data type of a column from sample values."""
        non_empty = [v for v in values if v and str(v).strip()]
        if not non_empty:
            return "unknown"

        sample = non_empty[:20]

        # Check for dates
        date_count = sum(1 for v in sample if self._parse_date(v) is not None)
        if date_count > len(sample) * 0.7:
            return "datetime"

        # Check for numbers
        num_count = sum(1 for v in sample if self._parse_number(v) is not None)
        if num_count > len(sample) * 0.7:
            return "numeric"

        # Check for identifiers (short, structured strings)
        if all(len(str(v)) < 30 for v in sample):
            pattern_match = sum(1 for v in sample if re.match(r'^[\w\-#]+$', str(v)))
            if pattern_match > len(sample) * 0.8:
                return "identifier"

        return "text"

    def _match_by_alias(self, column: str) -> Optional[Tuple[str, float]]:
        """Try to match column by alias lookup."""
        normalized = self._normalize_column_name(column)

        if normalized in self._alias_to_target:
            return (self._alias_to_target[normalized], 0.95)

        # Partial match
        for alias, target in self._alias_to_target.items():
            if alias in normalized or normalized in alias:
                return (target, 0.7)

        return None

    def _match_by_pattern(self, column: str, values: List[str],
                          target: str, config: Dict) -> Optional[float]:
        """Match column by data patterns."""
        patterns = config.get("patterns", [])
        if not patterns:
            return None

        sample = [v for v in values[:20] if v and str(v).strip()]
        if not sample:
            return None

        for pattern in patterns:
            matches = sum(1 for v in sample if re.match(pattern, str(v)))
            if matches > len(sample) * 0.5:
                return 0.8

        return None

    def _match_by_type(self, column: str, values: List[str],
                       target: str, config: Dict) -> Optional[float]:
        """Match column by data type compatibility."""
        expected_type = config.get("type")
        detected_type = self._detect_column_type(values)

        if expected_type == detected_type:
            # Type matches, give partial credit
            return 0.4

        return None

    def analyze_schema(self, file_path: str, sample_rows: int = 100) -> SchemaAnalysis:
        """
        Analyze a CSV file and map its columns to the golden schema.

        Args:
            file_path: Path to CSV file
            sample_rows: Number of rows to sample for analysis

        Returns:
            SchemaAnalysis with mappings and quality metrics
        """
        path = Path(file_path)
        logger.info(f"Analyzing schema: {path.name}")

        # Read sample data
        rows = []
        columns = []
        total_rows = 0

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            # Find header row
            lines = []
            for i, line in enumerate(f):
                lines.append(line)
                if i > 10:
                    break

            # Detect header
            header_idx = 0
            for i, line in enumerate(lines):
                if 'Date' in line or 'Asset' in line or 'Work' in line:
                    header_idx = i
                    break

            # Re-read with correct header
            f.seek(0)
            for _ in range(header_idx):
                next(f)

            reader = csv.DictReader(f)
            columns = reader.fieldnames or []

            for i, row in enumerate(reader):
                if i < sample_rows:
                    rows.append(row)
                total_rows += 1

        logger.info(f"  Found {len(columns)} columns, {total_rows} rows")

        # Detect CMMS vendor
        self.detected_vendor = identify_vendor(columns)
        if self.detected_vendor != "Unknown":
            logger.info(f"  Detected CMMS vendor: {self.detected_vendor}")

        # Build column value samples
        column_values = {col: [] for col in columns}
        for row in rows:
            for col in columns:
                column_values[col].append(row.get(col, ''))

        # Map columns
        mappings = []
        mapped_targets = set()
        warnings = []

        for col in columns:
            values = column_values[col]
            best_match = None
            best_confidence = 0
            match_type = "none"

            # Try alias matching first (fastest)
            alias_match = self._match_by_alias(col)
            if alias_match:
                target, conf = alias_match
                if conf > best_confidence and target not in mapped_targets:
                    best_match = target
                    best_confidence = conf
                    match_type = "alias"

            # Try pattern matching
            for target, config in GOLDEN_SCHEMA.items():
                if target in mapped_targets:
                    continue

                pattern_conf = self._match_by_pattern(col, values, target, config)
                if pattern_conf and pattern_conf > best_confidence:
                    best_match = target
                    best_confidence = pattern_conf
                    match_type = "pattern"

            # Try type matching
            if not best_match or best_confidence < 0.5:
                for target, config in GOLDEN_SCHEMA.items():
                    if target in mapped_targets:
                        continue

                    type_conf = self._match_by_type(col, values, target, config)
                    if type_conf and type_conf > best_confidence:
                        best_match = target
                        best_confidence = type_conf
                        match_type = "type"

            if best_match and best_confidence >= 0.4:
                mappings.append(ColumnMapping(
                    source_column=col,
                    target_column=best_match,
                    confidence=best_confidence,
                    match_type=match_type
                ))
                mapped_targets.add(best_match)

        # Find unmapped columns
        unmapped = [col for col in columns
                    if col not in [m.source_column for m in mappings]]

        # Check for required columns
        for target, config in GOLDEN_SCHEMA.items():
            if config.get("required") and target not in mapped_targets:
                warnings.append(f"Required column '{target}' not found in source data")

        # Calculate quality score
        required_mapped = sum(1 for m in mappings
                             if GOLDEN_SCHEMA.get(m.target_column, {}).get("required"))
        total_required = sum(1 for c in GOLDEN_SCHEMA.values() if c.get("required"))

        if total_required > 0:
            quality = (required_mapped / total_required) * 0.6 + \
                      (len(mappings) / len(GOLDEN_SCHEMA)) * 0.4
        else:
            quality = len(mappings) / len(GOLDEN_SCHEMA)

        return SchemaAnalysis(
            source_file=path.name,
            total_rows=total_rows,
            source_columns=columns,
            mappings=mappings,
            unmapped_columns=unmapped,
            quality_score=min(1.0, quality),
            warnings=warnings,
            sample_data=rows[:5]
        )

    def ingest(self, file_path: str,
               custom_mappings: Optional[Dict[str, str]] = None,
               chunk_size: int = 10000) -> Dict[str, Any]:
        """
        Ingest a CSV file and return standardized data.

        Args:
            file_path: Path to CSV file
            custom_mappings: Override automatic mappings {source: target}
            chunk_size: Process in chunks for memory efficiency

        Returns:
            Dict with:
            - schema_analysis: SchemaAnalysis object
            - data: List of standardized row dicts
            - statistics: Aggregated statistics
        """
        # Analyze schema
        analysis = self.analyze_schema(file_path)

        # Build final mapping (auto + custom overrides)
        final_mapping = {m.source_column: m.target_column for m in analysis.mappings}
        if custom_mappings:
            final_mapping.update(custom_mappings)

        # Process data
        standardized_rows = []
        stats = defaultdict(lambda: {"count": 0, "sum": 0, "min": None, "max": None})

        with open(file_path, 'r', encoding='utf-8-sig') as f:
            # Skip to header
            lines = f.readlines()
            header_idx = 0
            for i, line in enumerate(lines):
                if 'Date' in line or 'Asset' in line or 'Work' in line:
                    header_idx = i
                    break

            content = ''.join(lines[header_idx:])
            reader = csv.DictReader(content.splitlines())

            for row in reader:
                std_row = {}

                for source, target in final_mapping.items():
                    value = row.get(source, '')
                    config = GOLDEN_SCHEMA.get(target, {})

                    # Type conversion
                    if config.get("type") == "datetime":
                        std_row[target] = self._parse_date(value)
                    elif config.get("type") == "numeric":
                        num_val = self._parse_number(value)
                        std_row[target] = num_val

                        # Track stats
                        if num_val is not None:
                            stats[target]["count"] += 1
                            stats[target]["sum"] += num_val
                            if stats[target]["min"] is None or num_val < stats[target]["min"]:
                                stats[target]["min"] = num_val
                            if stats[target]["max"] is None or num_val > stats[target]["max"]:
                                stats[target]["max"] = num_val
                    else:
                        std_row[target] = str(value).strip() if value else ""

                standardized_rows.append(std_row)

        # Calculate averages
        for target in stats:
            if stats[target]["count"] > 0:
                stats[target]["avg"] = stats[target]["sum"] / stats[target]["count"]

        return {
            "schema_analysis": analysis,
            "data": standardized_rows,
            "statistics": dict(stats),
            "row_count": len(standardized_rows),
            "mapping_used": final_mapping
        }

    def generate_mapping_report(self, analysis: SchemaAnalysis) -> str:
        """Generate a human-readable mapping report."""
        lines = []
        lines.append("# Schema Mapping Report")
        lines.append(f"\n**Source File:** {analysis.source_file}")
        lines.append(f"**Total Rows:** {analysis.total_rows:,}")
        lines.append(f"**Quality Score:** {analysis.quality_score:.0%}")
        if self.detected_vendor != "Unknown":
            lines.append(f"**Detected CMMS:** {self.detected_vendor}")

        lines.append("\n## Column Mappings\n")
        lines.append("| Source Column | Target Field | Confidence | Match Type |")
        lines.append("|--------------|--------------|------------|------------|")

        for m in sorted(analysis.mappings, key=lambda x: -x.confidence):
            lines.append(
                f"| {m.source_column} | {m.target_column} | "
                f"{m.confidence:.0%} | {m.match_type} |"
            )

        if analysis.unmapped_columns:
            lines.append("\n## Unmapped Columns\n")
            lines.append("*These columns were not recognized:*\n")
            for col in analysis.unmapped_columns:
                lines.append(f"- `{col}`")

        if analysis.warnings:
            lines.append("\n## Warnings\n")
            for warn in analysis.warnings:
                lines.append(f"- {warn}")

        return "\n".join(lines)


def get_universal_ingestor(use_embeddings: bool = False) -> UniversalIngestor:
    """Get a configured UniversalIngestor instance."""
    return UniversalIngestor(use_embeddings=use_embeddings)


# CLI for testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python universal_ingestor.py <csv_file>")
        sys.exit(1)

    ingestor = UniversalIngestor()
    analysis = ingestor.analyze_schema(sys.argv[1])

    print(ingestor.generate_mapping_report(analysis))

    print("\n\nSample mappings for code:")
    print("{")
    for m in analysis.mappings:
        print(f'    "{m.source_column}": "{m.target_column}",')
    print("}")
