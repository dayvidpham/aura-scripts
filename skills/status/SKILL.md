# Aura Status

Check current Aura Protocol status via Beads.

## Steps

1. Check for active plans:
   ```bash
   bd list --labels="aura:p3-plan:s3-propose" --status=open
   bd list --labels="aura:p6-plan:s6-ratify" --status=open
   ```

2. Check implementation progress:
   ```bash
   bd list --labels="aura:p8-impl:s8-plan" --status=open
   bd list --labels="aura:p9-impl:s9-slice" --status=in_progress
   bd list --labels="aura:p9-impl:s9-slice" --status=blocked
   bd list --labels="aura:p9-impl:s9-slice" --status=done
   ```

3. Get project stats:
   ```bash
   bd stats
   ```

4. Report status

## Output Format

```
## Aura Protocol Status

**Phase:** {Phase 1: Request | Phase 3: Propose | Phase 4: Review | Phase 6: Ratified | Phase 9: Implementation}
**Active Plan:** {task-id or "None"}

### Plans
- [proposal-id] Status: {open|closed}
- [ratified-id] Status: {open|closed}

### Implementation Progress
- IMPL_PLAN: {task-id}
- Layer 1: {N}/{M} complete
- Layer 2: {N}/{M} complete (blocked: {count})

### Blocked Tasks
- {task-id}: {blocker reason}

### Recent Activity
bd list --limit=5
```

## Quick Status

```bash
bd stats
bd ready
bd blocked
```
