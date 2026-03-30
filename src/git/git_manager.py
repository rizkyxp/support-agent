"""Git operations manager for local repository."""

import logging
from pathlib import Path

from git import Repo, GitCommandError
from git.exc import InvalidGitRepositoryError

from src.utils.errors import GitError


logger = logging.getLogger(__name__)


class GitManager:
    """Manager for local git operations."""
    
    def __init__(self, repo_path: Path):
        """Initialize Git manager with local repository path.
        
        Args:
            repo_path: Path to local git repository
            
        Raises:
            GitError: If repo_path is not a valid git repository
        """
        self.repo_path = repo_path
        
        try:
            self.repo = Repo(repo_path)
            logger.info(f"Git manager initialized for repository: {repo_path}")
        except InvalidGitRepositoryError:
            raise GitError(f"Not a valid git repository: {repo_path}")
    
    def create_branch(self, branch_name: str, base_branch: str) -> None:
        """Create new branch from base_branch and checkout to it.
        
        Steps:
        1. Checkout to base_branch
        2. Pull latest changes
        3. Create new branch
        4. Checkout to new branch
        
        Args:
            branch_name: Name of new branch to create
            base_branch: Base branch to create from
            
        Raises:
            GitError: If any step fails
        """
        try:
            logger.info(f"Creating branch {branch_name} from {base_branch}")
            
            # Step 1: Checkout to base branch
            logger.debug(f"Checking out to {base_branch}")
            self.repo.git.checkout(base_branch)
            
            # Step 2: Pull latest changes
            logger.debug(f"Pulling latest changes from {base_branch}")
            self.repo.git.pull('origin', base_branch)
            
            # Step 3 & 4: Create and checkout to new branch
            logger.debug(f"Creating and checking out to {branch_name}")
            self.repo.git.checkout('-b', branch_name)
            
            logger.info(f"Successfully created and checked out to branch: {branch_name}")
            
        except GitCommandError as e:
            raise GitError(f"Failed to create branch {branch_name}: {e}")
    
    def checkout_and_pull(self, branch_name: str) -> None:
        """Checkout to branch and pull latest changes.
        
        Args:
            branch_name: Branch name to checkout
            
        Raises:
            GitError: If checkout or pull fails
        """
        try:
            logger.info(f"Checking out to {branch_name} and pulling latest")
            
            # Fetch remote branch first to ensure it exists locally
            logger.debug(f"Fetching {branch_name} from origin")
            try:
                self.repo.git.fetch('origin', branch_name)
            except GitCommandError as e:
                logger.warning(f"Fetch failed for {branch_name}, continuing anyway: {e}")
            
            # Checkout to branch
            logger.debug(f"Checking out to {branch_name}")
            self.repo.git.checkout(branch_name)
            
            # Pull latest changes
            logger.debug(f"Pulling latest changes from {branch_name}")
            self.repo.git.pull('origin', branch_name)
            
            logger.info(f"Successfully checked out and pulled: {branch_name}")
            
        except GitCommandError as e:
            raise GitError(f"Failed to checkout and pull {branch_name}: {e}")
    
    def commit_and_push(self, commit_message: str, branch_name: str, files_to_commit: list = None) -> bool:
        """Stage changes, commit, and push to remote.
        
        Args:
            commit_message: Commit message
            branch_name: Branch name to push
            files_to_commit: Optional list of specific files to commit. If None, commits all changes.
            
        Returns:
            bool: True if changes were committed and pushed, False if no changes
            
        Raises:
            GitError: If commit or push fails
        """
        try:
            logger.info(f"Committing and pushing to {branch_name}")
            
            # Stage changes
            if files_to_commit:
                # Stage only specific files
                logger.debug(f"Staging {len(files_to_commit)} specific files")
                for file_path in files_to_commit:
                    try:
                        self.repo.git.add(file_path)
                    except GitCommandError as e:
                        logger.warning(f"Failed to stage {file_path}: {e}")
            else:
                # Stage all changes (but exclude .repositories if it exists)
                logger.debug("Staging all changes")
                self.repo.git.add(A=True)
            
            # Check if there are changes to commit
            if not self.repo.is_dirty() and not self.repo.untracked_files:
                logger.info("No changes to commit, skipping commit and push")
                return False
            
            # Create commit
            logger.debug(f"Creating commit: {commit_message}")
            self.repo.git.commit('-m', commit_message)
            
            # Push to remote
            logger.debug(f"Pushing to origin/{branch_name}")
            self.repo.git.push('origin', branch_name)
            
            logger.info(f"Successfully committed and pushed to: {branch_name}")
            return True
            
        except GitCommandError as e:
            raise GitError(f"Failed to commit and push: {e}")
    
    def get_current_branch(self) -> str:
        """Get name of current branch.
        
        Returns:
            str: Current branch name
        """
        return self.repo.active_branch.name

    def get_current_commit_hash(self) -> str:
        """Get current HEAD commit hash for rollback.
        
        Returns:
            str: Full commit hash
        """
        return self.repo.head.commit.hexsha

    def get_diff_against_base(self, base_branch: str) -> str:
        """Get diff between current branch and base branch.
        
        Args:
            base_branch: Name of the base branch to compare against.
            
        Returns:
            str: The diff output
        """
        try:
            # Ensure base branch is available locally
            self.repo.git.fetch('origin', base_branch)
            return self.repo.git.diff(f"origin/{base_branch}...HEAD")
        except GitCommandError as e:
            logger.warning(f"Failed to get diff against {base_branch}: {e}")
            return ""

    def get_changed_files_against_base(self, base_branch: str) -> list[str]:
        """Get list of files changed compared to base branch.
        
        Args:
            base_branch: Name of the base branch to compare against.
            
        Returns:
            list[str]: List of file paths
        """
        try:
            self.repo.git.fetch('origin', base_branch)
            diff_output = self.repo.git.diff(f"origin/{base_branch}...HEAD", name_only=True)
            return [f for f in diff_output.strip().split('\n') if f]
        except GitCommandError as e:
            logger.warning(f"Failed to get changed files against {base_branch}: {e}")
            return []

    def rollback_to_commit(self, commit_hash: str) -> None:
        """Rollback to a specific commit (hard reset).
        
        Args:
            commit_hash: The commit hash to reset to.
            
        Raises:
            GitError: If reset fails
        """
        try:
            logger.info(f"Rolling back to commit: {commit_hash}")
            self.repo.git.reset('--hard', commit_hash)
            logger.info(f"Successfully rolled back to {commit_hash}")
        except GitCommandError as e:
            raise GitError(f"Failed to rollback to {commit_hash}: {e}")

    def force_push(self, branch_name: str) -> None:
        """Force push to remote.
        
        Args:
            branch_name: Branch name to force push.
            
        Raises:
            GitError: If force push fails
        """
        try:
            logger.info(f"Performing force push to {branch_name}")
            self.repo.git.push('origin', branch_name, '--force')
            logger.info(f"Successfully force pushed to {branch_name}")
        except GitCommandError as e:
            raise GitError(f"Failed to force push to {branch_name}: {e}")
