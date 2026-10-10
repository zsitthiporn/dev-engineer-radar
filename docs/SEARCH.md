# Search now, vector later

Current scope: six curated public articles. Browser-side text search checks title,
summary, tags and full article sections, with topic/verdict filters. Queries can
be shared through URL parameters. No backend, embedding service, new dependency
or database is needed for this small corpus. Thai matching uses substrings; it
does not infer synonyms or perform linguistic tokenization.

A vector index becomes useful if real queries need cross-language/synonym discovery
across a growing historical corpus. First collect a representative labeled query
set, compare lexical/tag baseline with hybrid retrieval and measure relevance,
latency and cost. Do not pick a database before that comparison.

An eventual index should be a rebuildable projection of approved public content:
chunk article sections; retain story ID, section heading, public URL, topic,
source date, review date, embedding model/version and content hash. Keep private
notes and signed URLs outside it. Filter by topic/date, combine exact product
matching with semantic ranking and return article/source references.

Vector similarity may propose `REVIEW` candidates for dedupe. It must not silently
collapse different versions, Preview→GA milestones or distinct capabilities.
Structured event identity and human review remain authoritative. JSONL/Git stay
the persistent source of truth; changing an embedding model never rewrites history.
