"""Invariant 3 (Evidence-First) acceptance tests.

Every ledger event produced by Sprint-1 carries a causal chain pointer:
    - AGENT_REGISTERED references the session_id and auditor_id.
    - AGENT_SUSPENDED references the ledger event ID of the prior
      AGENT_REGISTERED via causal_refs.prior_event_id AND the payload's
      prior_registration_event_id.
    - AGENT_REVOKED references the prior AGENT_REGISTERED identically.
"""

from __future__ import annotations

from multiagent.ledger.hash_chain.events import read_session_events
from multiagent.orchestrator.agent_lifecycle.registration import (
    register_agent,
    revoke_agent,
    suspend_agent,
)


def test_agent_registered_carries_auditor_and_session(
    session_id: str, auditor_id: str
) -> None:
    register_agent(
        session_id=session_id,
        auditor_id=auditor_id,
        agent_type="ORCHESTRATOR",
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        trust_tier="T1",
        authority_scope="ROUTING",
        max_synthesis_depth=1,
    )
    events = read_session_events(session_id)
    assert len(events) == 1
    evt = events[0]
    assert evt["event_type"] == "AGENT_REGISTERED"
    assert evt["auditor_id"] == auditor_id
    assert evt["session_id"] == session_id
    assert evt["actor"]["actor_type"] == "HUMAN"
    assert evt["actor"]["actor_id"] == auditor_id


def test_agent_suspended_references_prior_registration(
    session_id: str, auditor_id: str
) -> None:
    record = register_agent(
        session_id=session_id,
        auditor_id=auditor_id,
        agent_type="ORCHESTRATOR",
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        trust_tier="T1",
        authority_scope="ROUTING",
        max_synthesis_depth=1,
    )
    registration_event_id = record["_registration_event_id"]

    suspend_agent(
        agent_id=record["agent_id"],
        auditor_id=auditor_id,
        reason="acceptance test",
    )

    events = read_session_events(session_id)
    suspended = next(e for e in events if e["event_type"] == "AGENT_SUSPENDED")

    # Envelope-level causal ref.
    assert suspended["causal_refs"]["prior_event_id"] == registration_event_id
    assert suspended["causal_refs"]["referenced_event_id"] == registration_event_id
    # Payload-level ref for redundant traceability.
    assert (
        suspended["payload"]["prior_registration_event_id"]
        == registration_event_id
    )


def test_agent_revoked_references_prior_registration(
    session_id: str, auditor_id: str
) -> None:
    record = register_agent(
        session_id=session_id,
        auditor_id=auditor_id,
        agent_type="ORCHESTRATOR",
        model_id="claude-sonnet-4-6",
        provider="anthropic",
        trust_tier="T1",
        authority_scope="ROUTING",
        max_synthesis_depth=1,
    )
    registration_event_id = record["_registration_event_id"]

    revoke_agent(
        agent_id=record["agent_id"],
        auditor_id=auditor_id,
        reason="acceptance test",
    )

    events = read_session_events(session_id)
    revoked = next(e for e in events if e["event_type"] == "AGENT_REVOKED")
    assert revoked["causal_refs"]["prior_event_id"] == registration_event_id
    assert revoked["payload"]["prior_registration_event_id"] == registration_event_id
