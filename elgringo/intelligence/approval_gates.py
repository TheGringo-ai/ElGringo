"""
Human-in-the-Loop Approval Gates
==================================

Closes the gap with CrewAI/AutoGen/LangGraph's human-in-the-loop features.
Allows workflows to pause at configurable checkpoints for human approval,
rejection, or modification before continuing.

Usage:
    gates = ApprovalGateManager()

    # Create a gate
    gate_id = gates.create_gate(
        workflow_id="wf-123",
        description="Deploy to production?",
        context={"changes": 15, "risk": "medium"},
    )

    # Check status (from MCP tool)
    status = gates.get_gate(gate_id)

    # Approve/reject (from MCP tool)
    gates.approve(gate_id, comment="LGTM")
    gates.reject(gate_id, reason="Too risky")
"""

import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class GateStatus(Enum):
    """Status of an approval gate."""
    PENDING = "pending"       # Waiting for human decision
    APPROVED = "approved"     # Human approved
    REJECTED = "rejected"     # Human rejected
    MODIFIED = "modified"     # Human approved with modifications
    EXPIRED = "expired"       # Gate timed out
    SKIPPED = "skipped"       # Gate was bypassed (auto-approve mode)


class GateType(Enum):
    """Types of approval gates."""
    DEPLOY = "deploy"                # Before deployment
    CODE_CHANGE = "code_change"      # Before applying code changes
    SECURITY = "security"            # Security-sensitive operations
    DATA_DELETE = "data_delete"      # Before deleting data
    COST = "cost"                    # High-cost operations
    WORKFLOW_STEP = "workflow_step"  # Between workflow phases
    CUSTOM = "custom"                # User-defined


@dataclass
class ApprovalGate:
    """A human approval checkpoint in a workflow."""
    gate_id: str
    workflow_id: str
    gate_type: GateType
    description: str
    status: GateStatus = GateStatus.PENDING
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_at: Optional[str] = None
    resolved_by: str = ""  # "human", "auto", "timeout"
    comment: str = ""
    modifications: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 3600  # Default 1 hour
    auto_approve_if: Optional[Dict[str, Any]] = None  # Conditions for auto-approval

    @property
    def is_resolved(self) -> bool:
        return self.status not in (GateStatus.PENDING,)

    @property
    def is_expired(self) -> bool:
        if self.status != GateStatus.PENDING:
            return False
        created = datetime.fromisoformat(self.created_at)
        elapsed = (datetime.now(timezone.utc) - created).total_seconds()
        return elapsed > self.timeout_seconds

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["gate_type"] = self.gate_type.value
        d["status"] = self.status.value
        return d


class ApprovalGateManager:
    """
    Manages human approval gates for workflows.

    Supports:
    - Creating gates at workflow checkpoints
    - Blocking until approval/rejection
    - Auto-approval based on configurable rules
    - Expiration/timeout handling
    - Persistent gate history
    """

    def __init__(self, storage_dir: str = "~/.ai-dev-team/gates"):
        self.storage_dir = Path(os.path.expanduser(storage_dir))
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._gates: Dict[str, ApprovalGate] = {}
        self._auto_rules: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        """Load gates from disk."""
        gates_file = self.storage_dir / "gates.json"
        if gates_file.exists():
            try:
                with open(gates_file) as f:
                    data = json.load(f)
                for g in data:
                    g["gate_type"] = GateType(g["gate_type"])
                    g["status"] = GateStatus(g["status"])
                    gate = ApprovalGate(**g)
                    self._gates[gate.gate_id] = gate
            except Exception as e:
                logger.warning(f"Error loading gates: {e}")

        rules_file = self.storage_dir / "auto_rules.json"
        if rules_file.exists():
            try:
                with open(rules_file) as f:
                    self._auto_rules = json.load(f)
            except Exception:
                pass

    def _save(self):
        """Save gates to disk."""
        try:
            with open(self.storage_dir / "gates.json", "w") as f:
                json.dump([g.to_dict() for g in self._gates.values()], f, indent=2)
        except Exception as e:
            logger.warning(f"Error saving gates: {e}")

    def create_gate(
        self,
        workflow_id: str,
        description: str,
        gate_type: str = "custom",
        context: Optional[Dict[str, Any]] = None,
        timeout_seconds: int = 3600,
        auto_approve_if: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a new approval gate.

        Returns:
            Gate ID
        """
        gate_id = f"gate-{uuid.uuid4().hex[:8]}"

        gt = GateType(gate_type) if gate_type in [t.value for t in GateType] else GateType.CUSTOM

        gate = ApprovalGate(
            gate_id=gate_id,
            workflow_id=workflow_id,
            gate_type=gt,
            description=description,
            context=context or {},
            timeout_seconds=timeout_seconds,
            auto_approve_if=auto_approve_if,
        )

        # Check auto-approval rules
        if self._check_auto_approve(gate):
            gate.status = GateStatus.SKIPPED
            gate.resolved_at = datetime.now(timezone.utc).isoformat()
            gate.resolved_by = "auto"
            gate.comment = "Auto-approved by rule"
            logger.info(f"Gate {gate_id} auto-approved")
        else:
            logger.info(f"Gate {gate_id} created — waiting for human approval: {description}")

        self._gates[gate_id] = gate
        self._save()
        return gate_id

    def approve(self, gate_id: str, comment: str = "") -> bool:
        """Approve a pending gate."""
        gate = self._gates.get(gate_id)
        if not gate or gate.is_resolved:
            return False

        gate.status = GateStatus.APPROVED
        gate.resolved_at = datetime.now(timezone.utc).isoformat()
        gate.resolved_by = "human"
        gate.comment = comment
        self._save()
        logger.info(f"Gate {gate_id} APPROVED: {comment}")
        return True

    def reject(self, gate_id: str, reason: str = "") -> bool:
        """Reject a pending gate."""
        gate = self._gates.get(gate_id)
        if not gate or gate.is_resolved:
            return False

        gate.status = GateStatus.REJECTED
        gate.resolved_at = datetime.now(timezone.utc).isoformat()
        gate.resolved_by = "human"
        gate.comment = reason
        self._save()
        logger.info(f"Gate {gate_id} REJECTED: {reason}")
        return True

    def modify_and_approve(
        self, gate_id: str, modifications: Dict[str, Any], comment: str = ""
    ) -> bool:
        """Approve with modifications."""
        gate = self._gates.get(gate_id)
        if not gate or gate.is_resolved:
            return False

        gate.status = GateStatus.MODIFIED
        gate.resolved_at = datetime.now(timezone.utc).isoformat()
        gate.resolved_by = "human"
        gate.comment = comment
        gate.modifications = modifications
        self._save()
        logger.info(f"Gate {gate_id} MODIFIED+APPROVED: {comment}")
        return True

    def get_gate(self, gate_id: str) -> Optional[ApprovalGate]:
        """Get gate status."""
        gate = self._gates.get(gate_id)
        if gate and gate.is_expired:
            gate.status = GateStatus.EXPIRED
            gate.resolved_at = datetime.now(timezone.utc).isoformat()
            gate.resolved_by = "timeout"
            self._save()
        return gate

    def get_pending_gates(self, workflow_id: str = "") -> List[ApprovalGate]:
        """Get all pending gates, optionally filtered by workflow."""
        # Expire any timed-out gates first
        for gate in self._gates.values():
            if gate.status == GateStatus.PENDING and gate.is_expired:
                gate.status = GateStatus.EXPIRED
                gate.resolved_at = datetime.now(timezone.utc).isoformat()
                gate.resolved_by = "timeout"
        self._save()

        pending = [g for g in self._gates.values() if g.status == GateStatus.PENDING]
        if workflow_id:
            pending = [g for g in pending if g.workflow_id == workflow_id]
        return sorted(pending, key=lambda g: g.created_at)

    def wait_for_approval(self, gate_id: str, poll_interval: float = 1.0) -> GateStatus:
        """
        Blocking wait for gate resolution (for use in workflows).
        Returns the final gate status.
        """
        while True:
            gate = self.get_gate(gate_id)
            if not gate:
                return GateStatus.REJECTED
            if gate.is_resolved:
                return gate.status
            time.sleep(poll_interval)

    def add_auto_rule(
        self,
        gate_type: str,
        condition: str,
        description: str = "",
    ):
        """
        Add an auto-approval rule.

        Args:
            gate_type: Gate type to match (e.g. "code_change")
            condition: Condition expression (e.g. "risk == low", "changes < 5")
            description: Human-readable description
        """
        self._auto_rules.append({
            "gate_type": gate_type,
            "condition": condition,
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        try:
            with open(self.storage_dir / "auto_rules.json", "w") as f:
                json.dump(self._auto_rules, f, indent=2)
        except Exception:
            pass

    def _check_auto_approve(self, gate: ApprovalGate) -> bool:
        """Check if a gate should be auto-approved."""
        # Check gate-specific auto-approve condition
        if gate.auto_approve_if:
            ctx = gate.context
            for key, expected in gate.auto_approve_if.items():
                if ctx.get(key) != expected:
                    return False
            return True

        # Check global auto-rules
        for rule in self._auto_rules:
            if rule["gate_type"] == gate.gate_type.value:
                # Simple condition evaluation
                cond = rule["condition"]
                try:
                    if self._eval_condition(cond, gate.context):
                        return True
                except Exception:
                    pass

        return False

    def _eval_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate a simple condition against context."""
        # Support: "key == value", "key < number", "key > number"
        for op, fn in [("==", lambda a, b: a == b), ("!=", lambda a, b: a != b),
                       ("<=", lambda a, b: a <= b), (">=", lambda a, b: a >= b),
                       ("<", lambda a, b: a < b), (">", lambda a, b: a > b)]:
            if op in condition:
                parts = condition.split(op, 1)
                key = parts[0].strip()
                value = parts[1].strip()

                ctx_value = context.get(key)
                if ctx_value is None:
                    return False

                # Try numeric comparison
                try:
                    return fn(float(ctx_value), float(value))
                except (ValueError, TypeError):
                    return fn(str(ctx_value), value)

        return False

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent gate history."""
        gates = sorted(self._gates.values(), key=lambda g: g.created_at, reverse=True)
        return [g.to_dict() for g in gates[:limit]]

    def clear_expired(self) -> int:
        """Remove expired gates. Returns count removed."""
        expired = [gid for gid, g in self._gates.items() if g.status == GateStatus.EXPIRED]
        for gid in expired:
            del self._gates[gid]
        if expired:
            self._save()
        return len(expired)


def get_gate_manager() -> ApprovalGateManager:
    """Get singleton gate manager."""
    if not hasattr(get_gate_manager, "_instance"):
        get_gate_manager._instance = ApprovalGateManager()
    return get_gate_manager._instance
