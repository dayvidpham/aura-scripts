# Leave Structured Review Comment

Leave structured feedback as RFC comment.

## When to Use

Documenting review findings for the permanent record.

## Given/When/Then/Should

**Given** findings **when** documenting **then** use structured format with severity levels **should never** leave unstructured feedback

**Given** comment **when** creating **then** get next ID from CLI **should never** guess comment IDs

## Steps

1. Get next ID: `npx tsx src/cli/aura.ts rfc next-id`
2. Create comment file
3. Use structured format

## File Location

`docs/{version}/rfc/comments/{NNN}__{slug}__{YYYY-MM-DD}.Rmd`

## Format

```markdown
# RFC Comment: {Perspective} Review - {Target}

**RFC:** {version}
**ID:** {NNN}
**Date:** {YYYY-MM-DD}
**Reviewer:** {perspective}-reviewer

## Review Summary
**Vote:** {VOTE}
**Confidence:** {0.0-1.0}

## Findings
### BLOCKING Issues
{list or "None"}
### MAJOR Issues
{list or "None"}
### MINOR Issues
{list or "None"}

## Conclusion
{assessment and next steps}
```
