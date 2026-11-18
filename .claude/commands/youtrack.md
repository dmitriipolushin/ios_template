---
description: "Query YouTrack issues. Use when: 'show tasks', 'youtrack', 'show issues', 'what tasks', 'задачи', 'тикеты'."
argument-hint: "[issue ID or search query]"
allowed-tools: [Bash, Read]
---

# YouTrack

Query YouTrack issues via REST API.

## Configuration

Before first use, set these env vars in your shell profile (`~/.zshrc` / `~/.bashrc`):

```bash
export YOUTRACK_URL="https://youtrack.example.com"
export YOUTRACK_TOKEN="perm:..."           # issue token in YouTrack: Profile → Account Security → New Token
export YOUTRACK_PROJECT="XX"               # project short name prefix (e.g. "TA", "PROJ")
```

If any of these is missing — stop and ask the user to set them. Never commit tokens to the repo.

## Usage

Based on `$ARGUMENTS`, determine the action:

### 1. Get specific issue (e.g. "PROJ-3" or just "3")

```bash
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" \
  "$YOUTRACK_URL/api/issues/$ISSUE_ID?fields=idReadable,summary,description,customFields(name,value(name))"
```

If user passes just a number, prefix with `$YOUTRACK_PROJECT-`.

### 2. List issues (e.g. "all", "open", or a search query)

```bash
curl -s -H "Authorization: Bearer $YOUTRACK_TOKEN" \
  "$YOUTRACK_URL/api/issues?fields=idReadable,summary,customFields(name,value(name))&query=QUERY&\$top=25"
```

Common queries:
- All open: `State: Open,In Progress`
- By assignee: `Assignee: me`
- By tag: `tag: MVP`
- Custom: pass user's text as query

### 3. No arguments — show all open issues

Use query `State: -Resolved,-Done,-Cancelled` to show active tasks.

## Response Format

Present results as a clean table in Russian:

| ID | Задача | Статус |
|----|--------|--------|

For single issue — show full description and all custom fields.

## Rules

- Read token and URL from env vars only. Never hardcode.
- Present results concisely in Russian.
- If API returns error, show the error and suggest checking the query.
- For issue IDs, accept both `PROJ-3` and `3` formats (prefix with `$YOUTRACK_PROJECT-` if needed).
