# ADR 0003 — Yerel çalışma ve sağlayıcılar

Kabul: FastAPI + buildless browser UI, default FTS5, isteğe bağlı ONNX CPU embedding ve disposable Mem0. API anahtarı olmadan kritik akışlar çalışır. Next.js ayrı sunucu/build zinciri bu yerel sürümde ek yük bulundu. Cloud extraction varsayılanı reddedildi: kişisel veri aktarımı ve harcama için açık yetki yok. Yerel Ollama seam'i ayrı configuration gate taşır.
