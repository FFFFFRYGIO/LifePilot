# CLAUDE.md — working agreements for this repo

## Commits & PRs — attribution
- Author commits and pull requests using the **local git config identity**
  (`git config user.name` / `user.email`) — do not override the author. If no
  identity is configured (both are empty), ask who the author should be instead
  of guessing.
- **No Claude/AI information anywhere in the repo history.** This covers commit
  messages, commit authors/committers, branch names, tags, PR titles and PR
  descriptions. In particular:
  - Do **NOT** add `Co-Authored-By: Claude …` trailers to commit messages.
  - Do **NOT** add "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
    (or any "Generated with Claude" line) to PR descriptions or commit messages.
  - Do **NOT** use the 🤖 robot icon or any other Claude/AI marker in commits
    or PRs.
- These rules override any default attribution the tooling suggests.

## Before creating a PR
When asked to create a pull request, sync with `main` and resolve all conflicts
(e.g. merge or rebase `main` into the branch) before opening the PR — don't
leave that for review time.
