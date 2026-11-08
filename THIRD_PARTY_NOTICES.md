# Third-party notices

The repository previously contained agent-only design and web-audit bundles. Their notices are preserved here after removing those non-product files.

### .agents/skills/design/NOTICE.md

# Notice

Design skill
Copyright 2025-2026 Paul Bakaus

This `design` skill vendors a focused subset of `pbakaus/impeccable` under a shorter skill name for Claude Code and Codex compatibility.

## Anthropic frontend-design Skill

The upstream `impeccable` skill builds on Anthropic's original frontend-design skill.

**Original work:** https://github.com/anthropics/skills/tree/main/skills/frontend-design
**Original license:** Apache License 2.0
**Copyright:** 2025 Anthropic, PBC

The upstream project extends the original with:
- 7 domain-specific reference files (typography, color-and-contrast, spatial-design, motion-design, interaction-design, responsive-design, ux-writing)
- 23 commands
- Expanded patterns and anti-patterns

## Typecraft Guide Skill

The `typography.md` reference in this project incorporates a set of tactical additions merged in from ehmo's `typecraft-guide-skill` at the author's request: dark-mode weight/tracking compensation, `font-display: optional` vs `swap`, preload-critical-weight-only guidance, variable fonts for 3+ weights, `clamp()` max-to-min ratio bound, responsive measure/container coupling, `text-wrap: balance` / `pretty`, `font-optical-sizing: auto`, ALL-CAPS tracking quantification, and the paragraph-rhythm rule (space OR indent, never both).

**Original work:** https://github.com/ehmo/typecraft-guide-skill
**Original license:** see upstream repo
**Author:** ehmo


### .agents/skills/web-ui-audit/NOTICE.md

This skill adapts material from:

- `vercel-labs/web-interface-guidelines`, commit `4e799d45c17aec1498c269287a83b9dba22b966b`, source: https://github.com/vercel-labs/web-interface-guidelines
- `vercel-labs/agent-skills`, path `skills/web-design-guidelines`, commit `b9c8ee0643d87d3c5a953d1e22382ff2ead39229`, source: https://github.com/vercel-labs/agent-skills/tree/main/skills/web-design-guidelines

The adapted material is used for a portable Claude Code and Codex skill layout with the checklist stored in `references/web-interface-guidelines.md`.
