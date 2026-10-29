"""Conservative, source-linked preference proposals; no model calls or activation."""

import hashlib
import re

from .security import normalize


def preference_candidates(text):
    explicit = re.fullmatch(r"\s*(tercihim|preference|kuralım|rule)\s*:\s*(.+)\s*", text, re.I | re.S)
    value = explicit[2].strip() if explicit else text.strip()
    if not value or "?" in value or len(value) > (50000 if explicit else 2000):
        return []
    folded = normalize(value).replace("ı", "i")
    # Questions, quotations and hypothetical examples are not direct preference assertions.
    if not explicit and (
        "?" in value
        or any(c in value for c in ['"', "“", "”", "«", "»", "\n", "`"])
        or re.search(r"\b(eger|ornegin|diyelim|birisi|biri|olsaydi)\b", folded)
    ):
        return []
    intent = bool(
        explicit
        or re.search(
            r"\b(tercih ederim|seviyorum|istiyorum|cevap ver|yanit ver|ettir|kontrol etsin)\b", folded
        )
    )
    negative = bool(
        re.search(r"\b(istemiyorum|sevmiyorum|kullanma|yazma|verme|ettirme|gosterme|degil)\b", folded)
    )
    found = []

    def add(predicate, canonical, kind="USER_PREFERENCE"):
        if explicit:
            kind = "POLICY" if explicit[1].casefold().startswith(("kural", "rule")) else "USER_PREFERENCE"
        found.append({"predicate": predicate, "value": canonical, "memory_type": kind})

    if intent and not negative:
        for language, canonical in [("turkce", "Türkçe"), ("ingilizce", "İngilizce")]:
            if re.search(r"\b" + language + r"\b", folded) and re.search(r"cevap|yanit|konus", folded):
                add("reply.language", canonical)
        for length, canonical in [
            ("kisa", "Kısa yanıt"),
            ("uzun", "Uzun yanıt"),
            ("detayli", "Detaylı yanıt"),
        ]:
            if re.search(r"\b" + length + r"\s+(?:ve\s+\w+\s+)?(?:cevap|yanit|aciklama)", folded):
                add("reply.length", canonical)
        if "paragraf" in folded and ("yerine" in folded or "tercih" in folded):
            add("reply.format", "Paragraf biçiminde yanıt")
        if re.search(r"koyu tema|karanlik tema", folded):
            add("ui.theme", "Koyu tema")
        elif re.search(r"acik tema|aydinlik tema", folded):
            add("ui.theme", "Açık tema")
        if re.search(r"kod|programlama", folded):
            for name in ["python", "javascript", "typescript", "rust"]:
                if re.search(r"\b" + name + r"\b", folded):
                    add("code.language", name)
        if re.search(r"(?:kendi|yerel) bilgisayar|yerelde", folded) and re.search(r"calis|proje", folded):
            add("deployment.target", "Kendi bilgisayarımda yerel çalışma")
    if (
        re.search(r"tiklamadan once|tiklama(?:dan)? (?:evvel|oncesinde)", folded)
        and re.search(r"ajan.*(?:kontrol|dogrula)|(?:kontrol|dogrula).*ajan", folded)
        and not negative
        and (intent or explicit)
    ):
        add("workflow.click_review", "Her tıklamadan önce bağımsız ajan hedefi doğrulasın.", "POLICY")
    if (re.search(r"kaynak\w*\s+goster(?:meni)?\b", folded) and not negative) or re.search(
        r"kaynak gostermeden kesin konusmani istemiyorum", folded
    ):
        add("reply.sources", "Kaynak göster; belirsiz bilgiyi kesinmiş gibi sunma.", "POLICY")
    if re.search(r"gereksiz onay (?:sorulari )?sorma", folded):
        add("workflow.confirmation", "Yetkili işlerde gereksiz onay soruları sorma.", "POLICY")
    if len({item["predicate"] for item in found}) != len(found):
        # Ambiguous alternatives must not create two conflicting claims from one sentence.
        found = []
    if explicit and not found:
        kind = "POLICY" if explicit[1].casefold().startswith(("kural", "rule")) else "USER_PREFERENCE"
        # Unclassified independent statements must not share one conflicting property.
        key = hashlib.sha256(folded.encode()).hexdigest()[:20]
        add(("rule." if kind == "POLICY" else "preference.") + key, value, kind)
    return list({(item["predicate"], item["value"]): item for item in found}.values())
