# ADR 0001 — Kanonik çekirdek

Kabul: SQLite/WAL üzerinde olay + assertion registry; tüm motorlar projection. Tek vendor veritabanını truth yapmak reddedildi: lifecycle, provenance, deletion ve motor değişimi kontrolü kullanıcıda kalmalı. Ağır dağıtık altyapı tek kullanıcı için gereksiz bulundu. Tenant/scope sütunları geleceğe hazırlıktır; production SaaS desteği değildir.
