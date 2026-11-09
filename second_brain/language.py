"""Small transparent Turkish/English retrieval vocabulary; not a language model."""

import re

from .security import normalize


STOP = set(
    """the a an is are what which my in of to and ve veya bir bu ne nedir hangi benim
icin ile mi mı mu mü kullanicinin user nasil bana benden beni sen sana senin her once sonra
gore olarak daha da de en birseyi seyi sey onu bunu diye kadar hakkinda neydi neden
olmasini oldugunu oldugum istiyorum isterim seviyorum tercih ederim vermelisin
etmek etmeli misin ne yapmayi yapmali konusmustuk ogrenmistik olmustu kime
surekli dun simdi yeni verdik""".split()
)

# Whole forms keep unrelated words out of the concept vocabulary. General
# Turkish inflection matching is handled separately in the lexical index.
CONCEPTS = {
    "answer": (
        "cevap",
        "cevabi",
        "cevaplar",
        "cevaplari",
        "yanit",
        "yaniti",
        "yanitlar",
        "yanitlari",
        "response",
        "responses",
        "answer",
        "answers",
    ),
    "short": ("kisa", "ozlu", "concise", "short"),
    "long": ("uzun", "detayli", "long", "detailed"),
    "click": (
        "tikla",
        "tiklama",
        "tiklamadan",
        "tiklamak",
        "dugme",
        "click",
        "clicking",
        "basmadan",
        "basmak",
    ),
    "review": (
        "kontrol",
        "dogrula",
        "dogrulasin",
        "dogrulat",
        "dogrulama",
        "incele",
        "inceleme",
        "review",
        "reviewing",
        "verify",
    ),
    "agent": ("ajan", "ajana", "ajani", "ajanin", "ajanlar", "agent", "agents"),
    "source": (
        "kaynak",
        "kaynagi",
        "kaynaklar",
        "kaynaklari",
        "referans",
        "citation",
        "citations",
        "source",
        "sources",
    ),
    "uncertain": ("belirsiz", "suphe", "uncertain"),
    "permission": ("onay", "onayi", "onayini", "onayla", "izin", "izni", "permission", "approval"),
    "database": ("veritabani", "database", "depolama"),
    "remote": ("bulut", "uzak", "cloud", "remote"),
    "send": ("gonder", "yolla", "send"),
    "data": ("veri", "data"),
    "bug": ("hata", "hatayi", "hatalar", "bug", "bugs", "ariza", "defect"),
    "fix": (
        "duzelt",
        "duzeltme",
        "duzelttikten",
        "duzelttim",
        "duzeltince",
        "duzeltilince",
        "giderdik",
        "giderince",
        "giderdikten",
        "onar",
        "onarim",
        "fix",
        "fixed",
        "fixing",
    ),
    "test": ("test", "testi", "testler", "testleri", "testing", "regresyon", "regression"),
    "plant": ("bahce", "bahcedeki", "bitki", "bitkiler", "bitkileri", "garden", "plant", "plants"),
    "water": ("sula", "sulama", "sulamayi", "sulamak", "water", "watering"),
    "ocr": ("ocr",),
    "dark": ("koyu", "karanlik", "dark"),
    "light": ("aydinlik", "acik", "light"),
    "interface": ("arayuz", "interface"),
    "code": ("kod", "programlama", "code", "coding"),
}
CONCEPT_BY_WORD = {word: key for key, words in CONCEPTS.items() for word in words}


def folded(text):
    return normalize(text).replace("ı", "i")


def is_continuity_query(query):
    return folded(query).strip().rstrip("?!.,") in {
        "nerede kaldik",
        "nerede kalmistik",
        "en son ne yaptik",
        "kaldigimiz yerden devam edelim",
        "where did we leave off",
        "continue from the last session",
    }


def terms(text):
    text = folded(text)
    words = re.findall(r"\w+", text)
    result = []
    for word in words:
        if word in STOP:
            continue
        concept = CONCEPT_BY_WORD.get(word)
        result.append("@" + concept if concept else word)
    if re.search(r"emin (?:olma|degil)|kesin (?:bilme|olma)", text):
        result.append("@uncertain")
    if re.search(r"metin\w* oku|yazi\w* oku|text recognition", text):
        result.append("@ocr")
    return list(dict.fromkeys(result))


def polarity(text):
    """A conservative contradiction guard, including common Turkish negatives."""
    text = folded(text)
    return bool(
        re.search(
            r"\b(?:degil|asla|hayir|not|never|no|yok)\b|\w+(?:madan|meden|miyorum|miyoruz|ma|me|masin|mesin|mayin|meyin)\b",
            text,
        )
    )


def lesson_key(text):
    """Only two explicit workflow equivalences; preserve all original evidence."""
    value, concepts = folded(text), set(terms(text))
    if re.search(
        r"istemiyorum|etme(?:sin|yin)?\b|ettirme(?:sin|yin)?\b|gerek yok|yapma\b|alma\b|degil|\?", value
    ):
        return None
    if (
        {"@click", "@agent"} <= concepts
        and concepts & {"@review", "@permission"}
        and re.search(r"tiklamadan once|tiklama onces|basmadan (?:once|evvel)", value)
    ):
        return "workflow.click_review"
    if {"@bug", "@fix", "@test"} <= concepts and "sonra" in value and not polarity(text):
        return "workflow.regression_after_fix"
    return None


def compatible_values(left, right):
    a, b = set(terms(left)), set(terms(right))
    for x, y in [("@dark", "@light"), ("@short", "@long")]:
        if (x in a and y in b) or (y in a and x in b):
            return False
    names = {
        "sqlite",
        "postgresql",
        "mysql",
        "python",
        "javascript",
        "typescript",
        "rust",
        "turkce",
        "ingilizce",
    }
    av, bv = a & names, b & names
    return not av or not bv or av == bv
