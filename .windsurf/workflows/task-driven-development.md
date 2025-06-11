---
description: agentic development workflow that leverages git, github, and taskmaster-ai
---

# Task-Driven Development Workflow

## Description
This workflow automates the task-driven development process by combining taskmaster-ai, git, and GitHub tools. It ensures a clean working tree, identifies the next task, creates GitHub issues for tracking, maintains proper branch naming, and follows TDD principles for implementation, before creating a pull request with conventional commit messages.

## Steps

### Step 1: Verify clean working tree
I'll check if your git working tree is clean before proceeding.
```
mcp0_git_status --repo_path="{{projectRoot}}"

If there are uncommitted changes, I'll stop and ask you to commit or stash them first. Otherwise, I'll continue to the next step.
```

### Step 2: Get next task from taskmaster
I'll identify the next task you should work on based on dependencies and status.
```
mcp3_next_task --projectRoot="{{projectRoot}}"

Let me examine the task and its details to understand what we need to implement.
```

### Step 3: Present implementation plan for approval
I'll draft a short plan specifying **exactly one** pending subtask of the next task that will be tackled, including the branch name and high-level steps. I'll present this plan to you for approval **before** creating any branches or writing code.

_I will wait for your confirmation before continuing._

### Step 4: Identify GitHub user
I'll determine who you are on GitHub to properly assign issues and PRs.
```
mcp1_get_me

Now that I know your GitHub identity, I'll use this information for the issue and PR creation.
```

### Step 5: Create GitHub issue
I'll create a GitHub issue to track this task with comprehensive context.
```
mcp1_create_issue --owner="{{repoOwner}}" --repo="{{repoName}}" --title="Implement {{taskTitle}}" --body="## Task Description\n\n{{taskDescription}}\n\n## Implementation Details\n\n{{taskDetails}}\n\n## Dependencies\n\n{{taskDependencies}}\n\n## Test Strategy\n\n{{testStrategy}}"

I've created issue #{{issueNumber}} to track this task.
```

### Step 6: Create feature branch for the chosen subtask
I'll create a local feature branch for **the approved subtask only** using the naming convention:
```
<type>/<subtask-slug>-<issueNumber>
```
For example, `feat/sentiment-analysis-123`.
```
mcp0_git_create_branch --repo_path="{{projectRoot}}" --branch_name="{{taskType}}/{{subtaskSlug}}-{{issueNumber}}" --base_branch="main"
mcp0_git_checkout --repo_path="{{projectRoot}}" --branch_name="{{taskType}}/{{subtaskSlug}}-{{issueNumber}}"

I've created and checked out branch '{{taskType}}/{{subtaskSlug}}-{{issueNumber}}'.
```

### Step 7: Implement the chosen subtask
I'll implement **only the selected subtask** following TDD principles. After it is completed and merged, the workflow will repeat from Step 2 to pick the next subtask.
```
mcp3_get_task --projectRoot="{{projectRoot}}" --id="{{taskId}}"

Let's work through this subtask:

## Subtask evaluation
Let me check if this subtask is already completed:
mcp3_get_task --projectRoot="{{projectRoot}}" --id="{{subtaskId}}"

{{#if subtask.status == "done"}}
  This subtask is already completed. Moving to the next one.
{{else}}
  ## TDD approach
  1. First, I'll write tests for this functionality
  2. Then implement the code to make the tests pass
  3. Finally refactor while maintaining test coverage

  ## Implementation
  {{subtask.details}}

  ## Verification
  Let me verify the implementation passes tests and linting:
  run_command --Blocking=true --CommandLine="npm run lint" --Cwd="{{projectRoot}}"
  run_command --Blocking=true --CommandLine="npm test" --Cwd="{{projectRoot}}"

  ## Commit changes
  mcp0_git_add --repo_path="{{projectRoot}}" --files=["."]
  mcp0_git_commit --repo_path="{{projectRoot}}" --message="{{commitType}}({{scope}}): {{subtask.title}} #{{issueNumber}}"

  ## Update subtask status
  mcp3_set_task_status --projectRoot="{{projectRoot}}" --id="{{subtaskId}}" --status="done"
{{/if}}
```

### Step 8: Push branch to remote
I'll push the local branch to the remote repository.
```
run_command --Blocking=true --CommandLine="git push -u origin {{taskType}}/{{subtaskSlug}}-{{issueNumber}}" --Cwd="{{projectRoot}}"

Your branch has been pushed to the remote repository.
```

### Step 9: Create pull request
I'll create a pull request with a conventional commit title that links to the GitHub issue.
```
mcp1_create_pull_request --owner="{{repoOwner}}" --repo="{{repoName}}" --base="main" --head="{{taskType}}/{{subtaskSlug}}-{{issueNumber}}" --title="{{commitType}}({{scope}}): {{taskTitle}} #{{issueNumber}}" --body="## Description\n\n{{taskDescription}}\n\n## Implementation Details\n\n{{taskDetails}}\n\n## Testing\n\n{{testStrategy}}\n\nCloses #{{issueNumber}}"

I've created a pull request for your changes. You can review and merge it when ready.
```

### Step 10: Update task status
I'll update the task status to 'done' in taskmaster.
```
mcp3_set_task_status --projectRoot="{{projectRoot}}" --id="{{taskId}}" --status="done"

Task {{taskId}} has been marked as completed!
```
