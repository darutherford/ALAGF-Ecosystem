"""Exception taxonomy for the ALAGF multiagent track.

Governance rationale: No silent failures. Every error condition raises a typed
exception that downstream code can catch and convert into a ledger event.
Silent error handling is prohibited by Invariant 4 (Reconstructability).

Inheritance:

    ALAGFError                       (root, abstract)
    ├── ArtifactValidationError      (v1 parity; JSON Schema violations)
    ├── AuthorityViolationError      (v1 parity; Invariant 1 breach)
    ├── AgentRegistrationError       (Sprint-1 net-new)
    ├── UnregisteredAgentError       (Sprint-1 net-new)
    ├── DepthLimitExceededError      (Sprint-1 reserved; Sprint-3 enforcement)
    └── LedgerIntegrityError         (Sprint-1 net-new; hash-chain violations)
"""

from __future__ import annotations


class ALAGFError(Exception):
    """Root of the multiagent exception hierarchy."""


class ArtifactValidationError(ALAGFError):
    """Raised when an artifact fails JSON Schema validation.

    Governance rationale: JSON Schema files are the single source of truth
    (Precondition 1). Violations of the schema contract must halt operation;
    they must not be coerced or logged-and-continued.
    """


class AuthorityViolationError(ALAGFError):
    """Raised when a construction attempt violates Invariant 1 (Authority).

    Examples:
        - Attempting to construct an AgentIdentity with non_authoritative_flag
          set to any value other than true.
        - Registering an agent with registered_by that references another
          agent_id instead of a human auditor.
    """


class AgentRegistrationError(ALAGFError):
    """Raised on registration failure.

    Causes include duplicate agent_id within a session, invalid parent
    reference for SUB_AGENT/VALIDATOR types, or schema violation of the
    constructed AgentIdentity.

    Governance rationale: Registration is the architectural foundation
    of the multi-agent extension. Registration integrity is non-negotiable.
    """


class UnregisteredAgentError(ALAGFError):
    """Raised when an output is received from an unregistered or inactive agent.

    The orchestrator emits an UNREGISTERED_AGENT_OUTPUT ledger event BEFORE
    raising this exception, in compliance with Invariant 4 (no silent failure).
    """


class DepthLimitExceededError(ALAGFError):
    """Raised when a synthesis operation would exceed max_synthesis_depth.

    Reserved for Sprint-3 structural enforcement. Not emitted in Sprint-1.
    Defined here to stabilize the exception taxonomy across sprints.
    """


class LedgerIntegrityError(ALAGFError):
    """Raised on ledger-layer integrity violations.

    Examples:
        - Attempting to write an event with a duplicate event_id.
        - Hash-chain verification failure on read.
        - Out-of-order sequence number.

    Governance rationale: The ledger is append-only and causally chained
    (Invariant 4). Any integrity violation is a hard stop.
    """
