# ADR 0002 — Zaman ve silme

Kabul: valid/known eksenleri ve kaynak olay zamanı ayrı. Correction geçmişi ezmez. Hard erase için provenance closure, içerik/source hash tombstone'ları ve snapshot dışı write-ahead deletion ledger kullanılır. Shared original ZIP'i kısmi silinmiş gibi sunmak reddedildi; kapsam önizlemesiyle tüm ortak kaynak silinir. Yönetilen eski yedekler kaldırılır; unmanaged kopyalar için silme iddiası verilmez.
