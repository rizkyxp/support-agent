# Implementation Plan: GitHub AI Agent

## Overview

Implementasi autonomous Python agent yang mengotomatisasi penanganan GitHub Issues dan Pull Request reviews menggunakan Gemini API untuk code generation, PyGithub untuk GitHub API interaction, dan GitPython untuk local Git operations.

## Tasks

- [x] 1. Setup project structure dan dependencies
  - Create directory structure (src/, tests/, config/)
  - Create requirements.txt dengan dependencies: google-generativeai, PyGithub, GitPython, python-dotenv, hypothesis (untuk testing)
  - Create .env.example file untuk configuration template
  - Create main entry point script
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 2. Implement Configuration Manager
  - [x] 2.1 Create Configuration class dengan data model
    - Implement dataclass untuk Configuration dengan fields: gemini_api_key, github_token, repo_name, local_dir_path, default_target_base_branch
    - Implement load() classmethod untuk load dari environment variables atau .env file
    - Implement validate() method untuk validasi format dan required fields
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [ ]* 2.2 Write property test untuk Configuration
    - **Property 1: Configuration Loading Completeness**
    - **Property 2: Configuration Default Values**
    - **Property 3: Configuration Validation Errors**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**

- [x] 3. Implement custom exception classes
  - Create exceptions.py dengan AgentError, ConfigurationError, GitHubAPIError, GeminiAPIError, JSONParseError, GitError, FileWriteError
  - _Requirements: 13.1, 13.4_

- [x] 4. Implement data models
  - Create models.py dengan dataclasses: Issue, PullRequest, ReviewComment, SolutionFile, Solution, ProcessingResult
  - Implement Solution.from_json() classmethod untuk parsing JSON response
  - Implement ProcessingResult methods: add_success(), add_failure()
  - _Requirements: 2.3, 8.3, 4.4, 10.4_

- [ ] 5. Implement Gemini Client
  - [x] 5.1 Create GeminiClient class dengan initialization
    - Implement __init__() dengan API key configuration
    - Configure Gemini model dengan temperature 0.2
    - Setup retry configuration (max 3 retries, exponential backoff)
    - _Requirements: 14.3_
  
  - [x] 5.2 Implement generate_solution() method
    - Construct system prompt untuk JSON-only output dengan schema specification
    - Send request ke Gemini API dengan prompt dan system instruction
    - Validate response adalah valid JSON
    - Parse response menjadi Solution object
    - _Requirements: 4.3, 4.4, 10.3, 10.4, 14.1, 14.2, 14.4_
  
  - [x] 5.3 Implement _extract_json_from_markdown() helper method
    - Extract JSON dari markdown code blocks (```json ... ```)
    - Handle cases dimana JSON wrapped dalam markdown
    - _Requirements: 14.5_
  
  - [x] 5.4 Implement retry logic untuk API failures
    - Retry up to 3 times pada invalid JSON response
    - Exponential backoff: 1s, 2s, 4s
    - Log semua API interactions
    - Raise GeminiAPIError setelah max retries
    - _Requirements: 4.5, 4.6, 10.5, 10.6_
  
  - [ ]* 5.5 Write property tests untuk Gemini Client
    - **Property 9: Gemini API JSON Response Format**
    - **Property 10: JSON Extraction from Markdown**
    - **Property 11: Retry on Invalid JSON**
    - **Property 25: Gemini System Prompt Configuration**
    - **Property 26: Gemini Temperature Configuration**
    - **Validates: Requirements 4.3, 4.4, 4.5, 10.3, 10.4, 10.5, 14.1, 14.2, 14.3, 14.4, 14.5**

- [ ] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement GitHub Client
  - [x] 7.1 Create GitHubClient class dengan initialization
    - Implement __init__() dengan token dan repo_name
    - Initialize PyGithub client
    - Setup retry configuration untuk transient errors
    - _Requirements: 1.2, 1.3_
  
  - [x] 7.2 Implement get_assigned_issues() method
    - Query GitHub API untuk open issues
    - Filter issues assigned to authenticated user
    - Return list of Issue objects dengan number, title, body
    - Handle empty issue list gracefully
    - _Requirements: 2.1, 2.2, 2.3, 2.4_
  
  - [x] 7.3 Implement get_prs_with_changes_requested() method
    - Query GitHub API untuk PRs created by authenticated user
    - Filter PRs dengan latest review state CHANGES_REQUESTED
    - Return list of PullRequest objects dengan number, branch, base_branch
    - Handle empty PR list gracefully
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  
  - [x] 7.4 Implement get_review_comments() method
    - Get review comments untuk specific PR
    - Return list of ReviewComment objects dengan body, file_path, line, reviewer
    - _Requirements: 8.3_
  
  - [x] 7.5 Implement create_pull_request() method
    - Create PR dengan title format 'Fix issue #N: [title]'
    - Set PR body dengan 'Closes #N'
    - Link PR to original issue
    - Return PullRequest object
    - Raise GitHubAPIError on failure
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_
  
  - [x] 7.6 Implement request_review() method
    - Re-request review dari specified reviewers
    - Handle reviewer identification
    - Raise GitHubAPIError on failure
    - _Requirements: 12.1, 12.2, 12.3_
  
  - [x] 7.7 Implement error handling dan logging
    - Wrap PyGithub exceptions dalam GitHubAPIError
    - Log API rate limit status
    - Retry on transient network errors
    - _Requirements: 13.1_
  
  - [ ]* 7.8 Write property tests untuk GitHub Client
    - **Property 4: Issue Filtering Correctness**
    - **Property 5: Issue Data Completeness**
    - **Property 18: PR Filtering by Review State**
    - **Property 19: PR Data Completeness**
    - **Property 20: Reviewer Identification**
    - **Validates: Requirements 2.2, 2.3, 8.2, 8.3, 12.1**

- [ ] 8. Implement Git Manager
  - [x] 8.1 Create GitManager class dengan initialization
    - Implement __init__() dengan repo_path
    - Validate repo_path is valid git repository
    - Initialize GitPython Repo object
    - Raise GitError jika invalid repository
    - _Requirements: 1.4_
  
  - [x] 8.2 Implement create_branch() method
    - Checkout to base_branch
    - Pull latest changes dari remote
    - Create new branch dengan format 'fix/issue-N'
    - Checkout to new branch
    - Raise GitError on failure
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_
  
  - [x] 8.3 Implement checkout_and_pull() method
    - Checkout to specified branch
    - Pull latest changes dari remote
    - Raise GitError on failure
    - _Requirements: 9.1, 9.2, 9.3_
  
  - [x] 8.4 Implement commit_and_push() method
    - Stage all modified files dengan git add
    - Create commit dengan specified message
    - Push to remote branch
    - Raise GitError on failure
    - _Requirements: 6.1, 6.3, 6.4, 11.3, 11.5, 11.6_
  
  - [x] 8.5 Implement get_current_branch() helper method
    - Return name of current branch
    - _Requirements: 3.4_
  
  - [x] 8.6 Implement error handling dan logging
    - Wrap GitPython exceptions dalam GitError
    - Validate repository state before operations
    - Log all git commands executed
    - _Requirements: 13.1_
  
  - [ ]* 8.7 Write property tests untuk Git Manager
    - **Property 6: Branch Naming Format**
    - **Property 7: Branch Creation State Transition**
    - **Property 14: Commit Message Format for Issues**
    - **Property 15: Commit Message Format for PR Fixes**
    - **Validates: Requirements 3.3, 3.1, 3.2, 3.4, 6.2, 11.4**

- [ ] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Implement Issue Handler
  - [x] 10.1 Create IssueHandler class dengan initialization
    - Implement __init__() dengan dependencies: github_client, gemini_client, git_manager, config
    - _Requirements: 2.1_
  
  - [x] 10.2 Implement _read_relevant_files() helper method
    - Read all Python files dari local repository
    - Return dict mapping file_path to content
    - Handle file read errors gracefully
    - _Requirements: 4.1_
  
  - [x] 10.3 Implement _construct_prompt() helper method
    - Construct prompt containing issue description
    - Include relevant file contents
    - Format prompt untuk optimal AI understanding
    - _Requirements: 4.2, 10.2_
  
  - [x] 10.4 Implement _apply_solution() helper method
    - Parse Solution JSON structure
    - Write each file dengan new content
    - Preserve file permissions dan encoding
    - Rollback changes on file write failure
    - Raise FileWriteError on failure
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [x] 10.5 Implement _process_single_issue() method
    - Create feature branch untuk issue
    - Read relevant files
    - Construct prompt dan call Gemini API
    - Apply solution to local files
    - Commit dengan message format 'Fix issue #N: [title]'
    - Push changes to remote
    - Create Pull Request
    - Return True if successful, False otherwise
    - Log errors dan continue on failure
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 6.1, 6.2, 6.3, 7.1, 7.2, 7.3_
  
  - [x] 10.6 Implement process_issues() main method
    - Get assigned issues dari GitHub
    - Process each issue dengan error isolation
    - Continue processing remaining issues after error
    - Return ProcessingResult dengan summary
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 13.2, 13.3_
  
  - [ ]* 10.7 Write property tests untuk Issue Handler
    - **Property 8: Prompt Construction Completeness**
    - **Property 12: Solution Application Completeness**
    - **Property 13: File Attribute Preservation**
    - **Property 16: Pull Request Title Format**
    - **Property 17: Pull Request Body Issue Reference**
    - **Property 21: Error Isolation in Batch Processing**
    - **Property 27: Git Operations Rollback on File Write Failure**
    - **Validates: Requirements 4.2, 5.1, 5.2, 5.3, 5.4, 7.2, 7.3, 13.2**
  
  - [ ]* 10.8 Write unit tests untuk Issue Handler
    - Test empty issue list handling
    - Test error recovery untuk single issue failure
    - Test file read errors
    - Test solution application errors
    - _Requirements: 2.4, 13.2_

- [ ] 11. Implement PR Handler
  - [x] 11.1 Create PRHandler class dengan initialization
    - Implement __init__() dengan dependencies: github_client, gemini_client, git_manager, config
    - _Requirements: 8.1_
  
  - [x] 11.2 Implement _get_reviewers_who_requested_changes() helper method
    - Extract reviewer usernames dari review comments
    - Return list of unique reviewer usernames
    - _Requirements: 12.1_
  
  - [x] 11.3 Implement _construct_fix_prompt() helper method
    - Construct prompt containing review comments
    - Include current file contents
    - Format prompt untuk optimal AI understanding
    - _Requirements: 10.2_
  
  - [x] 11.4 Implement _apply_fixes() helper method
    - Parse Solution JSON structure
    - Write each file dengan new content
    - Preserve file permissions dan encoding
    - Rollback changes on file write failure
    - Raise FileWriteError on failure
    - _Requirements: 11.1, 11.2_
  
  - [x] 11.5 Implement _process_single_pr() method
    - Checkout to PR branch dan pull latest
    - Read current file contents
    - Construct fix prompt dan call Gemini API
    - Apply fixes to local files
    - Commit dengan message 'Address review comments'
    - Push changes to remote
    - Re-request review dari reviewers
    - Return True if successful, False otherwise
    - Log errors dan continue on failure
    - _Requirements: 9.1, 9.2, 10.1, 10.2, 10.3, 10.4, 11.1, 11.2, 11.3, 11.4, 11.5, 12.1, 12.2_
  
  - [x] 11.6 Implement process_prs() main method
    - Get PRs with changes requested dari GitHub
    - Process each PR dengan error isolation
    - Continue processing remaining PRs after error
    - Return ProcessingResult dengan summary
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 13.2, 13.3_
  
  - [ ]* 11.7 Write property tests untuk PR Handler
    - **Property 8: Prompt Construction Completeness** (untuk PR fixes)
    - **Property 12: Solution Application Completeness** (untuk PR fixes)
    - **Property 21: Error Isolation in Batch Processing** (untuk PRs)
    - **Validates: Requirements 10.2, 11.1, 11.2, 13.2**
  
  - [ ]* 11.8 Write unit tests untuk PR Handler
    - Test empty PR list handling
    - Test error recovery untuk single PR failure
    - Test reviewer identification
    - Test fix application errors
    - _Requirements: 8.4, 13.2_

- [ ] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Implement Agent Main Loop
  - [x] 13.1 Create Agent class dengan initialization
    - Implement __init__() dengan config parameter
    - Initialize all components: Configuration, GeminiClient, GitHubClient, GitManager, IssueHandler, PRHandler
    - Setup logging configuration
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [x] 13.2 Implement _log_summary() helper method
    - Log summary of issue processing results
    - Log summary of PR processing results
    - Include total, successful, failed counts
    - Include error messages
    - _Requirements: 13.3_
  
  - [x] 13.3 Implement run() main method
    - Process assigned issues via IssueHandler
    - Process PRs with changes requested via PRHandler
    - Log summary of all operations
    - Return exit code 0 for success, 1 for critical error
    - _Requirements: 2.1, 8.1, 13.1, 13.2, 13.3, 13.4_
  
  - [x] 13.4 Implement error handling dan logging
    - Catch critical errors (ConfigurationError, repository not found)
    - Exit dengan non-zero code on critical error
    - Log all operations dengan timestamp dan context
    - Ensure cleanup on exit
    - _Requirements: 13.1, 13.4_
  
  - [ ]* 13.5 Write property tests untuk Agent
    - **Property 21: Error Isolation in Batch Processing**
    - **Property 22: Error Logging Completeness**
    - **Property 23: Processing Summary Completeness**
    - **Property 24: Critical Error Exit Code**
    - **Validates: Requirements 13.1, 13.2, 13.3, 13.4**
  
  - [ ]* 13.6 Write unit tests untuk Agent
    - Test configuration loading errors
    - Test critical error handling
    - Test summary logging
    - Test exit codes
    - _Requirements: 13.1, 13.4_

- [x] 14. Create main entry point script
  - Create main.py atau __main__.py
  - Parse command line arguments (optional: --config-file)
  - Load configuration
  - Initialize Agent
  - Run agent dan exit dengan appropriate code
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 13.4_

- [ ] 15. Integration testing dan end-to-end validation
  - [ ]* 15.1 Write integration test untuk issue handling workflow
    - Mock GitHub API dan Gemini API
    - Use temporary git repository
    - Test complete flow: detect issue → create branch → generate solution → apply changes → commit → push → create PR
    - _Requirements: 2.1, 2.2, 3.1, 3.2, 3.3, 4.1, 4.2, 4.3, 5.1, 5.2, 6.1, 6.2, 6.3, 7.1, 7.2, 7.3_
  
  - [ ]* 15.2 Write integration test untuk PR handling workflow
    - Mock GitHub API dan Gemini API
    - Use temporary git repository
    - Test complete flow: detect PR → checkout branch → generate fixes → apply fixes → commit → push → re-request review
    - _Requirements: 8.1, 8.2, 9.1, 9.2, 10.1, 10.2, 10.3, 11.1, 11.2, 11.3, 11.4, 11.5, 12.1, 12.2_
  
  - [ ]* 15.3 Write integration test untuk error recovery
    - Test error isolation across multiple issues
    - Test error isolation across multiple PRs
    - Test processing summary accuracy
    - _Requirements: 13.2, 13.3_

- [x] 16. Documentation dan README
  - Create README.md dengan setup instructions
  - Document environment variables dan configuration
  - Document usage examples
  - Document error handling behavior
  - Create .env.example file
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 17. Final checkpoint - Ensure all tests pass dan agent berjalan
  - Run all unit tests dan property tests
  - Run integration tests
  - Test agent dengan real GitHub repository (optional, manual testing)
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked dengan `*` adalah optional dan dapat di-skip untuk faster MVP
- Setiap task reference specific requirements untuk traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties dari design document
- Unit tests validate specific examples dan edge cases
- Agent menggunakan Python dengan libraries: google-generativeai, PyGithub, GitPython, python-dotenv, hypothesis
