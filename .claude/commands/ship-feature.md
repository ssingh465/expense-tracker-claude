---
description: Commit staged/unstaged changes and raise a GitHub Pull Request
argument-hint: "Optional commit message override"
allowed-tools: Read, Bash(git:*, gh:*)
---

You are a senior developer finalizing a feature or fix for the Spendly expense tracker. Your goal is to move changes from the working directory to a merged PR on GitHub, following professional commit standards.

User input: $ARGUMENTS

## Step 1 — Analyze Changes
Run `git status` and `git diff` (including `--cached` if changes are already staged) to understand the exact modifications. 
Read the modified files if necessary to grasp the context and ensure no debug logs or temporary code are being committed.

## Step 2 — Propose Commit Message
Generate a commit message following the Conventional Commits specification:
- **Format**: `<type>(<scope>): <description>`
- **Types**: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`, `style:`, `test:`
- **Description**: Imperative mood, present tense, no period at the end.
- **Trailer**: Always append the mandatory co-author line:
  `Co-Authored-By: Claude <noreply@anthropic.com>`

If $ARGUMENTS contains a message, use it as the basis but ensure it follows the format. Otherwise, propose a message based on your analysis.

Present the proposed message to the user and wait for approval.

## Step 3 — Execute Commit
Once approved:
1. Run `git add .` to stage all changes (unless the user specifies certain files).
2. Run `git commit -m "<proposed_message>"`.

## Step 4 — Push and Raise PR
1. Identify the current branch name.
2. Push the branch: `git push origin <branch_name>`.
3. Create the PR using the GitHub CLI (`gh`):
   - **Title**: Use the first line of the commit message.
   - **Body**: Provide a concise summary of the changes.
   - **Footer**: Always include: `🤖 Generated with [Claude Code](https://claude.com/claude-code)`
   - Use `gh pr create --title "<title>" --body "<body>"` to avoid interactive prompts.

## Step 5 — Finalize
Output the URL of the created Pull Request to the user.
