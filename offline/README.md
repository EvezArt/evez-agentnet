# EVEZ Offline

A deliberately small local ChatGPT-style shell for a Samsung/Termux-class device.

The HTTP/UI layer is Python standard library only. It stores conversation history locally and calls a llama.cpp-compatible local endpoint when one is available. Without a model server it still runs and records messages, but it cannot honestly claim to generate model-quality answers.

## Run

From Termux:

    pkg install python
    cd ~/evez-agentnet/offline
    bash start.sh

Open:

    http://127.0.0.1:8787

Keep the server bound to 127.0.0.1. It is intentionally not an internet-facing service.

## Model layer

The runtime expects an OpenAI-compatible local endpoint at:

    http://127.0.0.1:8080/v1/chat/completions

That lets the same UI survive changes in the local inference engine. Use a small GGUF instruct model and a llama.cpp-compatible server. On a low-memory phone, start with a sub-1B to roughly 1.5B quantized model and short context. The model file, not this runtime, is the dominant storage/RAM cost.

Useful environment controls:

    EVEZ_LLAMA_URL=http://127.0.0.1:8080
    EVEZ_MODEL=local-gguf
    EVEZ_OFFLINE_HOME=~/.evez-offline

This runtime deliberately does not download a model automatically. That keeps the base install tiny and prevents a phone with limited storage from silently becoming a landfill of AI weights.

## Design

browser
  -> runtime.py
      -> local llama.cpp-compatible server
      -> local JSONL conversation record

No OpenRouter. No cloud API. No database. No Python web framework.

## Device-native presentation and watermarking

The browser surface is mobile-first and uses the device viewport, touch-safe controls, and viewport-fit=cover; it does not pretend the phone is a desktop terminal.

Every /chat response has two layers:

    answer       canonical unwatermarked content
    presentation visible output with watermark
    watermark    machine-readable provenance metadata

The watermark includes a local device label, a presentation ID, and the SHA-256 digest of the canonical artifact. The digest is computed before presentation text is appended, so the watermark cannot silently become part of the evidence it identifies.

The canonical conversation JSONL remains unwatermarked. association=PRESENTATION_ONLY is intentional.