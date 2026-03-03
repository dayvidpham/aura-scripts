# Research: XML Schema Extensions for Code Examples, Checklists, Coordination Tables, and Workflow Diagrams

**Date:** 2026-03-02
**Task:** aura-plugins-t8r0
**Depth:** deep-dive
**Topic:** XML schema design for code generation with HAS-A example attachments, completion checklists, coordination tables, and workflow diagrams

---

## Table of Contents

1. [Context and Current Schema State](#1-context-and-current-schema-state)
2. [Code Examples Attached to Constraints and Procedure Steps](#2-code-examples-attached-to-constraints-and-procedure-steps)
3. [Completion Checklists Per Role](#3-completion-checklists-per-role)
4. [Inter-Agent Coordination Command Tables Per Role](#4-inter-agent-coordination-command-tables-per-role)
5. [Workflow Diagrams as Named Stage Sequences](#5-workflow-diagrams-as-named-stage-sequences)
6. [Role-Specific Prose Introductions](#6-role-specific-prose-introductions)
7. [BCNF Preservation Strategy](#7-bcnf-preservation-strategy)
8. [Recommended Schema Extension Design](#8-recommended-schema-extension-design)
9. [Sources](#9-sources)

---

## 1. Context and Current Schema State

The Aura protocol schema (`skills/protocol/schema.xml`) is a BCNF-normalized XML document that drives code generation of agent role SKILL.md files via a Jinja2 template (`skills/templates/skill_header.j2`). The generation pipeline is:

```
schema.xml  -->  types.py (Python dataclasses)  -->  gen_skills.py  -->  skill_header.j2  -->  SKILL.md
```

The Python types in `types.py` are the source of truth. `gen_schema.py` generates the XML from Python types. `schema_parser.py` can also parse the XML back. The sync test `test_schema_types_sync.py` verifies bidirectional consistency.

### Current Schema Entities

| Entity | XML Element | Python Type | Notes |
|--------|------------|-------------|-------|
| Constraints | `<constraint>` | `ConstraintSpec` / `ConstraintContext` | GWT/S format, role-ref/phase-ref attributes |
| Procedure steps | `<step>` under `<procedure-steps>/<role>` | `ProcedureStep` | Has instruction, command, context, next-state |
| Phases | `<phase>` | `PhaseSpec` | 12-phase lifecycle |
| Commands | `<command>` | `CommandSpec` | Skill definitions |
| Handoffs | `<handoff>` | `HandoffSpec` | Actor-change transitions |
| Roles | `<role>` | `RoleSpec` | Agent role definitions |
| Labels | `<label>` | `LabelSpec` | Closed label set |
| Review axes | `<axis>` | `ReviewAxisSpec` | 3 code review axes |
| Title conventions | `<title-convention>` | `TitleConvention` | Task naming patterns |

### What is NOT Currently Schematized

Looking at the supervisor SKILL.md (956 lines), the hand-authored body below the `<!-- END GENERATED -->` marker contains:

- **Role-specific prose introduction** ("You coordinate parallel task execution...")
- **Code examples** embedded in constraints and procedures (bash/Go snippets)
- **Completion checklists** (markdown checkbox lists)
- **Inter-agent coordination command tables** (action/command pairs)
- **Workflow diagrams** ("Ride the Wave" stage sequence in ASCII)

These are the five categories we need to schematize.

---

## 2. Code Examples Attached to Constraints and Procedure Steps

### Research Question

What are best practices for XML schemas that embed code examples? How do documentation generators handle code example attachments on constraint/rule objects?

### Industry Prior Art

#### DocBook `<programlisting>` (Industry Standard)

DocBook uses the `<programlisting>` element with a `language` attribute for code blocks. Key design decisions:

- **`language` attribute** (CDATA): Identifies the programming language ("python", "bash", "go", etc.)
- **CDATA sections**: Content inside `<![CDATA[ ... ]]>` is not parsed as XML, so `<`, `>`, `&` do not need escaping. This is the recommended approach for embedding code.
- **Container pattern**: `<programlisting>` lives inside `<example>` or `<informalexample>` containers that provide title, cross-reference ID, and categorization.
- **Callout annotations**: `<programlistingco>` wraps a `<programlisting>` with `<areaspec>` for line/column-specific annotations and a `<calloutlist>` for explanations.
- **`linenumbering` attribute**: Controls auto-numbering (`numbered` / `unnumbered`).

Relevant parents of `<programlisting>` include `<example>`, `<figure>`, `<chapter>`, `<section>` -- and critically, the element can appear inside any block context.

Source: [DocBook programlisting reference](https://tdg.docbook.org/tdg/4.5/programlisting.html)

#### DITA `<codeblock>` (Alternative Standard)

DITA uses `<codeblock>` with:

- **`outputclass` attribute**: Specifies language for syntax highlighting (e.g., `outputclass="language-python"`).
- **Special characters**: Must be escaped because DITA parses content (unlike DocBook CDATA).
- **`show-whitespace`, `show-line-numbers`, `normalize-space`**: Additional outputclass keywords for display control.

Source: [DITA codeblock reference](https://www.oxygenxml.com/dita/1.3/specs/langRef/technicalContent/codeblock.html)

#### DocBook Annotation Association (Flexible Linking)

DocBook 5 introduced a general-purpose annotation mechanism using **attribute-based association**:

- `annotates` attribute on `<annotation>` matches the `xml:id` of the target element.
- `annotations` attribute on any element matches the `xml:id` of an associated `<annotation>`.
- Association can go in **either or both directions**.

This decoupled approach means annotations are not children of the annotated element -- they can live in a separate section.

Source: [DocBook 5 annotation mechanism](https://docbook.org/docs/howto/howto.xml)

### CDATA vs. Escaped Content: Decision Analysis

| Approach | Pros | Cons |
|----------|------|------|
| **CDATA sections** | No escaping needed; code reads naturally; easy to paste real code | Cannot contain `]]>`; breaks if code has that sequence; some XML parsers handle poorly |
| **Escaped content** | Always safe; no forbidden sequences; XML-roundtrip clean | `<`, `>`, `&` must be escaped; code becomes harder to read in raw XML |
| **External file reference** | Clean XML; real code files; testable | Requires file management; path resolution; more complex pipeline |

**Recommendation for Aura schema:** Use CDATA sections. The code examples in SKILL.md files are short (5-30 lines), are always bash/Go/pseudo-code, and the `]]>` sequence is extremely unlikely to appear. The readability benefit of CDATA outweighs the minor nesting limitation.

### HAS-A Design for Example Attachment

The key design question: Should `<example>` elements be **inline children** of `<constraint>` and `<step>`, or **referenced siblings** via IDREF?

**Analysis using BCNF criteria:**

An example is **functionally dependent** on its parent constraint or step -- it illustrates THAT specific rule. Moving it to a shared pool would violate the semantic dependency (an example of "use git agent-commit" makes no sense outside constraint C-agent-commit).

However, a code example COULD illustrate multiple constraints (e.g., a bash snippet showing both correct dependency direction AND leaf task creation). This is a many-to-many relationship.

**Design decision: Inline children with optional `also-illustrates` back-references.**

```xml
<!-- Inline child: primary HAS-A relationship -->
<constraint id="C-agent-commit" given="..." when="..." then="..." should-not="...">
  <examples>
    <example id="ex-agent-commit-1" lang="bash" label="correct">
      <![CDATA[git agent-commit -m "feat(protocol): add schema extensions"]]>
    </example>
    <example id="ex-agent-commit-2" lang="bash" label="anti-pattern">
      <![CDATA[git commit -m "feat(protocol): add schema extensions"]]>
    </example>
  </examples>
</constraint>

<!-- Back-reference for cross-cutting examples -->
<constraint id="C-dep-direction" ...>
  <examples>
    <example id="ex-dep-correct" lang="bash" label="correct">
      <![CDATA[bd dep add <parent-id> --blocked-by <child-id>]]>
    </example>
    <example id="ex-dep-anti" lang="bash" label="anti-pattern"
             also-illustrates="C-slice-leaf-tasks">
      <![CDATA[bd dep add <child-id> --blocked-by <parent-id>]]>
    </example>
  </examples>
</constraint>
```

This preserves BCNF because:
1. Each example is stored exactly once (inline with its primary parent).
2. The `also-illustrates` attribute is a reference, not duplication.
3. No transitive dependencies: the example depends on its constraint, not on any intermediate entity.

### Recommended `<example>` Element Schema

```xml
<!-- Attributes -->
<example
  id="ex-..."           <!-- Required: unique identifier -->
  lang="bash|go|python|pseudo|xml|json"  <!-- Required: language -->
  label="correct|anti-pattern|context|template"  <!-- Required: example category -->
  also-illustrates="C-id,S-id,..."  <!-- Optional: cross-references -->
  title="..."           <!-- Optional: human-readable title -->
>
  <![CDATA[
    ... code content ...
  ]]>
</example>
```

The `label` attribute is a closed enum indicating whether the example shows a **correct** pattern, an **anti-pattern**, contextual information, or a template.

---

## 3. Completion Checklists Per Role

### Research Question

What patterns exist for checklist/gate specifications in XML schemas?

### Industry Prior Art

#### NIST XCCDF (Extensible Configuration Checklist Description Format)

XCCDF is the standard for security compliance checklists. Key structural patterns:

- **Benchmark** (root) contains **Group** and **Rule** elements.
- **Rule** elements contain `<check>` child elements that specify the actual validation.
- **Group** elements organize rules hierarchically.
- Each Rule has `selected="true|false"` and `weight` for scoring.
- Values are parameterized via `<Value>` elements with `<default>` children.

Source: [NIST XCCDF specification](https://csrc.nist.gov/projects/security-content-automation-protocol/specifications/xccdf)

#### Schematron (Rule-Based Validation)

Schematron expresses constraints as patterns of assertions:

```xml
<pattern>
  <rule context="...xpath...">
    <assert test="...xpath...">Error message</assert>
    <report test="...xpath...">Info message</report>
  </rule>
</pattern>
```

Key insight: Schematron groups rules into **phases** that can be activated independently. This maps well to our per-role checklists.

Source: [Schematron introduction](https://www.xml.com/pub/a/2003/11/12/schematron.html)

#### Quality Gates in Software Development

Quality gates are predefined conditions that must be satisfied:
- Code coverage thresholds
- Zero security vulnerabilities
- Performance benchmarks
- Test pass rates

Source: [SonarSource quality gate definition](https://www.sonarsource.com/resources/library/quality-gate/)

### Current State in SKILL.md

The supervisor and worker SKILL.md files contain markdown checklists like:

```markdown
## Completion Checklist

- [ ] Production code path verified via code inspection
- [ ] Tests import production code
- [ ] No dual-export anti-pattern
- [ ] No TODO placeholders
- [ ] Service wired with real dependencies
- [ ] Quality gates pass
```

These are role-specific, not phase-specific. Some items are shared across roles, some are unique.

### Recommended `<checklist>` Element Schema

```xml
<checklists>
  <checklist id="CL-worker-completion" role-ref="worker" gate="completion"
             description="Items to verify before marking a slice complete">
    <item id="CLI-prod-path" required="true">
      Production code path verified via code inspection:
      no TODO placeholders in CLI/API actions,
      real dependencies wired (not mocks in production code),
      tests import production code (not test-only export)
    </item>
    <item id="CLI-test-imports" required="true">
      Tests import production code (not separate test-only export)
    </item>
    <item id="CLI-no-dual-export" required="true">
      No dual-export anti-pattern: one code path for both tests and production
    </item>
    <item id="CLI-no-todo" required="true">
      No TODO placeholders in owned code
    </item>
    <item id="CLI-real-deps" required="true">
      Service wired with real dependencies (not mocks in production code)
    </item>
    <item id="CLI-quality-gates" required="true">
      Quality gates pass (typecheck + tests)
    </item>
  </checklist>

  <checklist id="CL-supervisor-slice-closure" role-ref="supervisor" gate="slice-closure"
             description="Items to verify before closing a slice">
    <item id="CLS-reviewed" required="true">
      Slice reviewed at least once by Cartographers
    </item>
    <item id="CLS-no-blockers" required="true">
      No open BLOCKER findings
    </item>
    <item id="CLS-worker-signaled" required="true">
      Worker signaled completion via bd comments add
    </item>
  </checklist>
</checklists>
```

**BCNF analysis:** Each checklist item is functionally dependent on (role, gate) -- an item "production code path verified" only makes sense for the worker-completion context. No transitive dependencies. The `role-ref` is a foreign key, not duplication.

The `gate` attribute is a closed enum:

```xml
<enum name="GateType">
  <value id="completion" description="Final verification before task closure" />
  <value id="slice-closure" description="Supervisor verification before closing a slice" />
  <value id="review-ready" description="Pre-review verification" />
  <value id="landing" description="Pre-push landing checklist" />
</enum>
```

---

## 4. Inter-Agent Coordination Command Tables Per Role

### Research Question

How should role-specific coordination command tables be structured?

### Current State

Both supervisor and worker SKILL.md files contain tables like:

```markdown
## Inter-Agent Coordination

| Action | Command |
|--------|---------|
| Assign task | `bd update <task-id> --assignee "<worker-name>"` |
| Update status | `bd update <task-id> --status=in_progress` |
| Add comment | `bd comments add <task-id> "Status: ..."` |
| Check task state | `bd show <task-id>` |
```

These tables vary by role: supervisors have assign/track/spawn commands, workers have claim/report/blocked commands.

### Design Analysis

A coordination command is a triple of (role, action-verb, bd-command-template). This is a straightforward HAS-A relationship: a role HAS many coordination commands.

**Key insight:** Some coordination commands are shared across roles (e.g., `bd show <task-id>` for "Check task state" is used by every role). We need to support both role-specific and shared commands.

### Recommended `<coordination-commands>` Element Schema

```xml
<coordination-commands>
  <!-- Shared commands (all roles) -->
  <coord-cmd id="CC-show" action="Check task state" shared="true">
    <template>bd show &lt;task-id&gt;</template>
  </coord-cmd>
  <coord-cmd id="CC-comment" action="Add progress note" shared="true">
    <template>bd comments add &lt;task-id&gt; "..."</template>
  </coord-cmd>

  <!-- Role-specific commands -->
  <coord-cmd id="CC-assign" action="Assign task" role-ref="supervisor">
    <template>bd update &lt;task-id&gt; --assignee="&lt;worker-name&gt;"</template>
  </coord-cmd>
  <coord-cmd id="CC-update-status" action="Update status" role-ref="supervisor">
    <template>bd update &lt;task-id&gt; --status=in_progress</template>
  </coord-cmd>
  <coord-cmd id="CC-claim" action="Claim task" role-ref="worker">
    <template>bd update &lt;task-id&gt; --status=in_progress</template>
  </coord-cmd>
  <coord-cmd id="CC-report-completion" action="Report completion" role-ref="worker">
    <template>bd close &lt;task-id&gt;</template>
  </coord-cmd>
  <coord-cmd id="CC-report-blocker" action="Report blocker" role-ref="worker">
    <template>bd update &lt;task-id&gt; --notes="Blocked: &lt;reason&gt;"</template>
  </coord-cmd>
</coordination-commands>
```

**BCNF analysis:** Each coord-cmd is uniquely identified by `id`. The `role-ref` is a foreign key (or null for shared). The `action` is a human-readable label. The `template` is the bd command template. No duplication, no transitive dependencies.

**Alternative considered:** Embedding coord-cmds inside `<role>` elements. Rejected because shared commands would need duplication across every role, violating BCNF.

---

## 5. Workflow Diagrams as Named Stage Sequences

### Research Question

How do workflow definition languages represent stage sequences?

### Industry Prior Art

#### BPMN 2.0

BPMN defines workflows as:
- **Process** (container): `<process id="..." name="...">`
- **Tasks** (atomic work units): `<userTask id="..." name="...">`
- **Gateways** (branching): `<exclusiveGateway>`, `<parallelGateway>`
- **Sequence flows** (directed edges): `<sequenceFlow id="..." sourceRef="..." targetRef="...">`
- **Events**: `<startEvent>`, `<endEvent>`

The key pattern is that **control flow is explicit via sequenceFlow elements**, not implicit via ordering.

Source: [Flowable BPMN Introduction](https://www.flowable.com/open-source/docs/bpmn/ch07a-BPMN-Introduction)

#### XPDL (XML Process Definition Language)

XPDL uses:
- **WorkflowProcess** as the container
- **Activity** as the work unit
- **Transition** as the directed edge between activities

Source: [XPDL specification](https://en.wikipedia.org/wiki/XPDL)

### Current State

The supervisor SKILL.md contains a "Ride the Wave" workflow diagram:

```
Phase 8: PLAN
  +- Read RATIFIED_PLAN + URD
  +- Spawn 3 Cartographers (TeamCreate, /aura:explore)
  +- Query Cartographers to map codebase
  +- Decompose into vertical slices + integration points
  +- Create leaf tasks for every slice

Phase 9: BUILD
  +- Spawn N Workers into same team (TeamCreate, /aura:worker)
  +- Workers implement their slices in parallel
  +- Workers do NOT shut down when finished

Phase 10: REVIEW + FIX CYCLES (max 3)
  +- Cycle 1: ...
  +- Cycle 2 (if needed): ...
  +- Cycle 3 (if needed): ...
  +- After 3 cycles: remaining IMPORTANT -> FOLLOWUP, proceed to UAT

DONE -> Phase 11 (UAT)
```

This is a named, multi-stage workflow with conditional looping.

### Design Analysis

The existing schema already has `<phases>` with `<substeps>` and `<transitions>`. But the "Ride the Wave" workflow is a **higher-level orchestration pattern** that spans multiple phases and describes agent behavior patterns, not protocol transitions.

We need a separate concept: a **named workflow** that sequences **stages** (not phases). Each stage has:
- An identifier
- A human-readable description
- An owning phase (where it fits in the 12-phase lifecycle)
- An execution mode (sequential / parallel / conditional-loop)
- Child actions (specific things to do)

### Recommended `<workflows>` Element Schema

Inspired by BPMN's process/task/sequenceFlow pattern but simplified:

```xml
<workflows>
  <workflow id="WF-ride-the-wave" name="Ride the Wave"
            role-ref="supervisor"
            description="Coordinated Phase 8-10 execution pattern">
    <stage id="WFS-plan" name="PLAN" phase-ref="p8" order="1"
           execution="sequential">
      <action order="1">Read RATIFIED_PLAN + URD</action>
      <action order="2">Spawn 3 Cartographers (TeamCreate, /aura:explore)</action>
      <action order="3">Query Cartographers to map codebase</action>
      <action order="4">Decompose into vertical slices + integration points</action>
      <action order="5">Create leaf tasks for every slice</action>
    </stage>

    <stage id="WFS-build" name="BUILD" phase-ref="p9" order="2"
           execution="parallel">
      <action order="1">Spawn N Workers into same team (TeamCreate, /aura:worker)</action>
      <action order="2" execution="parallel">Workers implement their slices in parallel</action>
      <action order="3" note="Workers do NOT shut down when finished" />
    </stage>

    <stage id="WFS-review" name="REVIEW + FIX CYCLES" phase-ref="p10" order="3"
           execution="conditional-loop" max-iterations="3">
      <action order="1">Cartographers switch to /aura:reviewer-review-code</action>
      <action order="2">Cartographers review ALL slices (severity tree)</action>
      <action order="3">Create FOLLOWUP epic if ANY IMPORTANT/MINOR findings</action>
      <action order="4">Workers fix BLOCKERs + IMPORTANTs</action>
      <action order="5">Cartographers re-review</action>
      <exit-condition type="success">All reviewers ACCEPT, no open BLOCKERs</exit-condition>
      <exit-condition type="continue">BLOCKERs or IMPORTANT remain, cycles &lt; 3</exit-condition>
      <exit-condition type="escalate">3 cycles exhausted, BLOCKERs remain</exit-condition>
      <exit-condition type="proceed">3 cycles exhausted, only IMPORTANT remain -> FOLLOWUP</exit-condition>
    </stage>

    <stage id="WFS-done" name="DONE" phase-ref="p11" order="4"
           execution="sequential">
      <action order="1">Shut down Cartographers + Workers</action>
      <action order="2">Proceed to Phase 11 (UAT)</action>
    </stage>
  </workflow>
</workflows>
```

**BCNF analysis:**
- Each workflow is uniquely identified by `id`.
- Each stage is uniquely identified by `id` within the workflow.
- The `phase-ref` is a foreign key, not duplication.
- Actions are ordered children of stages -- no transitive dependencies.
- Exit conditions are structured data, not free-text.

---

## 6. Role-Specific Prose Introductions

### Current State

Each SKILL.md has a prose introduction below the generated header:

- Supervisor: "You coordinate parallel task execution."
- Worker: "You own a vertical slice (full production code path from CLI/API entry point -> service -> types)."
- Reviewer: role-specific review instructions
- Architect: specification and design instructions

### Design Analysis

Prose introductions are **role-specific singleton text blocks**. They have a 1:1 relationship with roles. This is a simple HAS-A: a role HAS one introduction.

### Recommended Schema

```xml
<role id="supervisor" name="Supervisor" description="Task coordinator...">
  <owns-phases>...</owns-phases>
  <introduction>
    You coordinate parallel task execution. Your job is coordination,
    tracking, and quality control -- never implementation.
  </introduction>
  ...
</role>
```

**Alternative considered:** A separate `<introductions>` section with role-ref. Rejected because introductions have a strict 1:1 relationship with roles, and separating them creates an unnecessary join. Inline child preserves locality.

---

## 7. BCNF Preservation Strategy

### The BCNF-Preserving Way to Add HAS-A Relationships

The current schema follows BCNF principles:
1. Each fact stored exactly once.
2. Relationships via idref attributes, no duplication.
3. No transitive dependencies.
4. Enums define closed sets; entities reference enums by id.

Adding HAS-A relationships requires careful analysis of functional dependencies.

### Decision Framework

| Relationship | Cardinality | FD Direction | Schema Pattern | BCNF Impact |
|-------------|-------------|--------------|----------------|-------------|
| Constraint HAS examples | 1:N | Example -> Constraint | Inline child | Preserves: example is FD on constraint |
| Procedure step HAS examples | 1:N | Example -> Step | Inline child | Preserves: same reasoning |
| Role HAS checklist | 1:N per gate | Checklist -> (Role, Gate) | Sibling section with role-ref | Preserves: avoids role element bloat |
| Role HAS coord commands | M:N (shared) | Command -> Role OR shared | Separate section with role-ref | Preserves: shared commands not duplicated |
| Role HAS workflow | 1:N | Workflow -> Role | Sibling section with role-ref | Preserves: workflow is FD on role |
| Role HAS introduction | 1:1 | Introduction -> Role | Inline child of role | Preserves: strict 1:1 |
| Example ALSO-ILLUSTRATES constraint | M:N | - | Back-reference attribute | Preserves: reference, not duplication |

### Key Principles

1. **Inline children** for strict 1:N where the child is functionally dependent on the parent (examples on constraints, introductions on roles).
2. **Sibling sections with foreign keys** for entities that have M:N relationships or shared semantics (coordination commands, checklists).
3. **Back-reference attributes** for cross-cutting relationships (`also-illustrates`).
4. **Closed enums** for all category/label/type fields to prevent stringly-typed drift.

### New Enums Required

```xml
<enum name="ExampleLabel">
  <value id="correct" description="Shows the recommended pattern" />
  <value id="anti-pattern" description="Shows what NOT to do" />
  <value id="context" description="Provides situational context" />
  <value id="template" description="Fill-in-the-blank template for the user" />
</enum>

<enum name="ExampleLang">
  <value id="bash" description="Shell commands and scripts" />
  <value id="go" description="Go source code" />
  <value id="python" description="Python source code" />
  <value id="pseudo" description="Pseudocode or structured text" />
  <value id="xml" description="XML markup" />
  <value id="json" description="JSON data" />
  <value id="markdown" description="Markdown content" />
</enum>

<enum name="GateType">
  <value id="completion" description="Final verification before task closure" />
  <value id="slice-closure" description="Supervisor verification before closing a slice" />
  <value id="review-ready" description="Pre-review verification" />
  <value id="landing" description="Pre-push landing checklist" />
</enum>

<enum name="WorkflowExecution">
  <value id="sequential" description="Actions execute in order" />
  <value id="parallel" description="Actions can execute concurrently" />
  <value id="conditional-loop" description="Actions repeat until exit condition met" />
</enum>
```

---

## 8. Recommended Schema Extension Design

### Summary of All Extensions

```xml
<aura-protocol version="2.1">
  <enums>
    <!-- Existing enums... -->
    <enum name="ExampleLabel">...</enum>
    <enum name="ExampleLang">...</enum>
    <enum name="GateType">...</enum>
    <enum name="WorkflowExecution">...</enum>
  </enums>

  <!-- Existing sections unchanged: labels, review-axes, phases -->

  <roles>
    <role id="supervisor" ...>
      <owns-phases>...</owns-phases>
      <!-- NEW: inline introduction -->
      <introduction>You coordinate parallel task execution...</introduction>
      <!-- Existing: label-awareness, invariants, standing-teams -->
    </role>
  </roles>

  <!-- Existing: commands, handoffs -->

  <constraints>
    <constraint id="C-agent-commit" given="..." when="..." then="..." should-not="...">
      <!-- NEW: inline examples (HAS-A) -->
      <examples>
        <example id="ex-agent-commit-correct" lang="bash" label="correct">
          <![CDATA[git agent-commit -m "feat(protocol): add schema extensions"]]>
        </example>
        <example id="ex-agent-commit-anti" lang="bash" label="anti-pattern">
          <![CDATA[git commit -m "feat(protocol): add schema extensions"]]>
        </example>
      </examples>
    </constraint>
  </constraints>

  <procedure-steps>
    <role ref="supervisor">
      <step order="1" id="S-supervisor-call-skill">
        <instruction>Call Skill(/aura:supervisor) to load role instructions</instruction>
        <command>Skill(/aura:supervisor)</command>
        <!-- NEW: inline examples on steps -->
        <examples>
          <example id="ex-call-skill" lang="pseudo" label="correct">
            <![CDATA[Skill(/aura:supervisor)]]>
          </example>
        </examples>
      </step>
    </role>
  </procedure-steps>

  <!-- NEW SECTION: Checklists -->
  <checklists>
    <checklist id="CL-worker-completion" role-ref="worker" gate="completion"
               description="Items to verify before marking a slice complete">
      <item id="CLI-prod-path" required="true">
        Production code path verified via code inspection
      </item>
      <!-- ... more items -->
    </checklist>
  </checklists>

  <!-- NEW SECTION: Coordination Commands -->
  <coordination-commands>
    <coord-cmd id="CC-show" action="Check task state" shared="true">
      <template>bd show &lt;task-id&gt;</template>
    </coord-cmd>
    <coord-cmd id="CC-assign" action="Assign task" role-ref="supervisor">
      <template>bd update &lt;task-id&gt; --assignee="&lt;worker-name&gt;"</template>
    </coord-cmd>
    <!-- ... more commands -->
  </coordination-commands>

  <!-- NEW SECTION: Workflows -->
  <workflows>
    <workflow id="WF-ride-the-wave" name="Ride the Wave"
              role-ref="supervisor"
              description="Coordinated Phase 8-10 execution pattern">
      <stage id="WFS-plan" name="PLAN" phase-ref="p8" order="1"
             execution="sequential">
        <action order="1">Read RATIFIED_PLAN + URD</action>
        <!-- ... -->
      </stage>
      <!-- ... more stages -->
    </workflow>
  </workflows>

  <!-- Existing sections unchanged: documents, dependency-model, followup-lifecycle -->
</aura-protocol>
```

### New Python Types Required

```python
@dataclass(frozen=True)
class CodeExample:
    """A code example attached to a constraint or procedure step."""
    id: str
    lang: ExampleLang     # New enum
    label: ExampleLabel   # New enum
    content: str          # The actual code (CDATA content)
    title: str | None = None
    also_illustrates: tuple[str, ...] = ()  # Cross-references

@dataclass(frozen=True)
class ChecklistItem:
    """A single item in a completion checklist."""
    id: str
    text: str
    required: bool = True

@dataclass(frozen=True)
class Checklist:
    """A completion checklist for a specific role and gate."""
    id: str
    role_ref: RoleId
    gate: GateType        # New enum
    description: str
    items: tuple[ChecklistItem, ...]

@dataclass(frozen=True)
class CoordinationCommand:
    """An inter-agent coordination command."""
    id: str
    action: str
    template: str
    role_ref: RoleId | None = None  # None = shared across all roles
    shared: bool = False

@dataclass(frozen=True)
class WorkflowAction:
    """A single action within a workflow stage."""
    order: int
    description: str
    execution: ExecutionMode | None = None  # Override stage default
    note: str | None = None

@dataclass(frozen=True)
class ExitCondition:
    """An exit condition for a conditional-loop stage."""
    type: str  # "success", "continue", "escalate", "proceed"
    description: str

@dataclass(frozen=True)
class WorkflowStage:
    """A named stage within a workflow."""
    id: str
    name: str
    phase_ref: PhaseId
    order: int
    execution: WorkflowExecution  # New enum
    actions: tuple[WorkflowAction, ...]
    max_iterations: int | None = None  # For conditional-loop
    exit_conditions: tuple[ExitCondition, ...] = ()

@dataclass(frozen=True)
class Workflow:
    """A named multi-stage workflow pattern."""
    id: str
    name: str
    role_ref: RoleId
    description: str
    stages: tuple[WorkflowStage, ...]
```

### Impact on Generation Pipeline

The Jinja2 template (`skill_header.j2`) will need new sections:

1. **Examples** rendered inline with constraints and steps (already in template context via `constraints` and `steps`).
2. **Completion Checklist** section rendered from `checklists` context variable.
3. **Coordination Commands** table rendered from `coord_commands` context variable.
4. **Workflow Diagram** section rendered from `workflows` context variable.
5. **Introduction** paragraph rendered from `role.introduction` (inline on role).

### Migration Path

1. Add new enums to `types.py`.
2. Add new dataclass types.
3. Add new constant dictionaries (CHECKLISTS, COORDINATION_COMMANDS, WORKFLOWS).
4. Extend `gen_schema.py` to emit new XML sections.
5. Extend `schema_parser.py` to parse new XML sections.
6. Extend `gen_skills.py` context builders.
7. Update `skill_header.j2` template.
8. Update `test_schema_types_sync.py` to verify new entities.
9. Populate data from existing hand-authored SKILL.md content.

---

## 9. Sources

### XML Code Example Embedding
- [DocBook programlisting reference](https://tdg.docbook.org/tdg/4.5/programlisting.html)
- [DocBook programlisting co (callout annotations)](https://tdg.docbook.org/tdg/4.5/programlistingco.html)
- [DocBook annotating program listings](https://sagehill.net/docbookxsl/AnnotateListing.html)
- [DITA codeblock](https://www.oxygenxml.com/dita/1.3/specs/langRef/technicalContent/codeblock.html)
- [DITA-OT extended codeblock processing](https://www.dita-ot.org/dev/reference/extended-functionality.html)
- [CDATA guide for developers](https://www.devzery.com/post/cdata-in-xml-a-comprehensive-guide-for-developers)
- [CDATA - Wikipedia](https://en.wikipedia.org/wiki/CDATA)

### Checklist and Gate Specifications
- [NIST XCCDF specification](https://csrc.nist.gov/projects/security-content-automation-protocol/specifications/xccdf)
- [XCCDF 1.2 Schema (XSD)](https://csrc.nist.gov/schema/xccdf/1.2/xccdf_1.2.xsd)
- [Schematron introduction](https://www.xml.com/pub/a/2003/11/12/schematron.html)
- [Schematron.com](https://schematron.com/)
- [SonarSource quality gate definition](https://www.sonarsource.com/resources/library/quality-gate/)

### Workflow Definition Languages
- [BPMN 2.0 Introduction - Flowable](https://www.flowable.com/open-source/docs/bpmn/ch07a-BPMN-Introduction)
- [BPMN primer - Camunda](https://docs.camunda.io/docs/components/modeler/bpmn/bpmn-primer/)
- [BPMN specification](https://www.bpmn.org/)
- [XPDL - Wikipedia](https://en.wikipedia.org/wiki/XPDL)

### BCNF and XML Schema Design
- [A Normal Form for XML Documents - Arenas & Libkin](https://marceloarenas.cl/publications/xnf_tods04.pdf)
- [Normalization Theory for XML - Libkin](https://homepages.inf.ed.ac.uk/libkin/papers/xsym07.pdf)
- [W3C XML Schema Design Patterns: Avoiding Complexity](https://www.xml.com/pub/a/2002/11/20/schemas.html)
- [XML Schemas: Composition vs. Subclassing](https://www.xfront.com/composition-versus-subclassing.html)
- [ID/IDREF vs. Key/KeyRef](https://docstore.mik.ua/orelly/xml/schema/ch09_03.htm)
- [XML Schemas: Global vs. Local](https://xfront.com/GlobalVersusLocal.html)
- [DocBook 5 annotation mechanism](https://docbook.org/docs/howto/howto.xml)
