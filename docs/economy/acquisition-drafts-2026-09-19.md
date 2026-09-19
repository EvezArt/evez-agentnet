# EVEZ Acquisition Drafts — 2026-09-19

These are review-ready drafts derived from public observations. They are not submitted applications. No client identity, prior client result, certification, years-of-experience claim, or revenue claim is invented.

## 1. AI Automation Developer Needed — $2,500 fixed

Source: https://www.upwork.com/freelance-jobs/apply/Automation-Developer-Needed_~022099026929727803146/

Draft:

I build automation systems as software, not just prompt chains. My current work includes workflow orchestration, agent/tool boundaries, evidence and state tracking, API integrations, Python automation, and reliability checks.

Your scope maps directly to the parts I can demonstrate: lead/workflow state transitions, API-connected automation, validation, durable event records, and human approval gates for consequential actions.

I would start by taking one scoped workflow from intake to a verified working result, with explicit failure handling and a short handoff document. I would keep the implementation auditable so you can see what happened, what was inferred, and what still needs attention.

I can provide links to specific EVEZ/EvezArt repositories and code relevant to the exact workflow before any engagement. I would not claim client results that I cannot substantiate.

## 2. Python Automation / PDF / MySQL MVP — $600 fixed

Source: https://www.upwork.com/freelance-jobs/apply/Python-Automation-Developer-Email-Inbox-Ingestion-PDF-Parsing-MySQL-Pipeline-MVP_~022100648447821780212/

Draft:

The workflow you describe is a clean fit for evidence-bound Python automation: ingest the message, identify and deduplicate the attachment, extract structured fields, validate required fields, persist both result and processing state, export the target CSV, and route failures for manual review.

I would structure the MVP around deterministic boundaries between ingestion, extraction, validation, persistence, export, and notification. Each processing attempt would retain a message identifier and execution state so retries do not silently duplicate records.

For the AI extraction step, I would enforce a strict schema rather than trusting free-form model output. Missing or ambiguous required fields would remain FAILED/REVIEW rather than being guessed.

The deliverable would include the Python implementation, SQL schema, deployment instructions, and a focused test set covering duplicate messages, malformed PDFs, missing fields, extraction failures, and successful end-to-end processing.

## 3. Senior AI Agent Engineer / OpenClaw — $250 fixed

Source: https://www.upwork.com/freelance-jobs/apply/Senior-Agent-Engineer-for-Personal-Secretary_~022099840337367611062/

Draft:

I work on self-hosted agent infrastructure with explicit capability boundaries, persistent state, event provenance, human approval gates, and deployment/debugging workflows.

For this system I would treat the secretary as a stateful application rather than an unrestricted autonomous agent. WhatsApp, calendar, tasks, email drafting, memory, browser automation, and server tools would each have explicit permissions and observable state transitions. Sensitive actions would remain approval-gated as you requested.

I can show relevant EVEZ/EvezArt implementation work for agent orchestration, event-sourced state, workflow automation, and security hardening. I would keep the proposal grounded in code that can actually be inspected rather than making generic autonomous-agent claims.

## 4. Custom AI App / Agent / Automation — $25-$40/hr

Source: https://www.upwork.com/freelance-jobs/apply/Developer-for-Custom-App-Agent-Automation-Development_~022100903429471177177/

Draft:

I am interested in the engineering side of this rather than a chatbot-only implementation. I work across Python/JavaScript automation, APIs, agent workflows, databases, event/state tracking, testing, and deployment.

For a system combining an AI application, agent, and business-process automation, I would first establish the request/data flow and the external-system boundaries, then implement the smallest production path with structured outputs, retries, validation, observability, and explicit handling for actions that require user approval.

I can provide concrete EVEZ/EvezArt repository examples relevant to the requested stack and explain exactly which parts they demonstrate. I will not pad the application with unverifiable claims.
