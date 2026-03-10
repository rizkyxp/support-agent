# Bugfix Requirements Document

## Introduction

The current implementation clones repositories inside the project directory (using `Path.cwd() / repositories_dir_str`), which causes the project itself to be modified by repository operations. This bug affects the cleanliness and isolation of the main project. The fix will move all repository cloning operations to a separate directory outside the current project using OS-specific default paths (user's home directory on macOS/Linux, C:\ drive on Windows), ensuring the project remains untouched by any repository changes and the agent works consistently across different operating systems.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the agent clones a repository THEN the system creates the clone inside the current project directory (e.g., `project_root/repositories/`)

1.2 WHEN repository operations (clone, fixes, branch creation) are performed THEN the system modifies files within the current project directory structure

1.3 WHEN the repositories directory is configured via `REPOSITORIES_DIR` environment variable THEN the system interprets it as a relative path from the current working directory (`Path.cwd()`)

### Expected Behavior (Correct)

2.1 WHEN the agent clones a repository THEN the system SHALL create the clone in a separate directory outside the current project using OS-specific default paths

2.2 WHEN running on macOS THEN the system SHALL use the user's home directory as the default clone location (e.g., `/Users/rizky/`)

2.3 WHEN running on Windows THEN the system SHALL use the C:\ drive as the default clone location (e.g., `C:\`)

2.4 WHEN running on Linux THEN the system SHALL use the user's home directory as the default clone location (e.g., `/home/rizky/`)

2.5 WHEN repository operations (clone, fixes, branch creation) are performed THEN the system SHALL perform all operations in the external directory without touching the current project

2.6 WHEN the repositories directory is configured via `REPOSITORIES_DIR` environment variable THEN the system SHALL resolve it as an absolute path or relative to a parent directory outside the project

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a repository is already cloned in the external directory THEN the system SHALL CONTINUE TO detect it and pull latest changes

3.2 WHEN repository cleanup operations are performed THEN the system SHALL CONTINUE TO delete old branches correctly

3.3 WHEN the GitHub CLI is used for cloning THEN the system SHALL CONTINUE TO respect the user's git protocol preference (SSH/HTTPS)

3.4 WHEN repository paths are retrieved via `get_repository_path()` THEN the system SHALL CONTINUE TO return the correct path to the repository

3.5 WHEN the repositories directory does not exist THEN the system SHALL CONTINUE TO create it automatically with proper error handling
