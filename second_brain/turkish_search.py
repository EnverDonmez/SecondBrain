"""Turkish lexical stems adapted from AvenoxBeyin v3.12.0 (MIT, Copyright 2026 Avenox)."""

import re
from functools import lru_cache

from .language import folded


_VOWELS = "aeiou"
_VOICELESS = "cfhkpst"
# Longest matches first, with the upstream stem-length and sound guards.
_SUFFIXES = (
    ("masin mesin", 4, "ln"),
    ("mali meli", 5, "ln"),
    ("iyor uyor acak ecek acag eceg", 4, "ln"),
    ("imiz umuz iniz unuz", 4, "consonant"),
    ("nden ndan", 5, "vowel"),
    ("ten tan", 4, "voiceless"),
    ("den dan", 4, "voiced"),
    ("nin nun nde nda", 5, "vowel"),
    ("miz muz niz nuz yla yle", 4, "vowel"),
    ("ler lar", 3, "any"),
    ("mak mek mis mus", 4, "ln"),
    ("te ta", 4, "voiceless"),
    ("de da", 4, "voiced"),
    ("si su ya ye yi yu", 4, "vowel"),
    ("in un im um le la", 4, "consonant"),
    ("di du", 5, "passive"),
    ("ma me", 4, "ln"),
    ("ir ur ar er", 5, "ln"),
    ("i u e a", 4, "consonant"),
)
_RULES = [(suffix, floor, gate) for group, floor, gate in _SUFFIXES for suffix in group.split()]
_BY_LAST = {
    last: [rule for rule in _RULES if rule[0][-1] == last] for last in {suffix[-1] for suffix, _, _ in _RULES}
}
_VOWEL_LOSS = {
    "sehr": "sehir",
    "fikr": "fikir",
    "beyn": "beyin",
    "metn": "metin",
    "kism": "kisim",
    "hukm": "hukum",
    "nehr": "nehir",
    "zihn": "zihin",
    "vakt": "vakit",
    "nesl": "nesil",
    "seyr": "seyir",
    "haps": "hapis",
    "keyf": "keyif",
    "kayb": "kayip",
    "kayd": "kayit",
    "nakd": "nakit",
    "cism": "cisim",
    "zulm": "zulum",
    "kahr": "kahir",
    "sekl": "sekil",
    "gonl": "gonul",
    "gogs": "gogus",
    "ismi": "isim",
    "ismin": "isim",
    "isme": "isim",
    "akli": "akil",
    "aklin": "akil",
    "akla": "akil",
    "agzi": "agiz",
    "agzin": "agiz",
    "agza": "agiz",
    "oglu": "ogul",
    "oglun": "ogul",
    "omru": "omur",
    "omrun": "omur",
}


def _attaches(stem, gate):
    last = stem[-1]
    if gate == "passive":
        return last in "ln" and stem[-2] in "iu"
    return {
        "vowel": last in _VOWELS,
        "consonant": last not in _VOWELS,
        "voiceless": last in _VOICELESS,
        "voiced": last not in _VOICELESS,
        "ln": last in "ln",
        "any": True,
    }[gate]


@lru_cache(maxsize=16384)
def stem(word):
    while len(word) >= 5 and word != "claude":
        for suffix, floor, gate in _BY_LAST.get(word[-1], ()):
            if not word.endswith(suffix):
                continue
            root = word[: -len(suffix)]
            if len(root) < floor or not _attaches(root, gate):
                continue
            tone = next((char for char in suffix if char in _VOWELS), "")
            last_vowel = next((char for char in reversed(root) if char in _VOWELS), "")
            if tone in ("a", "e") and last_vowel in ("a", "e") and last_vowel != tone:
                continue
            word = root
            break
        else:
            break
    word = _VOWEL_LOSS.get(word, word)
    if len(word) >= 4 and word[-2] in _VOWELS and word[-1] in "bg":
        word = word[:-1] + ("p" if word[-1] == "b" else "k")
    return word


def stem_key(word):
    return "sbstem" + stem(word) if re.fullmatch(r"[a-z]{3,64}", word) else None


def index_text(text):
    # Keep existing exact and prefix matches and add a separate stem vocabulary.
    words = dict.fromkeys(re.findall(r"\w+", folded(text)))
    keys = dict.fromkeys(
        key for word in words if not word.startswith("sbconcept") and (key := stem_key(word))
    )
    return text + " " + " ".join(keys) if keys else text


def match_terms(words, *, all_terms=False, prefix=False):
    parts = []
    for word in dict.fromkeys(words):
        exact = '"' + word + '"' + ("*" if prefix and not word.startswith("sbconcept") else "")
        key = stem_key(folded(word)) if not word.startswith("sbconcept") else None
        parts.append(f'({exact} OR "{key}")' if key else exact)
    return (" AND " if all_terms else " OR ").join(parts)
