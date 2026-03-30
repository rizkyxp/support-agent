"""Issue handling workflow."""

import logging
from pathlib import Path

from src.clients.gemini_cli_client import GeminiCLIClient
from src.clients.github_cli_client import GitHubCLIClient
from src.git.git_manager import GitManager
from src.config import Configuration
from src.models.data_models import Issue, ProcessingResult


logger = logging.getLogger(__name__)


class IssueHandler:
    """Handler for issue-to-PR workflow.
    
    Workflow:
    1. Create new branch from base branch
    2. Delegate code fixing to Gemini CLI (reads files, fixes, commits, pushes)
    3. Create Pull Request to base branch
    """
    
    def __init__(
        self,
        github_client: GitHubCLIClient,
        gemini_client: GeminiCLIClient,
        git_manager: GitManager,
        config: Configuration,
        repo_path: Path = None
    ):
        """Initialize issue handler with dependencies.
        
        Args:
            github_client: GitHub API client
            gemini_client: Gemini API client (or CLI client)
            git_manager: Git operations manager
            config: Agent configuration
            repo_path: Path to repository (if None, uses config.repositories_dir)
        """
        self.github_client = github_client
        self.gemini_client = gemini_client
        self.git_manager = git_manager
        self.config = config
        self.repo_path = repo_path or config.repositories_dir
        
        logger.info("Issue handler initialized")
    
    def _record_run_history(self, target_type: str, target_id: str, status: str, details: str = "") -> None:
        """Record the run outcome to the dashboard SQLite database."""
        try:
            import sqlite3
            from pathlib import Path
            db_path = Path.cwd() / ".agent_data" / "dashboard.sqlite"
            if db_path.exists():
                repo_name = self.repo_path.name if self.repo_path else "unknown"
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO run_history (target_repo, target_type, target_id, status, details) VALUES (?, ?, ?, ?, ?)",
                    (repo_name, target_type, str(target_id), status, details[:200])
                )
                conn.commit()
                conn.close()
        except Exception as e:
            logger.debug(f"Failed to record run history: {e}")

    def process_issues(self) -> ProcessingResult:
        """Process all assigned issues.
        
        For each issue:
        1. Create feature branch
        2. Delegate to Gemini CLI to fix, commit, and push
        3. Create Pull Request
        
        Returns:
            ProcessingResult: Summary of successful and failed operations
        """
        logger.info("Starting issue processing")
        
        # Get assigned issues
        try:
            issues = self.github_client.get_assigned_issues()
        except Exception as e:
            logger.error(f"Failed to fetch assigned issues: {e}")
            result = ProcessingResult(total=0, successful=0, failed=0)
            result.add_failure(f"Failed to fetch issues: {e}")
            return result
        
        if not issues:
            logger.info("No assigned issues found")
            return ProcessingResult(total=0, successful=0, failed=0)
        
        # Process each issue
        result = ProcessingResult(total=len(issues))
        for issue in issues:
            try:
                logger.info(f"Processing issue #{issue.number}: {issue.title}")
                success = self._process_single_issue(issue)
                if success:
                    result.add_success()
                    self._record_run_history("ISSUE", issue.number, "SUCCESS", "Resolved and created PR")
                else:
                    result.add_failure(f"Issue #{issue.number} processing returned False")
                    self._record_run_history("ISSUE", issue.number, "FAILED", "Processing returned False")
            except Exception as e:
                logger.error(f"Error processing issue #{issue.number}: {e}", exc_info=True)
                result.add_failure(f"Issue #{issue.number}: {str(e)}")
                self._record_run_history("ISSUE", issue.number, "FAILED", str(e))
        
        logger.info(f"Issue processing complete: {result.successful}/{result.total} successful")
        return result
    
    def _process_single_issue(self, issue: Issue) -> bool:
        """Process a single issue using Gemini CLI.
        
        Workflow:
        1. Create feature branch from base branch
        2. Delegate to Gemini CLI to read code, fix, commit, and push
        3. Create Pull Request to base branch
        
        Args:
            issue: Issue to process
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Step 1: Create feature branch
            branch_name = f"fix/issue-{issue.number}"
            logger.info(f"Creating branch: {branch_name}")
            self.git_manager.create_branch(
                branch_name=branch_name,
                base_branch=self.config.default_target_base_branch
            )
            
            # Step 2: Delegate to Gemini CLI to fix, commit, and push
            logger.info("Delegating to Gemini CLI to solve issue, commit, and push")
            result = self.gemini_client.solve_issue_and_push(
                repo_path=self.repo_path,
                branch_name=branch_name,
                issue_number=issue.number,
                issue_title=issue.title,
                issue_body=issue.body
            )
            
            if not result['success']:
                logger.error(f"Gemini CLI failed: {result['message']}")
                return False
            
            logger.info("Gemini CLI successfully solved issue and pushed changes")
            
            # Step 3: Create Pull Request
            pr_title = f"Fix issue #{issue.number}: {issue.title}"
            pr_body = f"Closes #{issue.number}\n\n{issue.body}"
            logger.info(f"Creating Pull Request: {pr_title}")
            pr = self.github_client.create_pull_request(
                title=pr_title,
                body=pr_body,
                head_branch=branch_name,
                base_branch=self.config.default_target_base_branch
            )
            
            logger.info(f"Successfully processed issue #{issue.number}, created PR: {pr.get('url', pr)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process issue #{issue.number}: {e}", exc_info=True)
            return False
