# EVEZ Negative Space Runtime

The negative-space layer is the accumulator underneath the answer.

It records unresolved boundaries instead of allowing the model to forget them between prompts.

Every frontier object contains statement, evidence_refs, falsifier, next_experiment, and source_hash. The source_hash is the SHA-256 provenance value for the audit text that produced the frontier.

Latent authoring transforms the frontier into a constrained work packet:

frontier -> question -> instrument -> experiment -> result -> revision

It must never transform:

frontier -> assumption -> fact

Correct long-term behavior:

unknown_0 -> tested_unknown_1 -> partial_knowledge -> new_unknown

The frontier can grow even when the system succeeds because every resolution exposes a successor boundary.
