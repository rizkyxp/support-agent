"""Post-fix change validation engine for GitHub AI Agent."""

import logging
from typing import List, Dict, Set
from src.git.git_manager import GitManager
from src.models.data_models import ValidationResult

logger = logging.getLogger(__name__)

class ChangeValidator:
    """Validator to ensure AI changes don't revert manual developer work."""
    
    def __init__(self, git_manager: GitManager):
        """Initialize validator with a git manager.
        
        Args:
            git_manager: Initialized GitManager for the repository
        """
        self.git_manager = git_manager
        
    def validate_changes(
        self,
        base_branch: str,
        protected_files: List[str],
        pre_fix_commit: str
    ) -> ValidationResult:
        """
        Validate that AI changes follow the protection rules.
        
        Args:
            base_branch: The base branch of the PR (usually main)
            protected_files: Files that were part of the PR but NOT mentioned in reviews
            pre_fix_commit: The commit hash before the AI started its work
            
        Returns:
            ValidationResult: Detailed findings of the validation
        """
        violations = []
        deleted_files = []
        details_parts = []
        
        logger.info(f"Validating changes against snapshot {pre_fix_commit[:8]}")
        
        # 1. Check Protected Files: They should NOT be modified from the pre-fix state
        for file_path in protected_files:
            try:
                # Get diff between pre-fix commit and current HEAD for this specific file
                diff = self.git_manager.repo.git.diff(pre_fix_commit, 'HEAD', '--', file_path)
                if diff.strip():
                    logger.warning(f"Violation: Protected file '{file_path}' was modified by AI.")
                    violations.append(file_path)
                    details_parts.append(f"File '{file_path}' is protected (not in review) but was modified.")
            except Exception as e:
                logger.error(f"Error validating protected file {file_path}: {e}")
        
        # 2. Check for File Deletions: Ensure no file that existed before was deleted
        pre_fix_files = self._get_files_at_commit(pre_fix_commit)
        current_files = self._get_files_at_commit('HEAD')
        
        for file_path in pre_fix_files:
            if file_path not in current_files:
                logger.warning(f"Violation: File '{file_path}' was deleted by AI.")
                deleted_files.append(file_path)
                details_parts.append(f"File '{file_path}' was deleted.")
        
        # 3. Summary
        is_valid = len(violations) == 0 and len(deleted_files) == 0
        details = "\n".join(details_parts) if details_parts else "No violations detected."
        
        return ValidationResult(
            is_valid=is_valid,
            violations=violations,
            deleted_files=deleted_files,
            details=details
        )
        
    def _get_files_at_commit(self, commit: str) -> Set[str]:
        """Get the list of all files in the repo at a specific commit."""
        try:
            output = self.git_manager.repo.git.ls_tree('-r', '--name-only', commit)
            return set(output.strip().split('\n'))
        except Exception as e:
            logger.error(f"Error listing files at commit {commit}: {e}")
            return set()
