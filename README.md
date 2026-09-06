# sdd-skill

A Claude Code skill that runs a full spec-driven pipeline — from a vague idea to merged tickets — with subagents doing the implementation and a human keeping control.

*[Читать по-русски](README.ru.md)*

**The instructions themselves are written in Russian.** Claude executes them the same either way, but if you want to read and edit what you are running, you will need a translation — see [Language](#language) below.

## What it is

You describe what you want. The skill then runs an interview until nothing is assumed silently, writes a spec into your tracker, cuts it into tracing slices, dispatches a fresh agent per ticket into its own git worktree, merges them linearly, and keeps a handoff document current so that hitting a context limit costs you nothing.

It is deliberately **not** a "build my app while I sleep" button. Every product fork is a question with one recommendation attached; every taste question is answered by looking at a mockup; every merge is verified by the coordinator with its own commands rather than trusted from an agent's report.

## It is a layer, not a replacement

This skill orchestrates the **mattpocock-skills** plugin (`ask-matt`, `to-spec`, `to-tickets`, `implement`, `tdd`, `code-review`, `grilling`, `domain-modeling`). Those skills define the flow; this one defines how to run it with agents and a human in the loop. Install both — the skill assumes the plugin is there.

## The pipeline

| # | Step | Done when |
|---|---|---|
| 1 | Repository is ready | `CLAUDE.md` and agent docs exist, every command in them actually runs |
| 2 | Interview until the frontier is empty | No branch of the decision tree is assumed silently; terms in `CONTEXT.md`, decisions in ADRs |
| 3 | Seams agreed | The human has approved what gets automated tests and what can only be checked by hand |
| 4 | Spec in the tracker | One issue, labelled, linking the glossary, ADRs, research reports and mockups |
| 5 | Tickets are tracing slices | Published blockers-first with native tracker dependencies |
| 6 | Handoff document exists | Written **before** the first executor, not before the context runs out |
| 7 | Executors implement | One fresh agent per ticket, each in its own worktree |
| 8 | Accept and merge | Claims re-verified on the branch, merged fast-forward only, ticket closed with evidence |
| 9 | Human gates | Taste content approved in full; manual acceptance through the same door a user walks through |
| 10 | Trace | What was decided, what was refused, what permissions were granted |

## What it adds over just asking an agent to build things

Every item below is a scar, not a preference:

- **One recommendation per question, never a menu.** A round of questions is accepted with a single "ok"; disagreeing means naming a number.
- **The coordinator fetches facts before asking.** Anything readable in files, code or docs is read first; primary-source research runs as a background agent while the rounds continue.
- **Taste is settled by looking.** Layout, palette and tone are answered against a real mockup in the project's real tokens, with a difference table in numbers. Taste questions are never delegated to a subagent — a subagent cannot show you a picture.
- **A worktree per executor**, including the one who nominally "works on the main branch". This kills three problems at once: mixed-up staging, races over the same files, and agents killing each other's processes.
- **A living handoff document**, updated after every merge — plus a hook that nags when it falls behind the code. Model limits and closed terminals arrive without warning; a fresh handoff makes them free.
- **Linear merges only** (`rebase` then `--ff-only`), and when an executor's base moved underneath it, `rebase --onto <target> <old blocker tip> <branch>` — with the old hash recorded in the handoff at the moment it moved, not hunted for in the reflog later.
- **A dropped executor's uncommitted files are value, not garbage.** They get listed in the handoff and handed to the next agent with "continue this draft, do not rewrite it".
- **Exit codes are read alone.** A command whose exit code *is* the answer runs without a `; echo; tail` after it — otherwise the shell reports the tail's success and a failed release reads as green. That one happened.
- **Permission is asked once per class of action, then written down.** Push, release, deploy, restart — once granted, the coordinator does them instead of handing the chore back to the human. Product decisions and anything requiring the human's own credentials stay with the human.
- **Credentials are never requested in chat.** A secret is entered where it is read — stdin or a form. If one appears in the conversation, the coordinator says so and recommends rotation.
- **Acceptance goes through the same door the user walks through.** Green tests do not prove a product works; a platform matrix is part of that door.

## Install

```bash
# 1. the pipeline this skill orchestrates
claude plugin marketplace add anthropics/claude-plugins-official
claude plugin install mattpocock-skills@claude-plugins-official

# 2. the skill itself
git clone https://github.com/IulaiJedi/sdd-skill ~/.claude/skills/sdd
```

Then start a session and type `/sdd`, or just say "run this by SDD" / «по SDD».

### Optional: the staleness hook

`handoff-stale.sh` reminds you to refresh the handoff document once it falls behind the code. It stays silent everywhere except a git repository that actually holds a `docs/handoff-*.md`, and any surprise makes it exit quietly — it nags, it never blocks. Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      { "hooks": [ { "type": "command", "command": "~/.claude/skills/sdd/handoff-stale.sh" } ] }
    ],
    "PreCompact": [
      { "hooks": [ { "type": "command", "command": "~/.claude/skills/sdd/handoff-stale.sh" } ] }
    ]
  }
}
```

Use an absolute path if `~` is not expanded in your setup. The threshold is three commits by default; `SDD_HANDOFF_THRESHOLD` changes it.

## Files

| File | What is in it |
|---|---|
| `SKILL.md` | The pipeline: roles, ten steps, what "done" means for each |
| `interview.md` | How a round runs: questions with recommendations, plain language, mockups, background research |
| `coordinator.md` | Publishing tickets, worktrees, dispatching, accepting a report, merging, recovering a dropped executor |
| `handoff.md` | What goes in the handoff document and when it is updated |
| `implement-agent-prompt.md` | The template for an executor's prompt — self-contained, because the executor starts with an empty context |
| `handoff-stale.sh` | The hook described above |

## Requirements

- Claude Code with the `mattpocock-skills` plugin
- `git` — worktrees are load-bearing here, not optional
- `gh` (GitHub CLI) if you want the tracker half; without a remote, tickets can live as files
- A repository you are willing to let agents commit into (they commit to their own branches and never push)

## Language

The skill's instructions are in Russian. That is not an oversight — they were written and sharpened in the language they are used in, and a second copy of 500 lines of process text would drift from the first one within weeks. Claude follows them regardless of the language you speak to it in.

If you want an English translation, a pull request adding `en/` is welcome — with the understanding that whichever copy stops being used will eventually be wrong.

## Where it comes from

Extracted from a real milestone rather than imagined: twelve tickets, fourteen background agents, a desktop application designed, built and released. The rules above are what that run cost. It is expensive for small work — for a two-file fix, skip the pipeline entirely.

## Credits and licence

The pipeline this skill drives is [Matt Pocock's skills](https://github.com/anthropics/claude-plugins-official), distributed through Anthropic's official plugin marketplace. This repository only adds the layer for running it with agents.

MIT — see [LICENSE](LICENSE).
