"""Multi-repository agent orchestrator."""

import logging
from pathlib import Path
from typing import Dict, List

from src.config import Configuration
from src.clients.gemini_client import GeminiClient
from src.clients.gemini_cli_client import GeminiCLIClient
from src.clients.github_client import GitHubClient
from src.clients.github_cli_client import GitHubCLIClient
from src.git.git_manager import GitManager
from src.handlers.issue_handler import IssueHandler
from src.handlers.pr_handler import PRHandler
from src.repository_manager import RepositoryManager
from src.models.data_models import ProcessingResult
from src.utils.errors import ConfigurationError


logger = logging.getLogger(__name__)


class MultiRepoAgent:
    """Multi-repository agent orchestrator for GitHub AI Agent."""
    
    def __init__(self, config: Configuration):
        """Initialize multi-repo agent with all components.
        
        Args:
            config: Agent configuration
        """
        self.config = config
        
        # Initialize shared clients
        logger.info("Initializing multi-repo agent components")
        
        # Initialize Gemini client (API or CLI based on config)
        if config.use_gemini_cli:
            logger.info("Using Gemini CLI for code generation (Pro account)")
            self.gemini_client = GeminiCLIClient(
                cli_path=config.gemini_cli_path,
                model=config.gemini_cli_model
            )
        else:
            logger.info("Using Gemini API for code generation")
            self.gemini_client = GeminiClient(api_key=config.gemini_api_key)
        
        # Initialize GitHub client (CLI or API based on config)
        if config.use_github_cli:
            logger.info("Using GitHub CLI for GitHub operations")
            self.github_client = GitHubCLIClient(
                cli_path=config.github_cli_path,
                organization=config.github_organization
            )
        else:
            logger.info("Using GitHub API for GitHub operations")
            self.github_client = GitHubClient(
                token=config.github_token,
                organization=config.github_organization
            )
        
        # Initialize repository manager
        self.repo_manager = RepositoryManager(
            config=config,
            github_client=self.github_client
        )
        
        logger.info("Multi-repo agent initialized successfully")
    
    def run(self) -> int:
        """Run agent workflows across all repositories.
        
        Steps:
        1. Search for assigned issues and PRs with changes requested across organization
        2. Only clone and process repositories that have work to do
        3. Log summary
        
        Returns:
            int: Exit code (0 for success, 1 for critical error)
        """
        try:
            logger.info("=" * 60)
            logger.info("GitHub AI Multi-Repo Agent starting")
            logger.info(f"Organization: {self.config.github_organization}")
            logger.info("=" * 60)
            
            # Step 1: Search for work across organization using gh search
            logger.info("\n--- Searching for Issues and PRs ---")
            
            issues_by_repo = {}
            prs_by_repo = {}
            repo_full_names = {}  # Map repo_name -> full_repo_name (org/repo)
            
            if self.config.process_issues:
                logger.info("Searching for assigned issues...")
                issues_by_repo = self.github_client.search_assigned_issues_in_org()
                # Extract full repository names from issues
                for repo_name, issues in issues_by_repo.items():
                    if issues and 'repository' in issues[0]:
                        repo_full_names[repo_name] = issues[0]['repository'].get('nameWithOwner', repo_name)
            
            if self.config.process_prs:
                logger.info("Searching for PRs with changes requested...")
                prs_by_repo = self.github_client.search_prs_with_changes_requested_in_org()
                # Extract full repository names from PRs
                for repo_name, prs in prs_by_repo.items():
                    if prs and 'repository' in prs[0]:
                        repo_full_names[repo_name] = prs[0]['repository'].get('nameWithOwner', repo_name)
            
            # Combine repos with work
            all_repos_with_work = set(issues_by_repo.keys()) | set(prs_by_repo.keys())
            
            if not all_repos_with_work:
                logger.info("\n✓ No issues or PRs to process")
                return 0
            
            logger.info(f"\n✓ Found work in {len(all_repos_with_work)} repositories")
            
            # Track overall results
            total_issue_result = ProcessingResult()
            total_pr_result = ProcessingResult()
            processed_repos = 0
            failed_repos = []
            
            # Step 2: Process repositories that have work
            for repo_name in sorted(all_repos_with_work):
                issues_count = len(issues_by_repo.get(repo_name, []))
                prs_count = len(prs_by_repo.get(repo_name, []))
                
                try:
                    logger.info("\n" + "=" * 60)
                    logger.info(f"Processing repository: {repo_name}")
                    logger.info(f"  Issues: {issues_count}, PRs: {prs_count}")
                    logger.info("=" * 60)
                    
                    # Ensure repository is cloned
                    logger.info(f"Ensuring repository is cloned: {repo_name}")
                    full_repo_name = repo_full_names.get(repo_name)
                    repo_path = self.repo_manager.ensure_repository_cloned(repo_name, full_repo_name)
                    
                    # Set current repository in GitHub client
                    self.github_client.set_repository(repo_name, full_repo_name)
                    
                    # Initialize Git manager for this repository
                    git_manager = GitManager(repo_path=repo_path)
                    
                    # Initialize handlers for this repository
                    issue_handler = IssueHandler(
                        github_client=self.github_client,
                        gemini_client=self.gemini_client,
                        git_manager=git_manager,
                        config=self.config,
                        repo_path=repo_path
                    )
                    pr_handler = PRHandler(
                        github_client=self.github_client,
                        gemini_client=self.gemini_client,
                        git_manager=git_manager,
                        config=self.config,
                        repo_path=repo_path
                    )
                    
                    # Process issues (if any)
                    if issues_count > 0:
                        logger.info(f"\n--- Processing Issues for {repo_name} ---")
                        issue_result = issue_handler.process_issues()
                        
                        # Aggregate results
                        total_issue_result.total += issue_result.total
                        total_issue_result.successful += issue_result.successful
                        total_issue_result.failed += issue_result.failed
                        total_issue_result.errors.extend([f"[{repo_name}] {e}" for e in issue_result.errors])
                    
                    # Process PRs (if any)
                    if prs_count > 0:
                        logger.info(f"\n--- Processing PRs for {repo_name} ---")
                        pr_data_for_repo = prs_by_repo.get(repo_name, [])
                        pr_result = pr_handler.process_prs(pr_data_for_repo)
                        
                        # Aggregate results
                        total_pr_result.total += pr_result.total
                        total_pr_result.successful += pr_result.successful
                        total_pr_result.failed += pr_result.failed
                        total_pr_result.errors.extend([f"[{repo_name}] {e}" for e in pr_result.errors])
                    
                    processed_repos += 1
                    logger.info(f"✓ Completed processing {repo_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to process repository {repo_name}: {e}", exc_info=True)
                    failed_repos.append(f"{repo_name}: {str(e)}")
            
            # Step 3: Log summary
            logger.info("\n" + "=" * 60)
            self._log_summary(
                total_issue_result, 
                total_pr_result, 
                processed_repos, 
                len(all_repos_with_work),
                failed_repos
            )
            logger.info("=" * 60)
            
            # Return success if no critical errors
            return 0
            
        except ConfigurationError as e:
            logger.critical(f"Configuration error: {e}")
            return 1
        except Exception as e:
            logger.critical(f"Critical error during agent execution: {e}", exc_info=True)
            return 1
    
    def _log_summary(
        self,
        issue_result: ProcessingResult,
        pr_result: ProcessingResult,
        processed_repos: int,
        total_repos: int,
        failed_repos: list
    ) -> None:
        """Log summary of all operations.
        
        Args:
            issue_result: Result from issue processing
            pr_result: Result from PR processing
            processed_repos: Number of successfully processed repositories
            total_repos: Total number of repositories
            failed_repos: List of failed repository names with errors
        """
        logger.info("EXECUTION SUMMARY")
        logger.info("-" * 60)
        
        # Repository summary
        logger.info(f"Repositories: {processed_repos}/{total_repos} processed successfully")
        if failed_repos:
            logger.info("  Failed repositories:")
            for repo_error in failed_repos:
                logger.info(f"    * {repo_error}")
        
        logger.info("")
        
        # Issue summary
        logger.info(f"Issues Processed: {issue_result.total}")
        logger.info(f"  - Successful: {issue_result.successful}")
        logger.info(f"  - Failed: {issue_result.failed}")
        if issue_result.errors:
            logger.info("  - Errors:")
            for error in issue_result.errors[:10]:  # Show first 10 errors
                logger.info(f"    * {error}")
            if len(issue_result.errors) > 10:
                logger.info(f"    ... and {len(issue_result.errors) - 10} more errors")
        
        logger.info("")
        
        # PR summary
        logger.info(f"PRs Processed: {pr_result.total}")
        logger.info(f"  - Successful: {pr_result.successful}")
        logger.info(f"  - Failed: {pr_result.failed}")
        if pr_result.errors:
            logger.info("  - Errors:")
            for error in pr_result.errors[:10]:  # Show first 10 errors
                logger.info(f"    * {error}")
            if len(pr_result.errors) > 10:
                logger.info(f"    ... and {len(pr_result.errors) - 10} more errors")
        
        logger.info("")
        
        # Overall summary
        total_items = issue_result.total + pr_result.total
        total_successful = issue_result.successful + pr_result.successful
        total_failed = issue_result.failed + pr_result.failed
        
        logger.info(f"TOTAL: {total_items} items processed across {processed_repos} repositories")
        logger.info(f"  - {total_successful} successful")
        logger.info(f"  - {total_failed} failed")
        
        if total_items == 0:
            logger.info("\nNo issues or PRs to process.")
        elif total_failed == 0 and not failed_repos:
            logger.info("\n✓ All items processed successfully!")
        else:
            logger.warning(f"\n⚠ {total_failed} items failed. Check logs for details.")
