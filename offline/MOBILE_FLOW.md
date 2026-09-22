# Mobile flow

This is the intended fourth-quarter path:

    Galaxy A16
        |
        +-- Termux
        |     |
        |     +-- llama-server
        |     |     +-- Qwen2.5 0.5B Instruct GGUF
        |     |     +-- CPU only
        |     |     +-- 2048 context
        |     |
        |     +-- EVEZ Offline runtime
        |           +-- localhost HTTP
        |           +-- JSONL conversation memory
        |           +-- no cloud API
        |
        +-- Chrome
              |
              +-- http://127.0.0.1:8787

The model is the expensive part. The UI/runtime is intentionally standard-library
Python and is only a few kilobytes of source. Once the model is downloaded, normal
chat requests do not require internet access.

The chosen official Qwen2.5-0.5B GGUF repository currently publishes Q3_K_M at about
432 MB and Q4_K_M at about 491 MB. Q3_K_M is the storage-first default here.
Q4_K_M can be selected manually if storage/RAM allows.

Do not expose either local server beyond 127.0.0.1 unless authentication and a
network boundary are deliberately added.

The local model is not equivalent to a frontier ChatGPT model. It is a compact
offline substitute with the same basic interaction flow: system context, recent
conversation, generation, and persistent local history.
