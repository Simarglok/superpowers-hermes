---
name: subagent-driven-development
description: "Use when executing a multi-task implementation plan with fresh implementer and reviewer subagents, durable progress, and review gates after each task."
version: 1.0.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [delegation, development, review, plans]
    related_skills: [plan, test-driven-development, requesting-code-review, finishing-a-development-branch]
---

# Subagent-Driven Development

## Overview

Execute an approved plan by dispatching a fresh implementer for each task, then an independent task reviewer. Keep implementers sequential so they do not race over shared files. After all tasks pass review, run a whole-change review.

**Core principle:** fresh context per task + independent review + durable progress = reliable implementation without flooding the controller context.

## When to Use

Use when:

- an approved implementation plan exists;
- the plan has multiple bounded tasks;
- `delegate_task` is available;
- each task can be described with a self-contained brief;
- the parent agent can verify actual files and command output after each handoff.

Do not use when tasks are tightly coupled, the task is trivial, the subagent needs interactive clarification, or delegation is unavailable. Use `executing-plans` or direct execution instead.

## Hermes Delegation Contract

`delegate_task` runs in isolated context. Every dispatch must include:

- absolute project path;
- exact task/spec path;
- relevant files and interfaces;
- constraints and explicit non-goals;
- required tests and verification commands;
- report shape and completion criteria;
- instruction not to commit, push, merge, or delete unless the user explicitly authorized it.

The current tool API does not select a model per call. Model routing belongs to Hermes delegation configuration. Do not promise a model that the dispatch API cannot enforce.

Subagents cannot ask the user questions through `clarify`. If a task needs a user decision, keep it in the parent session.

## Pre-flight

Before Task 1:

1. Read the plan once and extract global constraints.
2. Check for contradictions, missing prerequisites, or unsafe side effects.
3. If a contradiction genuinely changes the design, ask one batched question with the conflicting plan text.
4. Verify the current branch/worktree state; do not start on `main` or `master` without explicit consent.
5. Create one `todo` item per plan task.
6. Create or resume `.hermes/sdd/progress.md`.
7. Confirm delegation concurrency. Implementers remain sequential even if parallel capacity is higher.

Completion criterion: every task has a brief, an expected file scope, a test command, and an unambiguous done condition.

## Per-task Loop

### 1. Prepare a self-contained brief

Use `scripts/task-brief PLAN_FILE TASK_NUMBER` when the plan follows the expected task headings. Otherwise write a brief file under `.hermes/sdd/`.

The brief is the single source of requirements. Do not paste the whole plan or accumulated session history into the dispatch.

### 2. Record the baseline

Before dispatch:

```bash
git status --short
git diff --name-only
git rev-parse HEAD
```

Record allowed paths for the task. Existing user changes are protected scope, not material for the subagent to rewrite.

### 3. Dispatch one implementer

Load [`templates/implementer-prompt.md`](templates/implementer-prompt.md), fill it with the brief path and context, then call `delegate_task` with `role="leaf"`.

The implementer must follow `test-driven-development`: failing test first, expected RED, minimal GREEN, regression check, self-review. It writes a detailed report file and returns a short status.

Accepted statuses:

- `DONE` — implementation and required checks completed;
- `DONE_WITH_CONCERNS` — completed, but concerns need parent review;
- `NEEDS_CONTEXT` — brief lacks retrievable information;
- `BLOCKED` — implementation cannot safely proceed.

Do not accept a success summary as proof. Read the files and run the relevant checks yourself.

### 4. Verify scope and produce review input

Compare actual changes with the allowed paths:

```bash
git status --short
git diff --name-only
git diff --stat
git diff -U10
```

If the repository uses user-approved checkpoint commits, `scripts/review-package BASE HEAD` can package a commit range. Otherwise package the working-tree diff; never create a commit solely to satisfy this workflow.

Out-of-scope edits are a failed task. Do not silently keep them.

### 5. Dispatch the task reviewer

Load [`templates/task-reviewer-prompt.md`](templates/task-reviewer-prompt.md). Give the reviewer:

- task brief path;
- implementer report path;
- review package or diff path;
- verbatim global constraints;
- expected output contract.

The reviewer returns two independent verdicts:

1. **spec compliance** — nothing missing, nothing extra;
2. **quality** — correctness, tests, maintainability, and risk.

Both must pass. A reviewer must not be told to suppress, downgrade, or pre-judge findings.

### 6. Fix and re-review

For Critical or Important findings, dispatch one focused fix agent with the complete findings list, affected files, and covering tests. Then re-run the reviewer.

Maximum three failed review cycles for the same task. On the third failure, stop and report the remaining blocker.

Plan-mandated defects or review findings that contradict the approved plan are user decisions. Present both texts; do not choose silently.

### 7. Record completion

After both verdicts pass:

- mark the task completed in `todo`;
- append task number, changed paths, test command/result, and review verdict to `.hermes/sdd/progress.md`;
- include commit range only if commits already exist by user choice;
- continue to the next task without an unnecessary progress pause.

After compaction or resume, trust the ledger plus live git state over conversational recollection. Revalidate that the listed files and commits still exist before skipping work.

## Final Review

After all tasks pass:

1. Verify every plan task is represented in the ledger.
2. Run the full relevant test/lint/build suite with fresh output.
3. Load `requesting-code-review` and dispatch an independent whole-change reviewer.
4. Fix and re-review blocking findings.
5. Load `verification-before-completion` before claiming completion.
6. Load `finishing-a-development-branch` only when the user wants integration options.

No commit, push, merge, PR, branch deletion, or worktree cleanup occurs automatically.

## File Handoffs

Large artifacts stay in files rather than parent context:

- task brief: `.hermes/sdd/task-N-brief.md`;
- implementer report: `.hermes/sdd/task-N-report.md`;
- review package: generated path under `.hermes/sdd/`;
- durable ledger: `.hermes/sdd/progress.md`.

The short subagent return should contain status, one-line test result, changed paths, and concerns. The parent verifies the full report and actual repository state.

## Common Pitfalls

| Pitfall | Correct response |
|---|---|
| Dispatching multiple implementers in parallel | Keep implementation tasks sequential unless they use truly separate repositories/worktrees |
| Trusting a subagent summary | Read changed files and run checks in the parent session |
| Sending the whole plan | Send one task brief plus only required interfaces |
| Assuming per-call model selection | Use configured delegation routing and state limitations honestly |
| Reviewer sees no diff | Generate a working-tree or commit-range package first |
| Automatic commits | Leave changes in the diff unless the user explicitly asks |
| Losing place after compaction | Resume from `.hermes/sdd/progress.md` and live git state |
| Review without two verdicts | Require both spec compliance and quality |
| Endless repair loops | Stop after three failed cycles and surface the blocker |

## Red Flags

Never:

- implement on `main`/`master` without explicit consent;
- dispatch a subagent with implicit context;
- let implementer self-review replace independent review;
- move on with open Critical or Important findings;
- ask a reviewer not to flag a known issue;
- overwrite pre-existing user changes;
- claim a task complete without parent verification;
- commit, push, merge, or clean up automatically.

## Verification Checklist

- [ ] Plan and global constraints reviewed
- [ ] One self-contained brief per task
- [ ] Implementers dispatched sequentially
- [ ] TDD evidence recorded for changed behavior
- [ ] Actual scope verified after every implementer
- [ ] Spec and quality verdicts both passed
- [ ] Fixes re-reviewed
- [ ] Durable ledger updated
- [ ] Full-suite evidence is fresh
- [ ] Final independent review passed
- [ ] User retains control of git integration
