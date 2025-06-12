# Develop Subtask

This workflow helps develop a subtask from start to finish, including testing and pre-commit checks, leveraging MCP servers for git, GitHub, and taskmaster operations.

## Prerequisites
- Task and subtask must be identified in the chat context
- Working directory must be clean (no uncommitted changes)
- Taskmaster MCP server must be available
- GitHub MCP server must be available

## Steps

### Step 1: Verify Context and Working Directory
```
mcp3_get_task --projectRoot="{{projectRoot}}" --id="{{subtaskId}}"
```
- If task/subtask not found, abort with: "Task context not found. Please identify the task and subtask first."

```
mcp0_git_status --repo_path="{{projectRoot}}"
```
- If there are uncommitted changes, abort with: "Working directory is not clean. Please commit or stash changes before running this workflow."

### Step 2: Sync with Main Branch
```
mcp0_git_checkout --repo_path="{{projectRoot}}" --branch_name="main"
mcp0_git_pull --repo_path="{{projectRoot}}" --remote="origin" --branch="main"
```

### Step 3: Create Feature Branch
```
# Get subtask details
mcp3_get_task --projectRoot="{{projectRoot}}" --id="{{subtaskId}}"

# Create branch name from subtask title (kebab-case)
{{#assign branchName = "feat/" + subtaskId + "-" + (subtask.title | kebabcase)}}

# Create and checkout branch
mcp0_git_create_branch --repo_path="{{projectRoot}}" --branch_name="{{branchName}}" --base_branch="main"
mcp0_git_checkout --repo_path="{{projectRoot}}" --branch_name="{{branchName}}"
```

### Step 4: Development
```
# Get subtask details for context
mcp3_get_task --projectRoot="{{projectRoot}}" --id="{{subtaskId}}"

# Follow the implementation plan from the chat context
# Add detailed logging and documentation as you implement

# Example of adding a file with implementation
# write_to_file --TargetFile="{{filePath}}" --CodeContent="{{content}}" --EmptyFile=false
```

### Step 5: Write Unit Tests
```
# Create/update test files following TDD principles
# Example:
# write_to_file --TargetFile="tests/test_feature.py" --CodeContent="import pytest\n\ndef test_feature()\n    # Test implementation\n    assert True" --EmptyFile=false

# Run tests
run_command --Blocking=true --CommandLine="task test" --Cwd="{{projectRoot}}"
```

### Step 6: Run Pre-commit Checks
```
run_command --Blocking=true --CommandLine="task pre-commit-run" --Cwd="{{projectRoot}}"

# If there are issues, fix them and re-run tests
# run_command --Blocking=true --CommandLine="task test" --Cwd="{{projectRoot}}"
```

### Step 7: Stage and Commit Changes
```
# Stage all changes
mcp0_git_add --repo_path="{{projectRoot}}" --files=["."]

# Create conventional commit message
# feat(scope): brief description of changes
#
# More detailed description if needed.
#
# Related to subtask: {{subtaskId}}
mcp0_git_commit --repo_path="{{projectRoot}}" --message="feat({{scope}}): {{subtask.title}}\n\n{{subtask.details}}\n\nRelated to subtask: {{subtaskId}}"
```

### Step 8: Push Changes and Create PR (Optional)
```
# Push branch to remote
run_command --Blocking=true --CommandLine="git push -u origin {{branchName}}" --Cwd="{{projectRoot}}"

# Create PR (uncomment and fill in details)
# mcp1_create_pull_request --owner="{{repoOwner}}" --repo="{{repoName}}" --base="main" --head="{{branchName}}" --title="feat({{scope}}): {{subtask.title}}" --body="## Description\n\n{{subtask.details}}\n\n## Testing\n\nManual testing steps:\n1. \n2. \n3. \n\n## Related to\nSubtask: {{subtaskId}}"
```

### Step 9: Update Task Status
```
# Mark subtask as in-progress
mcp3_set_task_status --projectRoot="{{projectRoot}}" --id="{{subtaskId}}" --status="in-progress"

# When implementation is complete and tested:
# mcp3_set_task_status --projectRoot="{{projectRoot}}" --id="{{subtaskId}}" --status="done"
```

## Example Usage
```
/develop-subtask --subtaskId=1.2 --projectRoot=/path/to/repo --repoOwner=owner --repoName=repo --scope=auth
```

## Notes
- This workflow assumes the task and subtask context is already set in the chat
- All changes should be committed before running this workflow
