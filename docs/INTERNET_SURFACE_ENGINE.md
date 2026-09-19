# Internet Surface Engine

The Internet is modeled as a set of observable surfaces, not as an object the agent possesses.

## Safety and epistemic limits

- Explicit domain allowlists are mandatory.
- Requests are read-oriented HTTP GET observations only.
- robots.txt is checked before observation.
- Redirects are bounded.
- Response size is bounded.
- Requests are rate-limited.
- Authentication is never inferred or bypassed.
- A blocked or unavailable surface is recorded as a boundary, not converted into a claim.
- Content hashes identify observed bytes; they do not establish truth.

## Runtime

`python tools/internet_surface.py --domain example.com https://example.com`

Results append to `docs/reality-observations.jsonl` and can be promoted into EVEZ/1 evidence only after independent verification.

Future capability layers can add browser rendering, authenticated connectors, search indexes, APIs, Git providers, and other surfaces as separately declared capabilities. Each must retain the same discovered -> declared -> permitted -> tested -> effective -> verified lifecycle.