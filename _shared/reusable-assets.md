# Reusable external inputs

This file registers approved external inputs that future Projects may reuse. It
is a catalog, not a second copy of their contents. Internal shared references
are routed by [`CONTEXT.md`](CONTEXT.md); blank artifacts live under
[`../_templates/`](../_templates/).

## Available now

None. No external inputs were registered at setup (2026-11-26). Add one when a
feature needs it, under the admission rule below.

## Admission rule

Add an input only when its canonical location, owner, intended use, access
constraints, and freshness expectations are known. Link it from the workflows
or Projects that need it; do not copy it into several Projects. Record only safe
access requirements and variable names. Never store credentials here.
