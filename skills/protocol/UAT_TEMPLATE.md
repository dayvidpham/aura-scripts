# UAT Structured Output Template

Use this XML template to capture UAT results. Each component is presented one at a time to the user with its definition, motivating example, and design-space questions.

## Template

```xml
<uat>
  <metadata>
    <title>{{UAT_TITLE}}</title>
    <beads-id>{{BEADS_TASK_ID}}</beads-id>
    <proposal-ref>{{PROPOSAL_BEADS_ID}}</proposal-ref>
    <phase>{{plan | implementation}}</phase>
    <date>{{YYYY-MM-DD}}</date>
  </metadata>

  <components>

    <component id="{{N}}">
      <name>{{COMPONENT_NAME}}</name>

      <definition>
        <code lang="{{LANGUAGE}}">
{{CODE_SNIPPET_OR_INTERFACE_DEFINITION}}
        </code>
      </definition>

      <motivating-example>
        {{DESCRIPTION_OF_BEFORE_AFTER_OR_USAGE_SCENARIO}}
        <code lang="{{LANGUAGE}}">
{{EXAMPLE_CODE_OR_OUTPUT}}
        </code>
      </motivating-example>

      <questions>

        <question id="Q{{M}}">
          <text>{{EXACT_QUESTION_TEXT_PRESENTED_TO_USER}}</text>
          <context>{{OPTIONAL_ADDITIONAL_CONTEXT_SHOWN_BEFORE_OPTIONS}}</context>

          <options>
            <option id="{{A}}">
              <label>{{OPTION_LABEL}}</label>
              <description>{{OPTION_DESCRIPTION_WITH_TRADEOFFS}}</description>
            </option>
            <option id="{{B}}">
              <label>{{OPTION_LABEL}}</label>
              <description>{{OPTION_DESCRIPTION_WITH_TRADEOFFS}}</description>
            </option>
            <!-- 2-4 options per question -->
          </options>

          <user-response>
            <selected>{{OPTION_LABEL_OR_OTHER}}</selected>
            <verbatim>{{USER_RESPONSE_VERBATIM_INCLUDING_NOTES}}</verbatim>
          </user-response>
        </question>

        <!-- User-initiated comments (not in response to a question) -->
        <user-comment>
          <verbatim>{{EXACT_USER_COMMENT}}</verbatim>
        </user-comment>

      </questions>

      <decision>{{ACCEPT | REVISE}}</decision>
      <decision-notes>{{OPTIONAL_NOTES_ON_DECISION}}</decision-notes>
    </component>

  </components>

  <addenda>
    <!-- Post-UAT user comments captured verbatim -->
    <addendum>
      <verbatim>{{EXACT_USER_STATEMENT}}</verbatim>
      <design-implication>{{WHAT_THIS_MEANS_FOR_THE_DESIGN}}</design-implication>
    </addendum>
  </addenda>

  <final-decision>
    <verdict>{{ACCEPT | REVISE}}</verdict>
    <summary>
      <change id="{{N}}">{{KEY_DESIGN_CHANGE_FROM_ORIGINAL_PROPOSAL}}</change>
      <!-- One per design change -->
    </summary>
    <open-questions>
      <question>{{DEFERRED_OR_UNRESOLVED_QUESTION}}</question>
    </open-questions>
  </final-decision>

</uat>
```

## Beads Commands

```bash
# 1. Create the UAT task with structured description
#    - Labels link it to the proposal and UAT phase
#    - Description contains the full XML-structured UAT record
bd create \
  --labels "aura:p5-user:s5-uat" \
  --title "UAT: {{PLAN_OR_IMPL}} acceptance for {{FEATURE}}" \
  --description "---
references:
  proposal: {{PROPOSAL_TASK_ID}}
  urd: {{URD_TASK_ID}}
  request: {{REQUEST_TASK_ID}}
---
<FULL_XML_STRUCTURED_DESCRIPTION>"

# 2. Record post-UAT addenda as comments (user feedback after main survey)
bd comments add {{UAT_TASK_ID}} "UAT ADDENDUM (user-initiated, verbatim): {{VERBATIM}}"

# 3. Update URD with UAT results
bd comments add {{URD_TASK_ID}} "UAT {{PHASE}}: {{VERDICT}} - {{key design decisions summary}}"

# 4. After UAT passes, proceed to ratification (Phase 6)
bd label add {{PROPOSAL_TASK_ID}} aura:p6-plan:s6-ratify
bd comments add {{PROPOSAL_TASK_ID}} "RATIFIED: All 3 reviewers ACCEPT, UAT passed ({{UAT_TASK_ID}})."

# 5. If UAT fails (REVISE), return to proposal phase
#    - Do NOT ratify
#    - Create a new PROPOSAL-N task (increment N) related to the original
#    - Record the specific component and verbatim feedback
```

## Rules

1. **One component per AskUserQuestion call** — never batch all components into one survey
2. **Show definition + example BEFORE asking** — user must see the concrete thing first
3. **Options describe tradeoffs, not approval levels** — never use "exactly matches" / "mostly matches"
4. **Capture verbatim** — user responses are recorded exactly as given, including notes
5. **Option descriptions are part of the record** — capture label AND description for each option presented
6. **User-initiated comments** go in `<user-comment>` outside the question/answer flow
7. **Addenda** capture post-UAT feedback that modifies the design
8. **Final decision** summarizes all design changes relative to the proposal being UAT'd
9. **Binary decisions only** — component decisions are ACCEPT or REVISE (no intermediate levels)
10. **Findings tracked via severity tree** — if ACCEPT with minor concerns, track them as IMPORTANT/MINOR findings in the severity tree during code review (Phase 10), not at UAT time

## See Also

- [UAT_EXAMPLE.md](./UAT_EXAMPLE.md) — Complete worked example of this template in use
