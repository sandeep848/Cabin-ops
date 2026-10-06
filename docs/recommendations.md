# Recommendation and journey planning

The useful problem is cold-start personalization on a cabin network: a passenger may have no account history, no internet connection and limited time before landing. The ranker uses local catalogue metadata and optional explicit interests rather than collecting a behavioural profile.

## Ranking

1. Reject excluded titles, unsupported media kinds, non-family catalogue entries and videos without captions when captions are required.
2. Compute a hard budget from the smaller of the passenger's chosen time and the crew's current landing estimate, leaving five minutes before landing.
3. Build sparse TF-IDF vectors from titles, descriptions, genres and tags. Compute cosine similarity with selected interests.
4. Combine metadata relevance (0.6), an explicit pace match (0.2), and an eligible-duration baseline (0.2).
5. Greedily select up to eight candidates using MMR: 0.8 times the metadata score minus 0.2 times maximum similarity to a selected title. Each result explains matching interests, pace and duration eligibility.

The weights are hand-selected policy values. They are not learned from passenger engagement, and scores are not probabilities. Empty preferences provide a diverse metadata-based cold start. There is no unsupported claim of recommendation accuracy or predicted satisfaction.

## Packing a journey

An exact 0/1 dynamic programme chooses at most four items from the eight-title shortlist, maximizing score plus a small per-title utility while obeying the duration budget. Each transition adds 15 seconds. The algorithm is exact for this bounded candidate set; it does not claim a globally optimal programme over a larger catalogue. Titles do not repeat. The UI invalidates a plan when preferences change and warns when the crew's landing estimate changes.

Playback starts only by passenger action. An announcement pauses the active player; reading it does not automatically resume playback. There is no real aircraft PA/SDK integration or DRM entitlement claim.

## Evidence and extension

Tests check hard budget limits across multiple windows, unique selections, exclusions, media-kind filters, taste-dependent ordering, exact transition accounting and the server-enforced landing buffer. Browser tests decode and play local audio/video rather than checking that a play button merely exists. These are correctness checks, not passenger-study results.

For production recommendation evaluation, obtain operator-approved, consented feedback with a documented train/test split, define relevance judgments, compare TF-IDF/MMR against popularity/random/content baselines, evaluate ranking/diversity/coverage and measure latency on target hardware. Do not report synthetic tests as NDCG, retention or customer satisfaction evidence. Collaborative filtering needs enough consented history; adding it before that data exists would fabricate sophistication.

Operators can set `CABIN_ATLAS_CATALOG_PATH` and `CABIN_ATLAS_MEDIA_DIR` to a mounted rights-cleared catalogue and media directory. Asset filenames are flat, validated names, each media asset requires a SHA-256 digest, and captioned videos require a local VTT file. The included catalogue contains original playable microfeatures and compositions under CC0, with reproducible source in `scripts/build_original_content.py` (Pillow and FFmpeg required only to rebuild assets). Commercial airline content requires separate licensing, entitlement, DRM and supplier player integration.
