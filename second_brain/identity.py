"""Stable property keys; explicit aliases only, never fuzzy truth merging."""

import re
import unicodedata


def name_key(value):
    return " ".join(unicodedata.normalize("NFC", value).casefold().replace("i\u0307", "i").split())


def subject_key(value):
    key = name_key(value)
    return "user" if key in {"user", "self", "me", "kullanıcı", "kullanici"} else key


def predicate_key(subject, value):
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1.\2", value)
    key = re.sub(r"[\s_.-]+", ".", name_key(value)).strip(".")
    if subject == "user":
        aliases = {
            "class.year": "education.year",
            "school.year": "education.year",
            "academic.year": "education.year",
            "education.grade": "education.year",
            "sınıf": "education.year",
            "sinif": "education.year",
            "response.language": "reply.language",
            "cevap.dili": "reply.language",
            "yanıt.dili": "reply.language",
            "yanit.dili": "reply.language",
        }
        key = aliases.get(key, key)
    return key


def keys(con, tenant, subject, predicate):
    subject = subject_key(subject)
    alias = con.execute(
        "SELECT canonical_key FROM identity_aliases WHERE tenant=? AND alias_key=?", (tenant, subject)
    ).fetchone()
    subject = alias[0] if alias else subject
    return subject, predicate_key(subject, predicate)


def project_keys(con, row):
    subject, predicate = keys(con, row["tenant"], row["subject"], row["predicate"])
    if row["subject_key"] != subject or row["predicate_key"] != predicate:
        con.execute(
            "UPDATE memories SET subject_key=?,predicate_key=? WHERE id=?", (subject, predicate, row["id"])
        )
    return subject, predicate
