# Portfolio and interview evidence

## Project description

**Cabin Atlas — onboard passenger experience and aircraft-aware service platform**

Built an independent React/FastAPI cabin-edge application combining local entertainment playback, explainable duration-aware recommendations and flight-scoped service operations. Developed configurable aircraft layout snapshots, transactional quantity reservations, retry deduplication, cancellation refunds, crew ownership and auditable stock replenishment. Hardened session handling with revocation, hashed booking credentials, memory-only bearer state, protected media grants and negative cross-seat/cross-flight authorization tests.

Use only verified claims. Do not describe this as Panasonic software, airline-certified, breach-proof, a production airline deployment, or a trained recommendation model with measured passenger engagement. There is no guarantee that a particular company will hire you.

## Interview walkthrough

1. Explain the deployment problem: local network, shared terminals, variable cabin geometry, changing supply counts and limited flight time.
2. Show a configured narrow-body and a mixed-cabin wide-body. Explain explicit seat blocks and immutable flight snapshots.
3. Play a local video with captions and audio composition. Show optional position saving, a crew announcement interruption and history deletion.
4. Change interests and available time. Explain sparse TF-IDF, cosine similarity, MMR and exact optimisation over a bounded shortlist; state that weights are not trained engagement predictions.
5. Send two concurrent identical requests. Explain why stock, receipt and task insertion share a transaction. Show pending cancellation refunds once and crew ownership prevents conflicting completion.
6. Demonstrate negative authorization tests, media range responses, session revocation and production-container startup evidence.
7. Discuss the next supplier integration honestly: approved identity/seat binding, player/PA APIs, hardware rack validation, licensed media and independent security review.

## Evidence to present

Link the latest successful GitHub Actions run, the browser screenshots artifact, tests for fleet/inventory isolation and recommendations, the provisioning schema and security threat model. Performance and ranking-quality claims require target-hardware measurements and consented relevance data; do not invent them from correctness fixtures.
