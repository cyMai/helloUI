# Design decision records

Use `design/decisions/YYYY-MM-DD-short-topic.md` for changes likely to be revisited: navigation model, responsive transformation, token semantics, interaction pattern, or a deliberate exception. Skip records for routine copy or spacing fixes.

Each record should contain:

```markdown
# Decision title

Date: YYYY-MM-DD
Status: proposed | accepted | superseded
Scope: affected surfaces/components

## Context
What changed and why the previous rule no longer fits.

## Decision
The chosen rule, including mobile and desktop behavior where relevant.

## Consequences
Affected screens, components, tokens, accessibility, migration, and verification.

## Alternatives
Only credible alternatives and why they were not chosen.
```

Link the accepted record from the relevant canonical rule. When superseding, add a link to the successor and update the canonical spec in the same change. Never use a historical record as the active rule.
