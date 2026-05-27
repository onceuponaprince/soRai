---
name: {{NAME}}
description: {{DESCRIPTION}}
---

# {{NAME}}

Generate written content one {{TYPE_NOUN}} at a time, then route the result through the configured sink. Shape the caller's material; never invent context, metrics, quotes, or outcomes.

## Required Inputs

1. Content type: one of {{CONTENT_TYPES}}. See `{{TYPE_SPEC_FILE}}`.
2. Raw context: what happened or what source material should be shaped.
3. Target platforms: comma-separated. Defaults per type live in `{{TYPE_SPEC_FILE}}`.
4. Mode: `stage` routes to the sink; `dry-run` shows output only.

If required input is missing, ask one clarifying question before generating.

## Voice

{{VOICE_INSTRUCTION}}

{{GRAPH_QUERY_SECTION}}
## Workflow

Follow `pipeline.md` exactly.

## Quality Gates

Before routing, check the {{TYPE_NOUN}} against `references/quality-checklist.md`. Failed gates are fixed before routing.

## Sink

{{SINK_SECTION}}

## Metadata

Machine-readable discovery metadata is available in `frontmatter.yaml`.

---
content-engine v{{VERSION}} · profile: {{NAME}}
