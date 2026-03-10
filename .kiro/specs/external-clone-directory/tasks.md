# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - External Repository Location
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate repositories are created inside project directory
  - **Scoped PBT Approach**: Scope the property to concrete failing cases - default config and custom relative paths
  - Test that `isBugCondition(operation)` returns true: repositories_dir is inside Path.cwd()
  - Test cases: default REPOSITORIES_DIR, custom relative path (e.g., "my-repos"), verify paths are subdirectories of Path.cwd()
  - The test assertions should match Property 1 from design: repositories SHALL be located outside project directory
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found (e.g., "repositories_dir = /path/to/project/repositories instead of /Users/user/repositories")
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Repository Operations Behavior
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for repository operations that don't involve path determination
  - Test repository detection (checking if .git exists)
  - Test that get_repository_path() returns correct paths
  - Test that directory creation logic works
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 3. Fix for external clone directory

  - [x] 3.1 Add OS detection and default base directory logic
    - Import platform module at top of src/config.py
    - Create helper function to determine default base directory based on OS
    - macOS/Linux: Use Path.home() for user's home directory
    - Windows: Use Path("C:\\")
    - _Bug_Condition: isBugCondition(operation) where repositories_dir.is_relative_to(Path.cwd())_
    - _Expected_Behavior: repositories_dir is outside Path.cwd(), using OS-specific defaults_
    - _Preservation: Repository detection, path resolution, and directory creation continue working_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.2 Update Configuration.load() to resolve REPOSITORIES_DIR
    - Replace Path.cwd() / repositories_dir_str logic (around line 95)
    - Check if REPOSITORIES_DIR is absolute path (use Path.is_absolute())
    - If absolute: use it directly
    - If relative: append to OS-specific default base directory
    - Maintain default value of "repositories" if not specified
    - _Bug_Condition: isBugCondition(operation) where repositories_dir.parent == Path.cwd()_
    - _Expected_Behavior: repositories_dir resolves to external location or absolute path_
    - _Preservation: All existing repository operations continue working unchanged_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.3 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - External Repository Location
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms repositories are now created outside project directory
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [x] 3.4 Verify preservation tests still pass
    - **Property 2: Preservation** - Repository Operations Behavior
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm all repository operations still work after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
