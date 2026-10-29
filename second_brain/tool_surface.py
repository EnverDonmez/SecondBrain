"""One default model-facing workflow; legacy tools are an explicit opt-in."""

CORE_TOOLS = ["brain.prepare_context", "brain.remember", "brain.navigate", "brain.read"]
LEGACY_TOOLS = [
    "brain.search",
    "brain.recall",
    "brain.prepare_context",
    "brain.get_profile",
    "brain.get_project_state",
    "brain.timeline",
    "brain.propose_memory",
    "brain.remember",
    "brain.navigate",
    "brain.read",
    "brain.correct_memory",
    "brain.record_feedback",
    "brain.list_skills",
    "brain.get_skill",
    "brain.get_skill_file",
    "brain.list_capabilities",
    "brain.sync_status",
]
CONTRACT_VERSION = 4
