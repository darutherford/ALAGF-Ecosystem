"""Boundary enforcement orchestrator module.

Sprint-2 scope: AgentHandoff lifecycle and BOUNDARY_HANDSHAKE protocol.

Governance rationale (project core principle): agent boundaries are
governance boundaries. Every crossing of an agent boundary is an auditable
ledger event, not an implementation detail. This package implements the
runtime that polices those crossings.

Submodules:
    handshake   BOUNDARY_HANDSHAKE emission and channel lookup. Directional
                channels between registered ACTIVE agents within a single
                session.
    handoff     AGENT_HANDOFF emission with full precondition validation.
                Emits BOUNDARY_VIOLATION and raises BoundaryViolationError
                (or HandshakeError) on any precondition failure.
"""

from .handoff import (
    emit_handoff,
    get_handoff,
    list_session_handoffs,
    validate_handoff_preconditions,
)
from .handshake import (
    emit_handshake,
    is_channel_established,
    list_established_channels,
)

__all__ = [
    "emit_handoff",
    "emit_handshake",
    "get_handoff",
    "is_channel_established",
    "list_established_channels",
    "list_session_handoffs",
    "validate_handoff_preconditions",
]
