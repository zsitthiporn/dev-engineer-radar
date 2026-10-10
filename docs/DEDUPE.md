# Dedupe contract

## Producer normalization

Use curated config/identity.yml aliases to identify the product. Set productKey
to the canonical kebab-case key and eventKey to a stable capability/event label.
Set version and milestone explicitly when relevant. The same keys work across
Thai and English headlines; a headline translation is not a new event.

Unicode NFKC, case folding and punctuation normalization handle superficial text
variation. C# and .NET get stable text normalization. Similarity compares event
wording within one product; it is a review signal, not a probability or proof.

## Decision order

1. Existing immutable ID: same identity is DUPLICATE; changed identity is REVIEW.
2. Same product/event/version/milestone anywhere in history: DUPLICATE.
3. Explicit parent: UPDATE only for a distinct development with primary evidence,
   changeSummary and materialChange; otherwise REVIEW.
4. Same event with a different version/milestone: REVIEW until update is evidenced.
5. Same normalized source URL: REVIEW, including different products.
6. Similar event text within the canonical product: REVIEW at review_threshold.
7. No match/review signal: NEW.

Exact matches are checked before parent/fuzzy matches. History order cannot turn
an already reported GA into a new update. Ties are deterministic. Different
versions cannot be silently dropped because a title looks similar.

URL normalization lowercases scheme/host, removes default ports, trailing slashes,
fragments and only known tracking parameters. Meaningful queries and parameter
order remain; HTTP and HTTPS are not conflated. Redirects are not fetched.

## Resolving REVIEW

Inspect the matched story and primary sources.

- Same event: omit the candidate; reuse its identity for dedupe.
- Genuine material development: create a new ID, updateOf and primary evidence;
  use coverage UPDATE and choose materialChange.
- Independent capability: keep coverage NEW and record dedupeReview containing
  matchedId, a substantive reason (at least 20 characters) and reviewedAt.

Changing spelling or an ID to evade a duplicate is invalid. Registry aliases
should be updated when a product has another name. Do not merge parent products
with distinct products such as GitHub Copilot CLI merely because names overlap.

## Material triggers

Use milestone, release, breaking-change, security, benchmark, adoption,
clarification, capability or performance. Assertions of materiality need a
source and a concrete explanation. The CLI checks metadata and distinct identity;
a producer must still verify the truth of the stated change.

## Known limits

This is deterministic structured semantic dedupe with conservative text matching.
It cannot guarantee paraphrase detection when keys are inconsistent, translate
arbitrary languages or independently verify a release's meaning. A new event
with an incorrectly invented eventKey can evade similarity. Curated aliases,
producer review, persisted rationales and immutable history are required.
No embeddings or external model endpoint is configured.
