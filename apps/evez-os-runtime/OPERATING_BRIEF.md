# EVEZ OS Runtime Operating Brief

This branch reserves the repo-backed lineage path for the EVEZ OS runtime.

## State

- branch: feat/evez-os-runtime
- runtime target: apps/evez-os-runtime
- status: scaffold path created
- blocking condition: connector safety filters blocked code payload writes from chat

## Intended runtime

- dashboard for identity, runtime, distribution, conversion, delivery, memory
- mutation intake form
- mutation ledger
- capital object tables
- lineage view
- next-mutation queue

## Core law

prompt -> mutation -> asset -> payment/proof/state -> reuse

## Next step

Land the React/Vite app files into this branch from a tool surface that permits code payload writes, then import this folder into Vercel.
