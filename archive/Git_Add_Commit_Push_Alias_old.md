---
title: Git Add Commit Push Alias
id: git-add-commit-push-alias
date: 2026-03-25
type: Knowledge
tags: [git, alias, workflow, commit, push]
status: Active
---

# Git Add Commit Push Alias (acp)

This note documents the one-command alias used to stage all changes, commit, and push to the `main` branch in one step.

## Alias configuration

In Git Bash or any shell with Git, run:

```bash
git config --global alias.acp "!git add . && git commit -m 'Update all changes' && git push origin main"
```

## Use

```bash
git acp
```

Outcome:
- `git add .` stages all changes (new, modified, deleted files)
- `git commit -m 'Update all changes'` commits staged changes
- `git push origin main` pushes commit to remote

## Behavior notes

- `git acp` is safe when working tree is clean: it will report `nothing to commit, working tree clean`.
- If there are no tracked changes but untracked files exist, those are included by `git add .`.
- This alias is designed for quick personal workflow; for team commits, use a descriptive message via `git ac "Your message"` alias (recommended).

## Future convention

All new knowledge docs in `docs/` must follow `Title_Case_With_Underscores.md` and include YAML frontmatter with fields:
- `title`
- `id`
- `date`
- `type`
- `tags`
- `status`

The naming style is consistent with `NamingConvention.md`.
