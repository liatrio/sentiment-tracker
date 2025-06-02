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

### Step 3: Identify GitHub user
I'll determine who you are on GitHub to properly assign issues and PRs.
```
mcp1_get_me

Now that I know your GitHub identity, I'll use this information for the issue and PR creation.
```

### Step 4: Create GitHub issue
I'll create a GitHub issue to track this task with comprehensive context.
```
mcp1_create_issue --owner="{{repoOwner}}" --repo="{{repoName}}" --title="Implement {{taskTitle}}" --body="## Task Description\n\n{{taskDescription}}\n\n## Implementation Details\n\n{{taskDetails}}\n\n## Dependencies\n\n{{taskDependencies}}\n\n## Test Strategy\n\n{{testStrategy}}"

I've created issue #{{issueNumber}} to track this task.
```

### Step 5: Create feature branch
I'll create a local feature branch following the naming convention.
```
mcp0_git_create_branch --repo_path="{{projectRoot}}" --branch_name="{{taskType}}/{{taskSlug}}-{{issueNumber}}" --base_branch="main"
mcp0_git_checkout --repo_path="{{projectRoot}}" --branch_name="{{taskType}}/{{taskSlug}}-issue-{{issueNumber}}"

I've created and checked out branch '{{taskType}}/{{taskSlug}}-{{issueNumber}}'.
```

### Step 6: Implement subtasks
I'll iteratively implement each subtask following TDD principles.
```
mcp3_get_task --projectRoot="{{projectRoot}}" --id="{{taskId}}"

Let's work through each subtask one by one:

{{#each subtasks}}
  # Working on subtask {{this.id}}: {{this.title}}

  ## Subtask evaluation
  Let me check if this subtask is already completed:
  mcp3_get_task --projectRoot="{{projectRoot}}" --id="{{this.id}}"

  {{#if this.status == "done"}}
    This subtask is already completed. Moving to the next one.
  {{else}}
    ## TDD approach
    1. First, I'll write tests for this functionality
    2. Then implement the code to make the tests pass
    3. Finally refactor while maintaining test coverage

    ## Implementation
    {{this.details}}

    ## Verification
    Let me verify the implementation passes tests and linting:
    run_command --Blocking=true --CommandLine="npm run lint" --Cwd="{{projectRoot}}"
    run_command --Blocking=true --CommandLine="npm test" --Cwd="{{projectRoot}}"

    ## Commit changes
    mcp0_git_add --repo_path="{{projectRoot}}" --files=["."]
    mcp0_git_commit --repo_path="{{projectRoot}}" --message="{{commitType}}({{scope}}): {{this.title}} #{{issueNumber}}"

    ## Update subtask status
    mcp3_set_task_status --projectRoot="{{projectRoot}}" --id="{{this.id}}" --status="done"
  {{/if}}
{{/each}}
```

### Step 7: Push branch to remote
I'll push the local branch to the remote repository.
```
run_command --Blocking=true --CommandLine="git push -u origin {{taskType}}/{{taskSlug}}-{{issueNumber}}" --Cwd="{{projectRoot}}"

Your branch has been pushed to the remote repository.
```

### Step 8: Create pull request
I'll create a pull request with a conventional commit title that links to the GitHub issue.
```
mcp1_create_pull_request --owner="{{repoOwner}}" --repo="{{repoName}}" --base="main" --head="{{taskType}}/{{taskSlug}}-{{issueNumber}}" --title="{{commitType}}({{scope}}): {{taskTitle}} #{{issueNumber}}" --body="## Description\n\n{{taskDescription}}\n\n## Implementation Details\n\n{{taskDetails}}\n\n## Testing\n\n{{testStrategy}}\n\nCloses #{{issueNumber}}"

I've created a pull request for your changes. You can review and merge it when ready.
```

### Step 9: Update task status
I'll update the task status to 'done' in taskmaster.
```
mcp3_set_task_status --projectRoot="{{projectRoot}}" --id="{{taskId}}" --status="done"

Task {{taskId}} has been marked as completed!
```
