import pytest

from second_brain.core import Brain
from second_brain.models import OWNER, EventInput, MemoryInput


@pytest.fixture
def brain(tmp_path):
    return Brain(tmp_path / "brain")


@pytest.fixture
def make_memory(brain):
    def create(
        value="Türkçe",
        predicate="language",
        subject="user",
        scope="global",
        valid_from="2026-01-01",
        supersedes=None,
        actor="user",
        memory_type="USER_ASSERTED_FACT",
        sensitivity=1,
    ):
        import secrets

        event = brain.events.ingest(
            EventInput(
                source="test",
                source_id=secrets.token_hex(8),
                actor=actor,
                text=value,
                scope=scope,
                sensitivity=sensitivity,
                occurred_at=valid_from,
            ),
            OWNER,
        )
        memory = brain.memory.propose(
            MemoryInput(
                predicate=predicate,
                subject=subject,
                value=value,
                source_event_ids=[event["id"]],
                scope=scope,
                valid_from=valid_from,
                supersedes=supersedes,
                memory_type=memory_type,
                sensitivity=sensitivity,
            ),
            OWNER,
        )
        return brain.memory.commit(memory["id"], OWNER)

    return create
