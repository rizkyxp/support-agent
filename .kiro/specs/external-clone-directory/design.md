# External Clone Directory Bugfix Design

## Overview

The current implementation clones repositories inside the project directory using `Path.cwd() / repositories_dir_str`, which pollutes the project workspace with repository clones. This fix will move all repository cloning operations to OS-specific external locations: user's home directory on macOS/Linux, and C:\ drive on Windows. The fix will detect the operating system, determine the appropriate default path, and resolve the `REPOSITORIES_DIR` environment variable as an absolute path. All existing functionality (pull, cleanup, detection, path retrieval) will be preserved.

## Glossary

- **Bug_Condition (C)**: The condition where repository cloning occurs inside the project directory (using `Path.cwd()`)
- **Property (P)**: The desired behavior where repositories are cloned to OS-specific external locations
- **Preservation**: Existing repository operations (pull, cleanup, detection, path retrieval) that must continue working unchanged
- **repositories_dir**: The Path object in `Configuration` class that determines where repositories are cloned
- **Path.cwd()**: Python's current working directory, which points to the project root
- **REPOSITORIES_DIR**: Environment variable that specifies the repositories directory name or path

## Bug Details

### Bug Condition

The bug manifests when the agent clones any repository. The `Configuration.load()` method in `src/config.py` constructs the repositories directory path using `Path.cwd() / repositories_dir_str`, which creates the directory inside the current project. This causes repository files to be mixed with project files, violating separation of concerns.

**Formal Specification:**
```
FUNCTION isBugCondition(operation)
  INPUT: operation of type RepositoryOperation
  OUTPUT: boolean
  
  RETURN operation.type IN ['clone', 'pull', 'branch_create', 'cleanup']
         AND repositories_dir.is_relative_to(Path.cwd())
         AND repositories_dir.parent == Path.cwd()
END FUNCTION
```

### Examples

- **Example 1**: User runs agent from `/Users/rizky/github-ai-agent/`, system clones to `/Users/rizky/github-ai-agent/repositories/repo-name` (WRONG - inside project)
- **Example 2**: User sets `REPOSITORIES_DIR=my-repos`, system creates `/Users/rizky/github-ai-agent/my-repos/` (WRONG - still inside project)
- **Example 3**: On Windows, user runs from `C:\Projects\github-ai-agent\`, system clones to `C:\Projects\github-ai-agent\repositories\` (WRONG - inside project)
- **Edge Case**: User sets `REPOSITORIES_DIR=/tmp/repos` (absolute path), system should use `/tmp/repos/` directly (CORRECT - outside project)

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Repository detection must continue to work (checking if `.git` exists)
- Pulling latest changes must continue to work for existing repositories
- Branch cleanup operations must continue to delete old `fix/*` branches correctly
- `get_repository_path()` must continue to return correct paths
- GitHub CLI integration must continue to respect user's git protocol preference (SSH/HTTPS)
- Automatic directory creation with proper error handling must continue to work

**Scope:**
All repository operations that do NOT involve determining the base repositories directory location should be completely unaffected by this fix. This includes:
- Git operations (clone, pull, checkout, branch deletion)
- Repository path resolution logic
- GitHub CLI command execution
- Error handling and logging

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is:

1. **Hardcoded Path.cwd() Usage**: In `src/config.py` line 95, the code uses `repositories_dir = Path.cwd() / repositories_dir_str`, which always creates the directory relative to the current working directory (the project root).

2. **No OS Detection**: The code does not detect the operating system to determine appropriate default locations for external storage.

3. **Relative Path Assumption**: The code treats `REPOSITORIES_DIR` as always relative to `Path.cwd()`, with no logic to handle absolute paths or external base directories.

4. **No Home Directory Resolution**: The code does not use `Path.home()` or similar mechanisms to place repositories in user-specific locations outside the project.

## Correctness Properties

Property 1: Bug Condition - External Repository Location

_For any_ repository operation (clone, pull, branch creation, cleanup) performed by the agent, the fixed configuration SHALL determine a repositories directory that is located outside the current project directory, using OS-specific defaults: user's home directory on macOS/Linux (e.g., `/Users/rizky/repositories/`), or C:\ drive on Windows (e.g., `C:\repositories\`), and SHALL support absolute paths via the `REPOSITORIES_DIR` environment variable.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

Property 2: Preservation - Repository Operations Behavior

_For any_ repository operation that does NOT involve determining the base repositories directory location (such as git clone execution, pull operations, branch cleanup, path resolution, GitHub CLI usage), the fixed code SHALL produce exactly the same behavior as the original code, preserving all existing functionality for repository management operations.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `src/config.py`

**Function**: `Configuration.load()`

**Specific Changes**:
1. **Add OS Detection**: Import `platform` module and detect the operating system using `platform.system()`
   - Returns "Darwin" for macOS, "Windows" for Windows, "Linux" for Linux

2. **Determine Default Base Directory**: Create a helper function or inline logic to determine the default base directory:
   - macOS/Linux: Use `Path.home()` to get user's home directory
   - Windows: Use `Path("C:\\")`

3. **Resolve REPOSITORIES_DIR**: Update the logic to handle both relative and absolute paths:
   - If `REPOSITORIES_DIR` is an absolute path (starts with `/` or drive letter), use it directly
   - If `REPOSITORIES_DIR` is relative, append it to the OS-specific default base directory
   - Default value remains "repositories" if not specified

4. **Update Path Construction**: Replace `Path.cwd() / repositories_dir_str` with the new logic:
   ```python
   # Determine base directory based on OS
   base_dir = get_default_base_directory()
   
   # Resolve repositories directory
   if Path(repositories_dir_str).is_absolute():
       repositories_dir = Path(repositories_dir_str)
   else:
       repositories_dir = base_dir / repositories_dir_str
   ```

5. **Maintain Directory Creation**: Keep the existing `validate()` method logic that creates the directory if it doesn't exist

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code (repositories created inside project), then verify the fix works correctly (repositories created externally) and preserves existing behavior (all repository operations continue working).

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that repositories are currently being created inside the project directory.

**Test Plan**: Write tests that load configuration and check where `repositories_dir` points. Run these tests on the UNFIXED code to observe that paths are inside `Path.cwd()`.

**Test Cases**:
1. **Default Configuration Test**: Load config with default `REPOSITORIES_DIR`, assert that `repositories_dir` is inside `Path.cwd()` (will fail on unfixed code - confirms bug)
2. **Custom Relative Path Test**: Set `REPOSITORIES_DIR=my-repos`, assert that path is inside `Path.cwd()` (will fail on unfixed code - confirms bug)
3. **macOS Path Test**: On macOS, verify that default path is NOT in user's home directory (will fail on unfixed code - confirms bug)
4. **Windows Path Test**: On Windows, verify that default path is NOT on C:\ drive (will fail on unfixed code - confirms bug)

**Expected Counterexamples**:
- `repositories_dir` will be a subdirectory of `Path.cwd()`
- Cloning operations will create directories inside the project
- Possible root cause confirmed: `Path.cwd() / repositories_dir_str` is the culprit

### Fix Checking

**Goal**: Verify that for all repository operations, the fixed configuration produces external directory paths based on OS-specific defaults.

**Pseudocode:**
```
FOR ALL os IN ['Darwin', 'Windows', 'Linux'] DO
  config := Configuration.load_with_mocked_os(os)
  ASSERT NOT config.repositories_dir.is_relative_to(Path.cwd())
  ASSERT config.repositories_dir.parent IN [Path.home(), Path("C:\\")]
END FOR
```

### Preservation Checking

**Goal**: Verify that for all repository operations that do NOT involve path determination, the fixed code produces the same result as the original code.

**Pseudocode:**
```
FOR ALL operation IN ['detect_existing', 'pull_changes', 'cleanup_branches', 'get_path'] DO
  ASSERT repository_manager_original.operation() = repository_manager_fixed.operation()
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across different repository states
- It catches edge cases that manual unit tests might miss (empty repos, multiple branches, etc.)
- It provides strong guarantees that behavior is unchanged for all repository operations

**Test Plan**: Observe behavior on UNFIXED code first for repository operations, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Repository Detection Preservation**: Observe that existing repository detection works on unfixed code, then verify it continues after fix
2. **Pull Operations Preservation**: Observe that pulling latest changes works on unfixed code, then verify it continues after fix
3. **Branch Cleanup Preservation**: Observe that cleanup deletes `fix/*` branches on unfixed code, then verify it continues after fix
4. **Path Resolution Preservation**: Observe that `get_repository_path()` returns correct paths on unfixed code, then verify it continues after fix

### Unit Tests

- Test OS detection logic for macOS, Windows, and Linux
- Test default base directory determination for each OS
- Test absolute path handling (should use path directly)
- Test relative path handling (should append to base directory)
- Test that `REPOSITORIES_DIR` environment variable is respected
- Test directory creation with proper error handling

### Property-Based Tests

- Generate random OS types and verify external paths are always produced
- Generate random `REPOSITORIES_DIR` values (absolute and relative) and verify correct resolution
- Generate random repository names and verify path resolution works correctly
- Test that all repository operations work across many different external directory configurations

### Integration Tests

- Test full clone operation with external directory on each OS
- Test that cloned repositories can be detected and pulled
- Test that branch cleanup works in external directories
- Test that switching between different `REPOSITORIES_DIR` values works correctly
- Test backward compatibility: if user has existing repos in project directory, they should still be accessible (optional enhancement)
