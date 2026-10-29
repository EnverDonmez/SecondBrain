from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Actor = Literal["user", "assistant", "tool", "document", "system"]


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def timestamp(value: str | float | int | None) -> str:
    if value is None:
        return now()
    if isinstance(value, (float, int)):
        return datetime.fromtimestamp(value, UTC).isoformat(timespec="microseconds")
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat(timespec="microseconds")


class MemoryType(StrEnum):
    USER_ASSERTED_FACT = "USER_ASSERTED_FACT"
    USER_PREFERENCE = "USER_PREFERENCE"
    OBSERVED_EVENT = "OBSERVED_EVENT"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    PROJECT_STATE = "PROJECT_STATE"
    DECISION = "DECISION"
    CORRECTION = "CORRECTION"
    LESSON = "LESSON"
    PROCEDURE = "PROCEDURE"
    SKILL = "SKILL"
    POLICY = "POLICY"
    EXTERNAL_KNOWLEDGE = "EXTERNAL_KNOWLEDGE"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginInput(StrictModel):
    token: str = Field(default="", max_length=4096)
    remember: bool = Field(default=False, strict=True)


class EventInput(StrictModel):
    source: str = Field(min_length=1, max_length=80)
    source_id: str = Field(min_length=1, max_length=500)
    event_type: str = Field(default="conversation.message", max_length=100)
    actor: Actor = "user"
    text: str = Field(default="", max_length=2_000_000)
    occurred_at: str | None = None
    session_id: str | None = None
    conversation_id: str | None = None
    parent_id: str | None = None
    scope: str = Field(default="global", min_length=1, max_length=200)
    sensitivity: int = Field(default=1, ge=0, le=3)
    metadata: dict = Field(default_factory=dict)
    payload: dict = Field(default_factory=dict)
    attachments: list[str] = Field(default_factory=list)
    schema_version: int = 1

    @field_validator("occurred_at")
    @classmethod
    def normalize_date(cls, v):
        return timestamp(v) if v else v


class MemoryInput(StrictModel):
    memory_type: MemoryType = MemoryType.USER_ASSERTED_FACT
    subject: str = Field(default="user", min_length=1, max_length=200)
    predicate: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=50_000)
    scope: str = Field(default="global", min_length=1, max_length=200)
    source_event_ids: list[str] = Field(min_length=1, max_length=100)
    confidence: float = Field(default=1, ge=0, le=1)
    sensitivity: int = Field(default=1, ge=0, le=3)
    valid_from: str | None = None
    valid_to: str | None = None
    supersedes: str | None = None
    importance: int = Field(default=3, ge=1, le=5)
    topics: list[str] = Field(default_factory=list, max_length=8)
    related_memory_ids: list[str] = Field(default_factory=list, max_length=8)

    @field_validator("topics", "related_memory_ids")
    @classmethod
    def compact_links(cls, values):
        if any(not value.strip() or len(value) > 120 for value in values):
            raise ValueError("Topics and related IDs must contain 1–120 characters")
        return list(dict.fromkeys(value.strip() for value in values))

    @field_validator("valid_from", "valid_to")
    @classmethod
    def normalize_date(cls, v):
        return timestamp(v) if v else v

    @model_validator(mode="after")
    def interval(self):
        if self.valid_to and self.valid_from and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be after valid_from")
        return self


class SearchInput(StrictModel):
    query: str = Field(default="", max_length=2000)
    scope: str | None = None
    memory_type: MemoryType | None = None
    subject: str | None = None
    predicate: str | None = None
    source: str | None = None
    valid_at: str | None = None
    known_at: str | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1000000)
    status: Literal["active", "candidate", "disputed", "rejected"] | None = None
    engine: Literal["economy", "fts", "bm25", "hybrid", "vector", "graph", "mem0"] = "economy"
    include_candidates: bool = False
    graph_hops: int = Field(default=1, ge=0, le=2)

    @field_validator("valid_at", "known_at")
    @classmethod
    def normalize_date(cls, v):
        return timestamp(v) if v else v


class RememberFact(StrictModel):
    assertion: Literal["candidate", "direct_user"] = "candidate"
    memory_type: MemoryType = MemoryType.MODEL_INFERENCE
    subject: str = Field(default="user", min_length=1, max_length=200)
    predicate: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=2000)
    topics: list[str] = Field(default_factory=list, max_length=8)
    related_memory_ids: list[str] = Field(default_factory=list, max_length=8)
    supersedes: str | None = None
    importance: int = Field(default=3, ge=1, le=5)
    confidence: float = Field(default=0.8, ge=0, le=1)


class ContextInput(StrictModel):
    query: str = Field(default="Beynimi tara", max_length=2000)
    scope: str | None = None
    budget: int = Field(default=3000, ge=512, le=32000)
    engine: Literal["economy", "fts", "bm25", "hybrid", "vector", "graph", "mem0"] = "economy"
    graph_hops: int = Field(default=1, ge=0, le=2)
    valid_at: str | None = None
    known_at: str | None = None
    since: str | None = None
    until: str | None = None
    known_state: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,80}$")

    @field_validator("valid_at", "known_at", "since", "until")
    @classmethod
    def normalize_date(cls, value):
        return timestamp(value) if value else value

    @model_validator(mode="after")
    def interval(self):
        if self.since and self.until and self.since > self.until:
            raise ValueError("since must not be after until")
        return self


class MemoryChange(StrictModel):
    operation: Literal["organize", "approve", "reject", "hide"]
    id: str = Field(min_length=1, max_length=200)
    instruction: str = Field(min_length=1, max_length=2000)
    topics: list[str] | None = Field(default=None, max_length=8)
    related_memory_ids: list[str] | None = Field(default=None, max_length=8)

    @field_validator("topics", "related_memory_ids")
    @classmethod
    def compact(cls, values):
        return MemoryInput.compact_links(values) if values is not None else None

    @model_validator(mode="after")
    def metadata_only(self):
        editing = self.topics is not None or self.related_memory_ids is not None
        if (self.operation == "organize") != editing:
            raise ValueError("Only organize accepts topics/links, and it requires at least one of them")
        return self


class RememberInput(StrictModel):
    source_text: str = Field(min_length=1, max_length=24000)
    source_id: str | None = Field(default=None, min_length=1, max_length=500)
    source: str = Field(default="ai-conversation", min_length=1, max_length=80)
    actor: Literal["user", "assistant", "document"] = "assistant"
    scope: str = Field(default="global", min_length=1, max_length=200)
    sensitivity: int = Field(default=1, ge=0, le=3)
    occurred_at: str | None = None
    facts: list[RememberFact] = Field(default_factory=list, max_length=12)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=200)
    checkpoint: str | None = Field(default=None, min_length=1, max_length=1500)
    topics: list[str] = Field(default_factory=list, max_length=8)
    change: MemoryChange | None = None

    @model_validator(mode="after")
    def separate_change(self):
        if self.change and self.facts:
            raise ValueError("Save facts and change an existing record in separate requests")
        return self

    @field_validator("topics")
    @classmethod
    def compact_topics(cls, values):
        return MemoryInput.compact_links(values)

    @field_validator("occurred_at")
    @classmethod
    def normalize_date(cls, v):
        return timestamp(v) if v else v


class NavigateInput(StrictModel):
    branch: Literal[
        "root", "preferences", "projects", "topics", "knowledge", "conversations", "skills", "tools", "review"
    ] = "root"
    key: str | None = Field(default=None, max_length=500)
    query: str = Field(default="", max_length=2000)
    scope: str | None = None
    limit: int = Field(default=8, ge=1, le=20)
    offset: int = Field(default=0, ge=0, le=1000000)
    budget: int = Field(default=1800, ge=512, le=16000)
    valid_at: str | None = None
    known_at: str | None = None
    since: str | None = None
    until: str | None = None
    include_history: bool = False
    records: bool = False

    @field_validator("valid_at", "known_at", "since", "until")
    @classmethod
    def normalize_date(cls, value):
        return timestamp(value) if value else value

    @model_validator(mode="after")
    def interval(self):
        if self.since and self.until and self.since > self.until:
            raise ValueError("since must not be after until")
        return self


class ReadInput(StrictModel):
    kind: Literal["memory", "event", "skill", "tool"] = "memory"
    id: str = Field(min_length=1, max_length=200)
    query: str = Field(default="", max_length=2000)
    offset: int = Field(default=0, ge=0, le=2000000)
    characters: int = Field(default=1200, ge=100, le=6000)
    budget: int = Field(default=2400, ge=512, le=16000)
    valid_at: str | None = None
    known_at: str | None = None
    include_history: bool = False
    include_pending: bool = False
    path: str | None = Field(default=None, min_length=1, max_length=500)

    @field_validator("valid_at", "known_at")
    @classmethod
    def normalize_date(cls, value):
        return timestamp(value) if value else value

    @model_validator(mode="after")
    def skill_path(self):
        if self.path is not None and self.kind != "skill":
            raise ValueError("path is only supported for skill files")
        if self.include_pending and (
            self.kind != "memory" or self.include_history or self.valid_at or self.known_at
        ):
            raise ValueError("Pending reads only support current memory cards")
        return self


class Principal(StrictModel):
    id: str = "local-owner"
    tenant: str = "local"
    role: Literal["owner", "agent", "reader"] = "owner"
    scopes: list[str] = Field(default_factory=lambda: ["*"])
    permissions: list[str] = Field(
        default_factory=lambda: ["read", "propose", "capture", "approve", "delete", "admin"]
    )
    clearance: int = Field(default=3, ge=0, le=3)
    credential_id: str | None = None

    def permits_scope(self, scope: str) -> bool:
        return "*" in self.scopes or scope in self.scopes


OWNER = Principal()
