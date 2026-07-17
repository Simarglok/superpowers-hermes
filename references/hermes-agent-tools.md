# Hermes Agent Tool Mapping

This pack ports behavior, not Claude Code hook schemas. Hermes' system skill index and `skill_view` provide progressive disclosure.

| Superpowers action | Hermes Agent |
|---|---|
| Discover skills | system skill index or `skills_list` |
| Load a skill | `skill_view(name)` |
| Load a supporting file | `skill_view(name, file_path)` |
| Read files | `read_file` |
| Find files or search text | `search_files` |
| Create files | `write_file` |
| Edit existing files | `patch` |
| Run git, tests, builds | `terminal` |
| Track a background command | `terminal(background=true)` + `process` |
| Track tasks | `todo` |
| Ask a user decision | `clarify` |
| Delegate isolated work | `delegate_task` |
| Batch independent tool calls | `multi_tool_use.parallel` |
| Change desktop workspace | `project_create` / `project_switch` (not a git worktree) |

## Delegation limits

A `delegate_task` child has no parent-session memory. Goals and context must be self-contained. The current per-call API does not select a model; model routing and concurrency come from Hermes delegation configuration. If concurrency is one, execute sequentially and never claim parallel fan-out.

Subagents cannot use `clarify`. Keep interactive decisions in the parent session.

## Bootstrap decision

Claude's `SessionStart` hook is not copied. Hermes already injects the skill index and requires relevant skill loading. Functional equivalence must be checked in fresh-session acceptance transcripts. If this is not reliable enough, add only a supported Hermes-native startup/plugin mechanism; do not emulate `CLAUDE_PLUGIN_ROOT` or `hookSpecificOutput`.

## Git and safety

Skills may inspect git and offer integration choices. They must not commit, stage, push, merge, open a PR, delete a branch, or remove a worktree unless the user explicitly requests the action. Desktop Projects are workspace navigation, not isolation.
