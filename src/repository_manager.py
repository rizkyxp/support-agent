"""Repository manager for handling multiple repositories."""

import logging
from pathlib import Path
from typing import List

from git import Repo, GitCommandError

from src.config import Configuration
from src.utils.errors import GitError


logger = logging.getLogger(__name__)


class RepositoryManager:
    """Manager for handling multiple repositories in organization."""
    
    def __init__(self, config: Configuration, github_client: 'GitHubCLIClient'):
        """Initialize repository manager.
        
        Args:
            config: Agent configuration
            github_client: GitHub client (API or CLI)
        """
        self.config = config
        self.github_client = github_client
        self.repositories_dir = config.repositories_dir
        
        logger.info(f"Repository manager initialized with dir: {self.repositories_dir}")
    
    def get_organization_repositories(self) -> List[str]:
        """Get all repositories in the organization.
        
        Returns:
            List of repository names (without org prefix, e.g., 'repo-name')
        """
        try:
            logger.info(f"Fetching repositories for organization: {self.config.github_organization}")
            
            # Use GitHub client's method (works for both API and CLI)
            repo_names = self.github_client.get_organization_repositories()
            
            logger.info(f"Found {len(repo_names)} repositories in organization")
            return repo_names
            
        except Exception as e:
            logger.error(f"Failed to fetch organization repositories: {e}")
            return []
    
    def ensure_repository_cloned(self, repo_name: str, full_repo_name: str = None) -> Path:
        """Ensure repository is cloned locally.
        
        If repository doesn't exist locally, clone it.
        If it exists, return the path.
        
        Args:
            repo_name: Repository name (without org, e.g., 'repo-name')
            full_repo_name: Full repository name (org/repo-name). If None, uses config.github_organization
            
        Returns:
            Path to local repository
            
        Raises:
            GitError: If cloning fails
        """
        local_repo_path = self.repositories_dir / repo_name
        
        # Check if repository already exists
        if local_repo_path.exists() and (local_repo_path / '.git').exists():
            logger.info(f"Repository already exists: {local_repo_path}")
            
            # Pull latest changes
            try:
                logger.info(f"Pulling latest changes for {repo_name}")
                repo = Repo(local_repo_path)
                
                # Get current branch
                current_branch = repo.active_branch.name
                
                # Pull latest
                repo.git.pull('origin', current_branch)
                logger.info(f"Successfully pulled latest changes for {repo_name}")
            except Exception as e:
                logger.warning(f"Failed to pull latest changes for {repo_name}: {e}")
            
            return local_repo_path
        
        # Clone repository using GitHub CLI (supports SSH if configured)
        try:
            logger.info(f"Cloning repository: {repo_name} to {local_repo_path}")
            
            # Determine full repository name
            if full_repo_name:
                clone_target = full_repo_name
            elif self.config.github_organization:
                clone_target = f"{self.config.github_organization}/{repo_name}"
            else:
                raise GitError(f"Cannot clone {repo_name}: no organization specified and no full_repo_name provided")
            
            # Use gh repo clone which respects user's git protocol preference (SSH/HTTPS)
            import subprocess
            
            cmd = ["gh", "repo", "clone", clone_target, str(local_repo_path)]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                raise GitError(f"Failed to clone repository {repo_name}: {result.stderr}")
            
            logger.info(f"Successfully cloned repository: {repo_name}")
            return local_repo_path
            
        except subprocess.TimeoutExpired:
            raise GitError(f"Timeout while cloning repository {repo_name}")
        except Exception as e:
            logger.error(f"Failed to clone repository {repo_name}: {e}")
            raise GitError(f"Failed to clone repository {repo_name}: {e}")
    
    def get_repository_path(self, repo_name: str) -> Path:
        """Get path to local repository.
        
        Args:
            repo_name: Repository name in format 'org/repo-name'
            
        Returns:
            Path to local repository
        """
        repo_short_name = repo_name.split('/')[-1]
        return self.repositories_dir / repo_short_name
    
    def cleanup_old_branches(self, repo_path: Path) -> None:
        """Cleanup old feature branches in repository.
        
        Args:
            repo_path: Path to local repository
        """
        try:
            repo = Repo(repo_path)
            
            # Get all local branches
            branches = [b.name for b in repo.branches]
            
            # Find fix/* branches
            fix_branches = [b for b in branches if b.startswith('fix/')]
            
            if not fix_branches:
                return
            
            logger.info(f"Found {len(fix_branches)} fix branches in {repo_path.name}")
            
            # Checkout to default branch first
            try:
                repo.git.checkout(self.config.default_target_base_branch)
            except:
                pass
            
            # Delete fix branches
            for branch in fix_branches:
                try:
                    repo.git.branch('-D', branch)
                    logger.debug(f"Deleted branch: {branch}")
                except Exception as e:
                    logger.warning(f"Failed to delete branch {branch}: {e}")
            
            logger.info(f"Cleaned up {len(fix_branches)} old branches")
            
        except Exception as e:
            logger.warning(f"Failed to cleanup branches in {repo_path}: {e}")
