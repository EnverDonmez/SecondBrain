# Source Registry

27 Ekim 2026: [36 depoluk araştırmanın](reports/research-20261026/SECOND_BRAIN_ARASTIRMA_RAPORU.md) uygulamaya yansıması [ADR 0004](docs/adr/0004-evidence-before-expansion.md) içinde kayıtlıdır. memU/Titen/OpenViking/Basic Memory tasarım referansıdır; kodları kopyalanmadı, paketleri runtime'a eklenmedi. Yeni üçüncü taraf bağımlılığı yoktur. Bu turdaki davranış ve ölçüm kanıtı [mühendislik raporundadır](reports/engineering-20261027/ENGINEERING_REPORT.md).

Araştırma kanıtı ile çalıştırılan dependency birbirinden ayrılır. Aşağıdaki HEAD snapshot SHA'ları research snapshot'ıdır; kurulan wheel'in o commit olduğu iddia edilmez. Runtime sürümleri `requirements.lock` ile, yayımlanmış artifact hash'leri `reports/package-release-hashes.json` ile sabittir.

Kontrol zamanı: 2026-10-26T07:20:39.414310+00:00

## Upstream değerlendirmesi

| Proje / sabit kaynak | Son release referansı | Lisans kanıtı | Karar |
|---|---|---|---|
| [Hindsight](https://github.com/vectorize-io/hindsight/tree/fa359876bcf5ed652c001dac5d40bfcc51d1d41d) · `fa359876bcf5ed652c001dac5d40bfcc51d1d41d` | integrations/openclaw/v1.2.0, integrations/openclaw/v1.1.1 | [MIT (dosya metni)](https://github.com/vectorize-io/hindsight/blob/fa359876bcf5ed652c001dac5d40bfcc51d1d41d/LICENSE) | Reflection adayı; ek servis/LLM ve aynı corpus benchmark'ı yok, runtime'a eklenmedi. |
| [Mem0](https://github.com/mem0ai/mem0/tree/2c81af3bbe27d9bccb09c772d583df9e9be72ee5) · `2c81af3bbe27d9bccb09c772d583df9e9be72ee5` | v2.2.1, ts-v3.3.1 | [Apache-2.0 (dosya metni)](https://github.com/mem0ai/mem0/blob/2c81af3bbe27d9bccb09c772d583df9e9be72ee5/LICENSE) | Gerçek yerel projection kullanıldı; infer=False, telemetri kapalı, canonical authority korunuyor. |
| [Supermemory](https://github.com/supermemoryai/supermemory/tree/f355dc80396ff8e5fccc36b774ddd22b0e19cd05) · `f355dc80396ff8e5fccc36b774ddd22b0e19cd05` | server-v0.0.9, server-v0.0.9-rc.3 | [MIT (dosya metni)](https://github.com/supermemoryai/supermemory/blob/f355dc80396ff8e5fccc36b774ddd22b0e19cd05/LICENSE) | Açık repo ile ayrı sunucu binary lisansı ayrıldı; binary kurulmadı. |
| [MemOS](https://github.com/MemTensor/MemOS/tree/adcb9f270c982f2b9ff8db9714792829d3bd6ab8) · `adcb9f270c982f2b9ff8db9714792829d3bd6ab8` | v2.0.34, memos-local-plugin-v2.0.20 | [Apache-2.0 (dosya metni)](https://github.com/MemTensor/MemOS/blob/adcb9f270c982f2b9ff8db9714792829d3bd6ab8/LICENSE) | Geniş taxonomy/procedural referans; auth düzeltmesi bağımsız doğrulanmadan çalıştırılmadı. |
| [memU](https://github.com/NevaMind-AI/memU/tree/42ef9fa3a8034f5817684cba23ef69fa70a58197) · `42ef9fa3a8034f5817684cba23ef69fa70a58197` | v2.0.0-beta.0, v1.5.1 | [Apache-2.0 (dosya metni)](https://github.com/NevaMind-AI/memU/blob/42ef9fa3a8034f5817684cba23ef69fa70a58197/LICENSE.txt) | Skill distillation/file memory referansı; otomatik güvenilir kural üretimi benimsenmedi. |
| [LangMem](https://github.com/langchain-ai/langmem/tree/48e3c11f5bb527282c7d5339c6a87a0b35abccfc) · `48e3c11f5bb527282c7d5339c6a87a0b35abccfc` | Release tag doğrulanmadı | [MIT (dosya metni)](https://github.com/langchain-ai/langmem/blob/48e3c11f5bb527282c7d5339c6a87a0b35abccfc/LICENSE) | Procedure optimization referansı; mevcut yerel reflection yerine zorunlu LangGraph kurulmadı. |
| [Letta](https://github.com/letta-ai/letta/tree/8816d3a8516893bfdc0fa14bfb1235226012e295) · `8816d3a8516893bfdc0fa14bfb1235226012e295` | 0.16.8, 0.16.7 | [Apache-2.0 (dosya metni)](https://github.com/letta-ai/letta/blob/8816d3a8516893bfdc0fa14bfb1235226012e295/LICENSE) | Agent runtime'a kilitlenmemek için referans olarak kaldı. |
| [MIRIX](https://github.com/Mirix-AI/MIRIX/tree/8cb06a62bbb7c478beb33dd4f2815696a72df482) · `8cb06a62bbb7c478beb33dd4f2815696a72df482` | graph_revision_pre_squash, v0.1.6 | [Apache-2.0 (dosya metni)](https://github.com/Mirix-AI/MIRIX/blob/8cb06a62bbb7c478beb33dd4f2815696a72df482/LICENSE) | Multimodal fikirler incelendi; sürekli ekran capture açık izinsiz etkinleştirilmedi. |
| [Honcho](https://github.com/plastic-labs/honcho/tree/39a53549cb269607dd63fe6a4fc90944efb774dc) · `39a53549cb269607dd63fe6a4fc90944efb774dc` | v3.4.1, v3.4.0 | [AGPL-3.0 (dosya metni)](https://github.com/plastic-labs/honcho/blob/39a53549cb269607dd63fe6a4fc90944efb774dc/LICENSE) | İlişkisel user-model yaklaşımı; ayrı runtime/lisans ve canonical ownership nedeniyle seçilmedi. |
| [Memori](https://github.com/MemoriLabs/Memori/tree/574b1ea3e876f100ef82c37817d603eb7e258e59) · `574b1ea3e876f100ef82c37817d603eb7e258e59` | v3.3.6, v3.3.5 | [Apache-2.0 (dosya metni)](https://github.com/MemoriLabs/Memori/blob/574b1ea3e876f100ef82c37817d603eb7e258e59/LICENSE) | SQL açıklanabilirliği referansı; ikinci kanonik veritabanı eklenmedi. |
| [OmniMem](https://github.com/richarvey/OmniMem/tree/00ca2c12b55edff57f49d82b660829d13e47726e) · `00ca2c12b55edff57f49d82b660829d13e47726e` | dev-v7.0.x, v7.0.3 | [MIT (dosya metni)](https://github.com/richarvey/OmniMem/blob/00ca2c12b55edff57f49d82b660829d13e47726e/LICENSE) | Experience/failure ve propose-accept yaklaşımı özgün learning gate'e yansıtıldı; kod kopyalanmadı. |
| [Graphiti](https://github.com/getzep/graphiti/tree/5c27edfa8d3e0f49b2571bcebb4261bcc89ee037) · `5c27edfa8d3e0f49b2571bcebb4261bcc89ee037` | v0.31.2, mcp-v1.1.3 | [Apache-2.0 (dosya metni)](https://github.com/getzep/graphiti/blob/5c27edfa8d3e0f49b2571bcebb4261bcc89ee037/LICENSE) | Temporal projection adayı; graph backend/LLM yapılandırılmadığı için blocked. |
| [Cognee](https://github.com/topoteretes/cognee/tree/37f788bd287750e10d7610173e5332b3843f6ebd) · `37f788bd287750e10d7610173e5332b3843f6ebd` | v1.6.6rc1, v1.6.5 | [Apache-2.0 (dosya metni)](https://github.com/topoteretes/cognee/blob/37f788bd287750e10d7610173e5332b3843f6ebd/LICENSE) | Belge/knowledge graph adayı; canonical bitemporal authority olarak kullanılmadı. |
| [GraphRAG](https://github.com/microsoft/graphrag/tree/c600ff80b77b9b62c47d539a3ac9569e95d8949b) · `c600ff80b77b9b62c47d539a3ac9569e95d8949b` | v3.3.0, v3.2.0 | [MIT (dosya metni)](https://github.com/microsoft/graphrag/blob/c600ff80b77b9b62c47d539a3ac9569e95d8949b/LICENSE) | Corpus/global reasoning adayı; basit kişisel retrieval için ek LLM maliyeti etkinleştirilmedi. |
| [LightRAG](https://github.com/HKUDS/LightRAG/tree/aaebfe1bb8d55deb6a4304d357a3bf4c92fcd40a) · `aaebfe1bb8d55deb6a4304d357a3bf4c92fcd40a` | temp, v1.5.7 | [MIT (dosya metni)](https://github.com/HKUDS/LightRAG/blob/aaebfe1bb8d55deb6a4304d357a3bf4c92fcd40a/LICENSE) | Graph+vector referansı; baseline'a ek kazanım ölçülmediğinden zorunlu runtime değil. |
| [HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG/tree/d5c8329422e0a0b834a15874545cb6a74b4f9b26) · `d5c8329422e0a0b834a15874545cb6a74b4f9b26` | v1.0.0 | [MIT (dosya metni)](https://github.com/OSU-NLP-Group/HippoRAG/blob/d5c8329422e0a0b834a15874545cb6a74b4f9b26/LICENSE) | Associative multi-hop retrieval adayı; aynı corpus üzerinde test edilmedi. |
| [A-MEM](https://github.com/agiresearch/A-mem/tree/ceffb860f0712bbae97b184d440df62bc910ca8d) · `ceffb860f0712bbae97b184d440df62bc910ca8d` | Release tag doğrulanmadı | [MIT (dosya metni)](https://github.com/agiresearch/A-mem/blob/ceffb860f0712bbae97b184d440df62bc910ca8d/LICENSE) | Zettelkasten linking fikri; canonical truth ve owner approval yerine geçirilmedi. |
| [KAG](https://github.com/OpenSPG/KAG/tree/fdab15b3929d2ee40dfcdd388f90233096a6afc9) · `fdab15b3929d2ee40dfcdd388f90233096a6afc9` | v0.8.0, v0.7.1 | [Apache-2.0 (dosya metni)](https://github.com/OpenSPG/KAG/blob/fdab15b3929d2ee40dfcdd388f90233096a6afc9/LICENSE) | Ontology/logical retrieval adayı; kişisel şema için ağır ek runtime seçilmedi. |
| [EverOS](https://github.com/EverMind-AI/EverOS/tree/5b0979b1b7f3a0cbe235756ff098515ec490753e) · `5b0979b1b7f3a0cbe235756ff098515ec490753e` | v1.5.1, v1.5.0 | [Apache-2.0 (dosya metni)](https://github.com/EverMind-AI/EverOS/blob/5b0979b1b7f3a0cbe235756ff098515ec490753e/LICENSE) | Okunabilir arşiv ve rebuildable index fikri; özgün event/vault çekirdeği geliştirildi. |
| [ReMe](https://github.com/agentscope-ai/ReMe/tree/cd3cbbadd84b533229aebba8003590d863224336) · `cd3cbbadd84b533229aebba8003590d863224336` | v0.4.2.0, v0.4.1.13 | [Apache-2.0 (dosya metni)](https://github.com/agentscope-ai/ReMe/blob/cd3cbbadd84b533229aebba8003590d863224336/LICENSE) | File-as-memory/consolidation referansı; filtrelenmiş session kaydı lossless archive sayılmadı. |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory/tree/8dcfcb3c50fde49205f703cfacb95b1f9a823fde) · `8dcfcb3c50fde49205f703cfacb95b1f9a823fde` | v0.24.1, v0.24.0 | [AGPL-3.0 (dosya metni)](https://github.com/basicmachines-co/basic-memory/blob/8dcfcb3c50fde49205f703cfacb95b1f9a823fde/LICENSE) | Markdown/MCP referansı; AGPL kod runtime'a entegre edilmedi. |
| [OpenViking](https://github.com/volcengine/OpenViking/tree/55e735769af639c87749a0516a34902e4d556ebb) · `55e735769af639c87749a0516a34902e4d556ebb` | v0.5.2, python-sdk@0.1.17 | [AGPL-3.0 (dosya metni)](https://github.com/volcengine/OpenViking/blob/55e735769af639c87749a0516a34902e4d556ebb/LICENSE) | Progressive disclosure/context namespace fikri; ayrı engine kurulmadı. |
| [Memvid](https://github.com/memvid/memvid/tree/e6bd9f7b9c38cd8d5370fa0fc936ac1dcd751813) · `e6bd9f7b9c38cd8d5370fa0fc936ac1dcd751813` | v2.0.140, v2.0.139 | [Apache-2.0 (dosya metni)](https://github.com/memvid/memvid/blob/e6bd9f7b9c38cd8d5370fa0fc936ac1dcd751813/LICENSE) | Portable artifact adayı; kendi backup/export biçimi kanonik kayıtların sahibi kaldı. |
| [Claude-Mem](https://github.com/thedotmack/claude-mem/tree/d9b36b66dc68da92af9df238e4c4debab587ba62) · `d9b36b66dc68da92af9df238e4c4debab587ba62` | v15.2.1, v15.2.0 | [Apache-2.0 (dosya metni)](https://github.com/thedotmack/claude-mem/blob/d9b36b66dc68da92af9df238e4c4debab587ba62/LICENSE) | Lifecycle capture tasarım referansı; HTTP/binary parçaları çalıştırılmadı. |
| [Agent Skills](https://github.com/agentskills/agentskills/tree/69ef37e9424c0a7ea9dd2293b559e43ec8176379) · `69ef37e9424c0a7ea9dd2293b559e43ec8176379` | Release tag doğrulanmadı | [Apache-2.0 (dosya metni)](https://github.com/agentskills/agentskills/blob/69ef37e9424c0a7ea9dd2293b559e43ec8176379/LICENSE) | Paket standardı benimsendi; upstream scriptler kopyalanmadı. |
| [rank-bm25](https://github.com/dorianbrown/rank_bm25/tree/47aa3ddf8dc1ebeb7ef4e65f2b4536af44594099) · `47aa3ddf8dc1ebeb7ef4e65f2b4536af44594099` | 0.2.2, 0.2.1 | [Apache-2.0 (dosya metni)](https://github.com/dorianbrown/rank_bm25/blob/47aa3ddf8dc1ebeb7ef4e65f2b4536af44594099/LICENSE) | Doğrudan kullanılan bağımsız BM25 implementasyonu. |
| [FastEmbed](https://github.com/qdrant/fastembed/tree/b105723f06ae0c1814dea6557637068cb77463c3) · `b105723f06ae0c1814dea6557637068cb77463c3` | v0.9.1, v0.9.1-gpu | [Apache-2.0 (dosya metni)](https://github.com/qdrant/fastembed/blob/b105723f06ae0c1814dea6557637068cb77463c3/LICENSE) | Doğrudan kullanılan ONNX CPU embedding katmanı. |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk/tree/a525a3d9bece967d91534b746a6c842931b7b4ec) · `a525a3d9bece967d91534b746a6c842931b7b4ec` | v2.3.0, v2.2.0 | [MIT (dosya metni)](https://github.com/modelcontextprotocol/python-sdk/blob/a525a3d9bece967d91534b746a6c842931b7b4ec/LICENSE) | Doğrudan kullanılan gerçek stdio protocol server/client. |
| [FastAPI](https://github.com/fastapi/fastapi/tree/7a0a3f0b286c6c865cf4398ea0e957a87b8bffa4) · `7a0a3f0b286c6c865cf4398ea0e957a87b8bffa4` | 0.162.0, 0.161.1 | [MIT (dosya metni)](https://github.com/fastapi/fastapi/blob/7a0a3f0b286c6c865cf4398ea0e957a87b8bffa4/LICENSE) | Doğrudan kullanılan yerel HTTP gateway ve Pydantic sözleşmeleri. |
| [Uvicorn](https://github.com/Kludex/uvicorn/tree/9d81c12a2c411d3bf104368472b708a3218d9b4e) · `9d81c12a2c411d3bf104368472b708a3218d9b4e` | 0.54.0, 0.53.0 | [BSD ailesi (tam metne bak)](https://github.com/Kludex/uvicorn/blob/9d81c12a2c411d3bf104368472b708a3218d9b4e/LICENSE.md) | Doğrudan kullanılan loopback ASGI sunucusu. |
| [Codex](https://github.com/openai/codex/tree/970111f6cb62cc02fe36a82ea7d71b37a2889c97) · `970111f6cb62cc02fe36a82ea7d71b37a2889c97` | rust-v0.165.0-alpha.1, rust-v0.164.0 | [Apache-2.0 (dosya metni)](https://github.com/openai/codex/blob/970111f6cb62cc02fe36a82ea7d71b37a2889c97/LICENSE) | Resmi hook/App Server/MCP kaynak referansı; kullanıcı thread'leri okunmadı. |
| [Reflexion](https://github.com/noahshinn/reflexion/tree/218cf0ef1df84b05ce379dd4a8e47f17766733a0) · `218cf0ef1df84b05ce379dd4a8e47f17766733a0` | Release tag doğrulanmadı | [MIT (dosya metni)](https://github.com/noahshinn/reflexion/blob/218cf0ef1df84b05ce379dd4a8e47f17766733a0/LICENSE) | Feedback→lesson fikri; research code kullanılmadı. |
| [ExpeL](https://github.com/LeapLabTHU/ExpeL/tree/e41ec9a24823e7b560c561ab191441b56d9bcefc) · `e41ec9a24823e7b560c561ab191441b56d9bcefc` | Release tag doğrulanmadı | [Apache-2.0 (dosya metni)](https://github.com/LeapLabTHU/ExpeL/blob/e41ec9a24823e7b560c561ab191441b56d9bcefc/LICENSE) | Biriken evidence→insight fikri; research code kullanılmadı. |
| [Voyager](https://github.com/MineDojo/Voyager/tree/55e45a880755d0c8c66ca7fb5fe7962ac8974f89) · `55e45a880755d0c8c66ca7fb5fe7962ac8974f89` | Release tag doğrulanmadı | [MIT (dosya metni)](https://github.com/MineDojo/Voyager/blob/55e45a880755d0c8c66ca7fb5fe7962ac8974f89/LICENSE) | Skill library/verifier fikri; oyun/runtime kurulmadı. |
| [MemPalace](https://github.com/MemPalace/mempalace/tree/84582fb055a6429261f9c779da86c0561ec80adc) · `84582fb055a6429261f9c779da86c0561ec80adc` | v3.11.0, v3.10.0 | [MIT (dosya metni)](https://github.com/MemPalace/mempalace/blob/84582fb055a6429261f9c779da86c0561ec80adc/LICENSE) | Verbatim/mining adayı; upstream kimliği güncel resmi depo ile düzeltildi, benchmark reprodüksiyonu yapılmadı. |
| [TencentDB Agent Memory](https://github.com/TencentCloud/TencentDB-Agent-Memory/tree/6a4bb55ea54834d8265ce52024d3e3c75db30d38) · `6a4bb55ea54834d8265ce52024d3e3c75db30d38` | v2.0.3-beta.1, v2.0.2 | [MIT (dosya metni)](https://github.com/TencentCloud/TencentDB-Agent-Memory/blob/6a4bb55ea54834d8265ce52024d3e3c75db30d38/LICENSE) | Chat/Skill/Wiki/Code-Graph varlık ayrımı referansı; takım servisi kurulmadı. |
| [RapidOCR](https://github.com/RapidAI/RapidOCR/tree/80b427d69bfc5b91a12913394875910296c6f315) · `80b427d69bfc5b91a12913394875910296c6f315` | v5.0.0a5, v5.0.0a4 | [Apache-2.0 (dosya metni)](https://github.com/RapidAI/RapidOCR/blob/80b427d69bfc5b91a12913394875910296c6f315/LICENSE) | Gerçek yerel CPU ONNX OCR; üretilmiş görsel ve taranmış PDF üzerinde test edildi. |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper/tree/9e472ae9de8bb374552f531f752654554b76b2d6) · `9e472ae9de8bb374552f531f752654554b76b2d6` | v1.2.1, v1.2.0 | [MIT (dosya metni)](https://github.com/SYSTRAN/faster-whisper/blob/9e472ae9de8bb374552f531f752654554b76b2d6/LICENSE) | Gerçek tiny/int8 CPU konuşma dökümü; sentetik TTS üzerinde ağsız test edildi. |
| [PyAV](https://github.com/PyAV-Org/PyAV/tree/b9adc02c92ac67406e0c174373493eb9a2181caf) · `b9adc02c92ac67406e0c174373493eb9a2181caf` | v19.0.2, v19.0.1 | [BSD ailesi (tam metne bak)](https://github.com/PyAV-Org/PyAV/blob/b9adc02c92ac67406e0c174373493eb9a2181caf/LICENSE.txt) | Sabit container allowlist'i ile yerel ses decode ve video kare örnekleme; FFmpeg binary notices ayrıca envanterde. |
| [pypdfium2](https://github.com/pypdfium2-team/pypdfium2/tree/21fa91a05007e06d13c76c86f2fc39f6e9d2cc43) · `21fa91a05007e06d13c76c86f2fc39f6e9d2cc43` | 5.14.0, 5.14.0b1 | [Dosya doğrulanamadı](https://github.com/pypdfium2-team/pypdfium2/blob/21fa91a05007e06d13c76c86f2fc39f6e9d2cc43/LICENSE) | Taranmış PDF sayfalarının yerel render'ı; PDFium ve bundled bağımlılık notices korunur. |

## Kurulu paketler

Tam transitif metadata, gereksinimler ve license dosya SHA-256 değerleri `reports/source-registry.json` içindedir. Orijinal kurulu lisans metinleri `third_party/licenses/` altında korunur. PyPI release hash kaydı indirilen her wheel'in yerelde yeniden hash'lenmesi yerine geçmez.

| Paket | Sabit sürüm | Dağıtım metadata'sındaki lisans | Saklanan lisans dosyası |
|---|---|---|---|
| annotated-doc | 0.0.5 | MIT | 1 |
| annotated-types | 0.8.0 | MIT | 1 |
| anyio | 4.15.1 | MIT | 1 |
| ast_serialize | 0.13.1 | MIT | 2 |
| attrs | 26.1.0 | MIT | 1 |
| av | 19.0.2 | BSD-3-Clause | 4 |
| backoff | 2.2.1 | MIT | 1 |
| boolean.py | 5.0 | BSD-2-Clause | 3 |
| CacheControl | 0.14.4 | Apache-2.0 | 1 |
| certifi | 2026.10.23 | MPL-2.0 | 1 |
| cffi | 2.1.1 | MIT-0 | 1 |
| charset-normalizer | 3.5.2 | MIT | 1 |
| click | 8.5.0 | BSD-3-Clause | 1 |
| colorama | 0.4.6 | Belirtilmemiş; dosyayı incele | 1 |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | 3 |
| ctranslate2 | 4.8.4 | MIT | 0 |
| cyclonedx-python-lib | 11.12.0 | Apache-2.0 | 2 |
| defusedxml | 0.7.1 | PSFL | 1 |
| distro | 1.9.0 | Apache License, Version 2.0 | 1 |
| fastapi | 0.162.0 | MIT | 1 |
| fastembed | 0.9.1 | Apache-2.0 | 2 |
| faster-whisper | 1.2.1 | MIT | 1 |
| filelock | 4.2.4 | MIT | 1 |
| flatbuffers | 25.12.19 | Apache 2.0 | 0 |
| fsspec | 2026.9.0 | BSD-3-Clause | 1 |
| grpcio | 1.84.1 | Apache-2.0 | 1 |
| h11 | 0.16.0 | MIT | 1 |
| h2 | 4.4.1 | MIT | 1 |
| hf-xet | 1.7.0 | Apache-2.0 | 1 |
| hpack | 4.2.0 | MIT | 1 |
| httpcore | 1.0.9 | BSD-3-Clause | 1 |
| httpcore2 | 2.16.0 | BSD-3-Clause | 1 |
| httpx | 0.28.1 | BSD-3-Clause | 1 |
| httpx2 | 2.16.0 | BSD-3-Clause | 1 |
| huggingface_hub | 1.33.0 | Apache-2.0 | 1 |
| hyperframe | 6.1.0 | The MIT License (MIT) | 1 |
| hypothesis | 6.170.11 | MPL-2.0 | 1 |
| idna | 3.20 | BSD-3-Clause | 1 |
| iniconfig | 2.3.1 | MIT | 1 |
| jiter | 0.18.0 | MIT | 1 |
| jsonschema | 4.26.0 | MIT | 1 |
| jsonschema-specifications | 2025.9.1 | MIT | 1 |
| librt | 0.16.0 | MIT | 1 |
| license-expression | 30.4.4 | Apache-2.0 | 11 |
| loguru | 0.7.3 | Belirtilmemiş; dosyayı incele | 0 |
| lxml | 6.1.3 | BSD-3-Clause | 2 |
| markdown-it-py | 4.2.0 | Belirtilmemiş; dosyayı incele | 2 |
| mcp | 2.3.0 | MIT | 1 |
| mcp-types | 2.3.0 | MIT | 1 |
| mdurl | 0.1.2 | Belirtilmemiş; dosyayı incele | 1 |
| mem0ai | 2.2.1 | Apache-2.0 | 1 |
| mmh3 | 5.3.1 | MIT License | 1 |
| msgpack | 1.2.3 | Apache-2.0 | 1 |
| mypy | 2.4.0 | MIT | 2 |
| mypy_extensions | 1.1.0 | MIT | 1 |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | 17 |
| onnxruntime | 1.31.0 | MIT License | 0 |
| openai | 3.37.0 | Apache-2.0 | 1 |
| opencv-python | 5.0.0.93 | Apache 2.0 | 2 |
| opentelemetry-api | 1.45.1 | Apache-2.0 | 1 |
| packageurl-python | 0.17.6 | MIT | 0 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | 3 |
| pathspec | 1.1.1 | Belirtilmemiş; dosyayı incele | 1 |
| pillow | 13.0.0 | MIT-CMU | 1 |
| pip | 26.2.2 | MIT | 22 |
| pip-requirements-parser | 32.0.1 | MIT | 1 |
| pip_api | 0.0.35 | Apache License | 1 |
| pip_audit | 2.10.1 | Belirtilmemiş; dosyayı incele | 1 |
| platformdirs | 4.13.5 | MIT | 1 |
| pluggy | 1.7.0 | MIT | 1 |
| portalocker | 4.4.1 | BSD-3-Clause | 1 |
| posthog | 7.75.11 | MIT | 1 |
| protobuf | 6.33.6 | 3-Clause BSD License | 1 |
| py-serializable | 2.1.0 | Apache-2.0 | 1 |
| py_rust_stemmers | 0.1.8 | Belirtilmemiş; dosyayı incele | 1 |
| pyclipper | 1.4.0 | MIT | 1 |
| pycparser | 3.12 | BSD-3-Clause | 1 |
| pydantic | 2.14.1 | MIT | 1 |
| pydantic_core | 2.50.1 | MIT | 1 |
| Pygments | 2.21.0 | BSD-2-Clause | 2 |
| PyJWT | 2.15.1 | MIT | 2 |
| pyparsing | 3.3.3 | MIT | 1 |
| pypdf | 6.21.2 | BSD-3-Clause | 1 |
| pypdfium2 | 5.14.0 | BSD-3-Clause, Apache-2.0, dependency licenses | 18 |
| pytest | 9.1.1 | MIT | 1 |
| python-docx | 1.2.0 | MIT | 1 |
| python-multipart | 0.0.32 | Apache-2.0 | 1 |
| pytz | 2026.5 | MIT | 1 |
| pywin32 | 312 | PSF | 8 |
| PyYAML | 6.0.3 | MIT | 1 |
| qdrant-client | 1.20.0 | Apache-2.0 | 1 |
| rank-bm25 | 0.2.2 | Apache2.0 | 1 |
| rapidocr-onnxruntime | 1.4.4 | Apache-2.0 | 0 |
| referencing | 0.37.0 | MIT | 1 |
| requests | 2.34.2 | Apache-2.0 | 2 |
| rich | 15.0.0 | MIT | 1 |
| rpds-py | 2026.9.1 | MIT | 1 |
| ruff | 0.17.2 | MIT | 1 |
| second-brain-os | 0.1.0 | Apache-2.0 | 3 |
| setuptools | 84.2.1 | MIT | 15 |
| shapely | 2.2.0 | BSD-3-Clause | 3 |
| six | 1.17.0 | MIT | 1 |
| sniffio | 1.3.1 | MIT OR Apache-2.0 | 3 |
| sortedcontainers | 2.4.0 | Apache 2.0 | 1 |
| SQLAlchemy | 2.1.6 | MIT | 2 |
| sse-starlette | 3.6.0 | BSD-3-Clause | 2 |
| starlette | 1.10.0 | BSD-3-Clause | 1 |
| tokenizers | 0.23.3 | Belirtilmemiş; dosyayı incele | 0 |
| tomli | 2.5.0 | MIT | 1 |
| tomli_w | 1.2.0 | Belirtilmemiş; dosyayı incele | 1 |
| tqdm | 4.70.1 | MPL-2.0 AND MIT | 1 |
| truststore | 0.10.5 | MIT | 1 |
| typing-inspection | 0.4.4 | MIT | 1 |
| typing_extensions | 4.16.0 | PSF-2.0 | 1 |
| urllib3 | 2.8.0 | MIT | 1 |
| uvicorn | 0.54.0 | BSD-3-Clause | 1 |
| wheel | 0.48.0 | MIT | 1 |
| win32_setctime | 1.2.1 | MIT license | 1 |

## Model ve standartlar

Embedding modelinin gerçek snapshot ve dosya SHA-256 kayıtları `reports/model-manifest.json`, Whisper tiny ağırlıklarının revision ve SHA-256 kayıtları `reports/speech-model-manifest.json` içindedir. OCR ONNX dosyaları rapidocr-onnxruntime wheel'iyle gelir. Model kartı iddiaları bağımsız kalite benchmark'ı sayılmadı; gerçek yerel testlerin kapsamı TESTING.md ve MEDIA_PIPELINE.md içindedir.

[Codex hooks](https://learn.chatgpt.com/docs/hooks), [App Server](https://learn.chatgpt.com/docs/app-server), [MCP](https://learn.chatgpt.com/docs/extend/mcp), [Claude hooks](https://code.claude.com/docs/en/hooks), [Gemini hooks](https://geminicli.com/docs/hooks/), [Cursor hooks](https://cursor.com/docs/hooks) entegrasyon yüzeyleri için resmi kaynaklardır. Canlı hesap erişimi bu belgelerin bulunmasından çıkarılmadı.

Open Brain/OneBrain/Engram/Hippocampus gibi birden fazla projeye işaret edebilen isimler tek runtime bağımlılığına dönüştürülmedi. ProcMEM, LongMemEval/V2, LoCoMo, Memora/FAMA, SkillsBench, AFTER, SkillEvolBench ve MemLens araştırma yaklaşımı olarak değerlendirildi; dataset/code lisans ve yerel reprodüksiyonları bu teslimde doğrulanmadı. Bu nedenle dış benchmark sonuçları bizim sonuçlarımız olarak sunulmaz.
