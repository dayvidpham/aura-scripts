# Aura Status

Check current Aura Protocol status via Beads.

## Steps

1. Check for active plans:
   ```bash
   bd list --labels="aura:propose-plan" --status=open
   bd list --labels="aura:ratified-plan" --status=open
   ```

2. Check implementation progress:
   ```bash
   bd list --labels="aura:impl-plan" --status=open
   bd list --labels="aura:impl" --status=in_progress
   bd list --labels="aura:impl" --status=blocked
   bd list --labels="aura:impl" --status=done
   ```

3. Get project stats:
   ```bash
   bd stats
   ```

4. Report status

## Output Format

```
## Aura Protocol Status

**Phase:** {RequestPlan | ProposePlan | Review | Ratified | Implementation}
**Active Plan:** {task-id or "None"}

### Plans
- [propose-plan-id] Status: {open|closed}
- [ratified-plan-id] Status: {open|closed}

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
