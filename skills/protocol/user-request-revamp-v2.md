/aura:epoch Should devise a new architectural approach to the commands, process, and constraints that make it harder for work to get lost or forgotten about, for certain recurring issues to be addressed via improved validation pipelines, and for better process management and handoff. Improved human handoff would look something like the @protocol/HANDOFF_EXAMPLE-*.md files. Want to also define an explicit Beads schema and taxonomy with with labels that apply to each phase, task, review, UAT, URE, URD, IMPL_PLAN. Labels are being applied non-uniformly, often forgotten about and in a non-standardized manner.

Should look something like this:

The PROPOSAL-1 and PROPOSAL-2 should be a child of the URE.

What we want:
```
REQUEST
  └── blocked by URE
        └── blocked by PROPOSAL-1 (closed, superseded)
              └── blocked by PROPOSAL-1-REVIEW-A-1 (closed)
              └── blocked by PROPOSAL-1-REVIEW-B-1 (closed)
              └── blocked by PROPOSAL-1-REVIEW-C-1 (closed)
        └── blocked by PROPOSAL-{2,3,...,N-1} (closed, superseded)
              └── blocked by PROPOSAL-{K}-REVIEW-A-1 (closed)
              └── blocked by PROPOSAL-{K}-REVIEW-B-1 (closed)
              └── blocked by PROPOSAL-{K}-REVIEW-C-1 (closed)
        └── blocked by PROPOSAL-N (open, aura:plan:ratify)
              └── blocked by PROPOSAL-N-REVIEW-A-1 (closed)
              └── blocked by PROPOSAL-N-REVIEW-B-1 (closed)
              └── blocked by PROPOSAL-N-REVIEW-C-1 (closed)
              └── blocked by IMPL_PLAN
                    ├── blocked by slice-1
                    │     ├── blocked by leaf-task-a
                    │     └── blocked by leaf-task-b
                    └── blocked by slice-2
                          ├── blocked by leaf-task-c
                          └── blocked by leaf-task-d
```

Here is an actual example:
<example>
worktree/unified-schema-t9d [epic/unified-schema-t9d]
 I  -> bd dep tree unified-schema-t9d                                                             minttea@desktop

🌲 Dependency tree for unified-schema-t9d:

unified-schema-t9d: REQUEST: Aura ingest CLI command - data ingestion pipeline for Claude and OpenCode transcripts [P1] (open) [READY]
    └── unified-schema-m3l: URE: Aura ingest pipeline requirements elicitation [P1] (open)
    │   ├── unified-schema-apj: PROPOSAL-1: RFC v0.1.0 Aura ingest pipeline [P1] (closed)
        └── unified-schema-hjy: PROPOSAL-2: RFC v0.2.0 Aura ingest pipeline (revised) [P1] (open)
        │   ├── unified-schema-fuf: IMPL_PLAN: Aura ingest pipeline — 10 vertical slices (S1-S10) [P1] (open)
        │   │   ├── unified-schema-bq9: IMPL-UAT-1: Group A implementation acceptance (S2, S4, S5) [P2] (closed)
        │   │   ├── unified-schema-er6: Review Round 2: blocking fix verification [P2] (closed)
        │   │   ├── unified-schema-i80: Code Review: Adapter Slices S6-S8 [P2] (closed)
        │   │   ├── unified-schema-n6c: Code Review: Pipeline + CLI (S9-S10) [P2] (closed)
        │       └── unified-schema-o20: Code Review: Foundation Slices S1-S5 [P2] (closed)
            └── unified-schema-zj9: UAT-1: Plan acceptance for aura ingest pipeline RFC v0.2.0 [P2] (closed)


worktree/unified-schema-t9d [epic/unified-schema-t9d]
 I  -> pwd                                                                                        minttea@desktop
/home/minttea/dev/agent-data-leverage/unified-schema/worktree/unified-schema-t9d

</example>

Reviews rounds on the completed vertical slices in the IMPL_PLAN tend to create tasks that get lost. Unsure how to best account for them at the moment. Currently have this other FOLLOW_UP epic issue tracker that takes the Review Rounds / Code Reviews (these names need to be standardized) on the IMPL_PLAN, then takes the tasks generated from them, and then proposes architecture and designs that will resolve the issues the reviewers had.

Ideally, there would be a follow-up epoch where: architect should propose new architecture, should also plan architectural changes or make a design that understands and prevents these issues, how they arise, and prevent them from arising in the future. Could be architecture, design, or just new, better validation rules via `go fmt` or `go vet` or ast-grep rules. launch the supervisor using the `@aura-swarm` command once the architecture is proposed to resolve all these issues, and the tasks are topologically sorted and placed into vertical slices.

This would be generic though, not specific to a golang codebase---just using these command as an example. This would produce a followup-epic with structure like so:

<followup-epic-example>
worktree/unified-schema-t9d [epic/unified-schema-t9d]
 I  -> pwd                                                                                        minttea@desktop
/home/minttea/dev/agent-data-leverage/unified-schema/worktree/unified-schema-t9d

worktree/unified-schema-t9d [epic/unified-schema-t9d]
 I  -> bd dep tree unified-schema-ldl                                                             minttea@desktop

🌲 Dependency tree for unified-schema-ldl:

unified-schema-ldl: EPIC: Ingest Pipeline Follow-Up Work (post-implementation) [P2] (closed)
    ├── unified-schema-f6f: F1: HostSlug & Project Identity Refactoring [P2] (closed)
    │   ├── unified-schema-af6: R3: Adapters populate HostSlug, pipeline reads it [P2] (closed)
    │   ├── unified-schema-da3: R2: Extract shared DeriveProjectIdentifiers into hostslug.go [P2] (closed)
    │   ├── unified-schema-xvo: R1: Add HostSlug field to UnifiedMetadata [P2] (closed)
        └── unified-schema-kip: M5: DeriveHostSlug doesn't handle git:// or file:// remotes [P3] (closed)
    ├── unified-schema-02c: F7: Documentation [P3] (closed)
    │   ├── unified-schema-z6u: ARCH: Preventive Architecture for Ingest Pipeline Follow-Up [P2] (open)
    │   ├── unified-schema-2pm: M16: AGENTS.md Landing the Plane missing git agent-commit [P3] (closed)
    │   ├── unified-schema-jd3: M14: Orphan cleanup scan location coupled to tmpDir placement [P3] (closed)
        └── unified-schema-mas: M15: DefaultConfig() ghost in plan docs [P3] (closed)
    ├── unified-schema-08a: F6: URD Alignment [P3] (closed)
    │   ├── unified-schema-147: G2: Missing config silently uses defaults instead of prompting aura kickstart [P3] (closed)
    │   ├── unified-schema-34r: G3: 10s debounce window for staleness threshold not implemented [P3] (closed)
    │   ├── unified-schema-g35: G7: Pipeline stage interfaces are methods, not named Go interface types [P3] (closed)
    │   ├── unified-schema-njc: G5: --verbose doesn't show file-level detail; default output lacks session-level progress [P3] (closed)
    │   ├── unified-schema-p2m: G4: Dry-run output doesn't collapse subagents under parent with count [P3] (closed)
        └── unified-schema-p7l: G6: goleak not wired into TestMain for library packages [P3] (closed)
    ├── unified-schema-3j6: F2: Filesystem & IO Safety [P3] (closed)
    │   ├── unified-schema-0yo: M4: OSFileSystem.CopyFile doesn't call out.Sync() [P3] (closed)
    │   ├── unified-schema-bus: M11: Non-atomic remove+rename window for updates [P3] (closed)
        └── unified-schema-zao: I4: MemFS.Rename doesn't move directory contents [P3] (closed)
    ├── unified-schema-dtk: F3: Adapter Robustness [P3] (closed)
    │   ├── unified-schema-07x: I8: DefaultAdapterRegistry never populated [P3] (closed)
    │   ├── unified-schema-1df: M9: t.Helper() misuse in adapter_test.go [P3] (closed)
    │   ├── unified-schema-2se: I6: countToolCallParts counts all JSON files, not specifically tool-call parts [P3] (closed)
    │   ├── unified-schema-4z9: M6: Scanner buffer limit misleading in ClaudeAdapter [P3] (closed)
    │   ├── unified-schema-gox: I14: Empty ses.Directory causes hard ExtractMetadata failure in OpenCode [P3] (closed)
    │   ├── unified-schema-oms: M7: Unrealistic subagent fixture in claude_test.go [P3] (closed)
    │   ├── unified-schema-pcc: M1: ValidatePathContainment doc precondition not enforced [P3] (closed)
        └── unified-schema-s46: M8: No corrupt session JSON test for OpenCode adapter [P3] (closed)
    ├── unified-schema-n8e: F5: CLI UX & Debug [P3] (closed)
    │   ├── unified-schema-1sq: M13: printSummary total includes errors but parenthetical doesn't [P3] (closed)
    │   ├── unified-schema-5vg: M12: Duplicate kickstartCmd and ftueCmd [P3] (closed)
        └── unified-schema-jw5: I13: --debug flag registered but has zero effect [P3] (closed)
    └── unified-schema-qeb: F4: Pipeline Error Handling & Test Coverage [P3] (closed)
    │   ├── unified-schema-1xx: I15: SessionResult.Status misleading on extraction failure [P3] (closed)
    │   ├── unified-schema-2fd: I2: TestPipeline_OutputFilePermissions doesn't verify permissions [P3] (closed)
    │   ├── unified-schema-60y: I10: No test for Force+IncludeActive+active session [P3] (closed)
    │   ├── unified-schema-6zl: I17: Worktree prefix match without trailing slash guard [P3] (closed)
    │   ├── unified-schema-c8e: I11: No test for schema version upgrade triggering DiffUpdated [P3] (closed)
    │   ├── unified-schema-cqp: I12: buildSourceConfigs silently drops invalid paths [P3] (closed)
    │   ├── unified-schema-g2o: M2: Temp dir placement deviates from RFC specification [P3] (closed)
    │   ├── unified-schema-nlp: I16: Empty BasePath produces unhelpful error message [P3] (closed)
        └── unified-schema-s3l: M17: B6 tracking field has no test assertion on meta.Git.Tracking [P3] (closed)

</followup-epic-example>

