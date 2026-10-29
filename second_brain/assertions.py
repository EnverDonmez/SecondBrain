"""Cheap guards for client-selected user statements, not a language model."""

import re

from .language import folded
from .security import risks


DIRECT_TYPES = {"USER_ASSERTED_FACT", "USER_PREFERENCE", "PROJECT_STATE", "DECISION"}


def statement_reason(value, evidence):
    """None means eligible; authorship/meaning still comes from the connected client."""
    if len(evidence) != 1 or evidence[0]["actor"] != "user":
        return "direct_user_source_required"
    text = evidence[0]["text"]
    if risks(text) or risks(value):
        return "source_requires_review"
    start = text.find(value)
    if start < 0:
        return "verbatim_value_required"
    if not any(character.isalpha() for character in value):
        return "statement_context_required"
    before = text[:start]
    after = text[start + len(value) :]
    # Keep the complete clause: selecting '4. sınıf' out of '4. sınıf
    # değilim' or a question must not drop the qualifier/negation.
    if not value.rstrip().endswith((".", "!", ";", "\n")):
        if re.match(r"^[^.!;\n]*\?", after) or re.match(r"^\s*\w", after):
            return "complete_statement_clause_required"
    if (
        any(character in value for character in ['"', "“", "”", "`", "?"])
        or before.count('"') % 2
        or before.count("`") % 2
        or before.rfind("“") > before.rfind("”")
    ):
        return "quoted_or_questioned_statement"
    # Look behind a selected fragment as well, so selecting only '4. sınıfım'
    # from 'Diyelim ki 4. sınıfım' does not remove its hypothetical qualifier.
    clause_start = max(before.rfind("\n"), before.rfind(";"), before.rfind("!"), before.rfind("?")) + 1
    prefix = before[clause_start:]
    # Periods in numbered expressions (3. sınıf) are not sentence boundaries.
    boundaries = list(re.finditer(r"(?<!\d)\.\s", prefix))
    if boundaries:
        prefix = prefix[boundaries[-1].end() :]
    context = folded(prefix + value)
    if re.search(
        r"\b(?:belki|galiba|sanirim|eger|diyelim|mesela|ornegin|farz|maybe|perhaps|if|suppose|imagine|example)\b"
        r"|\b\w*(?:olsaydim|olabilirim|olabilir|olsam)\b",
        context,
    ):
        return "uncertain_or_hypothetical"
    if re.search(r"\b(?:yarin|seneye|gelecek|tomorrow)\b|\bnext (?:year|month)\b|\bwill be\b", context):
        return "future_statement_requires_dates"
    return None
