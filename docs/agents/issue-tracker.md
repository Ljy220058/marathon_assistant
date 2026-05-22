# Issue Tracker

Issues and PRDs for this repo live in GitHub Issues for `Ljy220058/marathon_assistant`.

## Conventions

- Create issues with `gh issue create --title "..." --body "..."`.
- Read issues with `gh issue view <number> --comments`.
- List issues with `gh issue list --state open --json number,title,body,labels,comments`.
- Comment with `gh issue comment <number> --body "..."`.
- Apply labels with `gh issue edit <number> --add-label "..."`.
- Remove labels with `gh issue edit <number> --remove-label "..."`.
- Close issues with `gh issue close <number> --comment "..."`.

Run `gh` commands from the repo root so the CLI infers the repository from `origin`.

## Skill Integration

When a skill says "publish to the issue tracker", create a GitHub issue.

When a skill says "fetch the relevant ticket", use `gh issue view <number> --comments`.
