# Requirements Document

## Introduction

Local Autonomous AI Developer Agent adalah script Python yang berjalan di mesin lokal Mac untuk mengotomatisasi penanganan GitHub Issues dan Pull Request reviews. Agent menggunakan Gemini API untuk menghasilkan solusi kode, PyGithub untuk interaksi dengan GitHub API, dan GitPython untuk operasi Git lokal. Agent memiliki akses ke source code lokal yang sudah di-clone dan dapat membuat branch, melakukan perubahan kode, serta membuat Pull Request secara otomatis.

## Glossary

- **Agent**: Script Python yang menjalankan autonomous AI developer workflow
- **Issue_Handler**: Komponen yang menangani GitHub Issues yang di-assign
- **PR_Handler**: Komponen yang menangani Pull Request dengan status changes requested
- **Gemini_Client**: Komponen yang berkomunikasi dengan Gemini API
- **GitHub_Client**: Komponen yang berkomunikasi dengan GitHub API via PyGithub
- **Git_Manager**: Komponen yang mengelola operasi Git lokal via GitPython
- **Configuration**: Object yang menyimpan GEMINI_API_KEY, GITHUB_TOKEN, REPO_NAME, LOCAL_DIR_PATH, dan DEFAULT_TARGET_BASE_BRANCH
- **Solution_JSON**: Format JSON yang dikembalikan Gemini API berisi file path dan konten perbaikan
- **Base_Branch**: Branch target untuk Pull Request (configurable, default: main)

## Requirements

### Requirement 1: Configuration Management

**User Story:** As a developer, I want to configure the agent with API keys and repository settings, so that the agent can access GitHub and Gemini API.

#### Acceptance Criteria

1. THE Configuration SHALL load GEMINI_API_KEY from environment or config file
2. THE Configuration SHALL load GITHUB_TOKEN from environment or config file
3. THE Configuration SHALL load REPO_NAME in format 'org/repo-name'
4. THE Configuration SHALL load LOCAL_DIR_PATH pointing to cloned repository
5. THE Configuration SHALL load DEFAULT_TARGET_BASE_BRANCH with default value 'main'
6. IF any required configuration is missing, THEN THE Configuration SHALL raise a descriptive error

### Requirement 2: Detect Assigned Issues

**User Story:** As a developer, I want the agent to detect open issues assigned to me, so that the agent can automatically work on them.

#### Acceptance Criteria

1. WHEN the Agent starts, THE Issue_Handler SHALL query GitHub API for open issues
2. THE Issue_Handler SHALL filter issues assigned to the authenticated user
3. THE Issue_Handler SHALL retrieve issue number and description for each assigned issue
4. IF no assigned issues exist, THEN THE Issue_Handler SHALL log this status and continue to next workflow

### Requirement 3: Create Feature Branch from Issue

**User Story:** As a developer, I want the agent to create a dedicated branch for each issue, so that changes are isolated.

#### Acceptance Criteria

1. WHEN an assigned issue is detected, THE Git_Manager SHALL checkout to Base_Branch
2. THE Git_Manager SHALL pull latest changes from remote Base_Branch
3. THE Git_Manager SHALL create a new branch with format 'fix/issue-[issue_number]'
4. THE Git_Manager SHALL checkout to the newly created branch
5. IF branch creation fails, THEN THE Git_Manager SHALL log the error and skip to next issue

### Requirement 4: Generate Code Solution from Issue

**User Story:** As a developer, I want the agent to generate code solutions using AI, so that issues can be resolved automatically.

#### Acceptance Criteria

1. WHEN working on an issue, THE Issue_Handler SHALL read relevant files from LOCAL_DIR_PATH
2. THE Issue_Handler SHALL construct a prompt containing issue description and file contents
3. THE Gemini_Client SHALL send the prompt to Gemini API with system instructions for JSON output
4. THE Gemini_Client SHALL receive Solution_JSON containing file paths and updated contents
5. IF Gemini API returns non-JSON response, THEN THE Gemini_Client SHALL retry with stricter prompt
6. IF Gemini API fails after retries, THEN THE Gemini_Client SHALL log error and skip to next issue

### Requirement 5: Apply Code Changes Locally

**User Story:** As a developer, I want the agent to apply AI-generated changes to local files, so that the solution is ready for commit.

#### Acceptance Criteria

1. WHEN Solution_JSON is received, THE Issue_Handler SHALL parse the JSON structure
2. FOR each file in Solution_JSON, THE Issue_Handler SHALL overwrite the local file with new content
3. THE Issue_Handler SHALL preserve file permissions and encoding
4. IF file write fails, THEN THE Issue_Handler SHALL log error and rollback changes

### Requirement 6: Commit and Push Changes

**User Story:** As a developer, I want the agent to commit and push changes, so that they are available on GitHub.

#### Acceptance Criteria

1. WHEN local files are updated, THE Git_Manager SHALL stage all modified files with git add
2. THE Git_Manager SHALL create a commit with message format 'Fix issue #[issue_number]: [issue_title]'
3. THE Git_Manager SHALL push the branch to remote repository
4. IF push fails, THEN THE Git_Manager SHALL log error and skip Pull Request creation

### Requirement 7: Create Pull Request from Issue

**User Story:** As a developer, I want the agent to create a Pull Request automatically, so that changes can be reviewed.

#### Acceptance Criteria

1. WHEN changes are pushed, THE GitHub_Client SHALL create a Pull Request to Base_Branch
2. THE GitHub_Client SHALL set PR title to 'Fix issue #[issue_number]: [issue_title]'
3. THE GitHub_Client SHALL set PR body to reference the issue with 'Closes #[issue_number]'
4. THE GitHub_Client SHALL link the PR to the original issue
5. IF PR creation fails, THEN THE GitHub_Client SHALL log error with details

### Requirement 8: Detect Pull Requests with Changes Requested

**User Story:** As a developer, I want the agent to detect PRs that need revisions, so that the agent can address reviewer feedback.

#### Acceptance Criteria

1. WHEN the Agent starts, THE PR_Handler SHALL query GitHub API for Pull Requests created by authenticated user
2. THE PR_Handler SHALL filter PRs with latest review state 'CHANGES_REQUESTED'
3. THE PR_Handler SHALL retrieve PR number, branch name, and review comments
4. IF no PRs with changes requested exist, THEN THE PR_Handler SHALL log this status

### Requirement 9: Synchronize Local Repository with PR Branch

**User Story:** As a developer, I want the agent to work on the correct PR branch, so that fixes are applied to the right place.

#### Acceptance Criteria

1. WHEN processing a PR with changes requested, THE Git_Manager SHALL checkout to the PR branch
2. THE Git_Manager SHALL pull latest changes from remote PR branch
3. IF checkout or pull fails, THEN THE Git_Manager SHALL log error and skip to next PR

### Requirement 10: Generate Code Fixes from Review Comments

**User Story:** As a developer, I want the agent to generate fixes based on reviewer feedback, so that PR can be approved.

#### Acceptance Criteria

1. WHEN processing review comments, THE PR_Handler SHALL read current file contents from LOCAL_DIR_PATH
2. THE PR_Handler SHALL construct a prompt containing review comments and file contents
3. THE Gemini_Client SHALL send the prompt to Gemini API with system instructions for JSON output
4. THE Gemini_Client SHALL receive Solution_JSON containing file paths and updated contents
5. IF Gemini API returns non-JSON response, THEN THE Gemini_Client SHALL retry with stricter prompt
6. IF Gemini API fails after retries, THEN THE Gemini_Client SHALL log error and skip to next PR

### Requirement 11: Apply Review Fixes and Update PR

**User Story:** As a developer, I want the agent to apply fixes and update the PR, so that reviewers can see the changes.

#### Acceptance Criteria

1. WHEN Solution_JSON is received for PR fixes, THE PR_Handler SHALL parse the JSON structure
2. FOR each file in Solution_JSON, THE PR_Handler SHALL overwrite the local file with new content
3. THE Git_Manager SHALL stage all modified files with git add
4. THE Git_Manager SHALL create a commit with message 'Address review comments'
5. THE Git_Manager SHALL push the commit to the same PR branch
6. IF push fails, THEN THE Git_Manager SHALL log error and skip re-request review

### Requirement 12: Re-request Review from Reviewers

**User Story:** As a developer, I want the agent to notify reviewers after fixes are applied, so that they can review again.

#### Acceptance Criteria

1. WHEN fixes are pushed to PR branch, THE GitHub_Client SHALL identify reviewers who requested changes
2. THE GitHub_Client SHALL re-request review from those reviewers via GitHub API
3. IF re-request fails, THEN THE GitHub_Client SHALL log error with details

### Requirement 13: Error Handling and Logging

**User Story:** As a developer, I want the agent to handle errors gracefully, so that one failure does not stop the entire workflow.

#### Acceptance Criteria

1. WHEN any component encounters an error, THE Agent SHALL log the error with timestamp and context
2. THE Agent SHALL continue processing remaining issues or PRs after an error
3. THE Agent SHALL provide a summary of successful and failed operations at completion
4. IF a critical error occurs, THEN THE Agent SHALL exit with non-zero status code

### Requirement 14: Gemini API System Prompt Configuration

**User Story:** As a developer, I want to configure Gemini's behavior, so that it returns valid JSON consistently.

#### Acceptance Criteria

1. THE Gemini_Client SHALL use a system prompt instructing JSON-only output
2. THE Gemini_Client SHALL specify JSON schema in the prompt with file_path and content fields
3. THE Gemini_Client SHALL configure temperature and other parameters for deterministic output
4. THE Gemini_Client SHALL validate response is valid JSON before returning
5. IF response is not valid JSON, THEN THE Gemini_Client SHALL extract JSON from markdown code blocks if present
