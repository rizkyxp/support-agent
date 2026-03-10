"""Main agent orchestrator."""

import logging

from src.config import Configuration
from src.clients.gemini_client import GeminiClient
from src.clients.github_client import GitHubClient
from src.git.git_manager import GitManager
from src.handlers.issue_handler import IssueHandler
from src.handlers.pr_handler import PRHandler
from src.models.data_models import ProcessingResult
from src.utils.errors import ConfigurationError


logger = logging.getLogger(__name__)


class Agent:
    """Main agent orchestrator for GitHub AI Agent."""
    
    def __init__(self, config: Configuration):
        """Initialize agent with all components.
        
        Args:
            config: Agent configuration
        """
        self.config = config
        
        # Initialize clients
        logger.info("Initializing agent components")
        self.gemini_client = GeminiClient(api_key=config.gemini_api_key)
        self.github_client = GitHubClient(
            token=config.github_token,
            repo_name=config.repo_name
        )
        self.git_manager = GitManager(repo_path=config.local_dir_path)
        
        # Initialize handlers
        self.issue_handler = IssueHandler(
            github_client=self.github_client,
            gemini_client=self.gemini_client,
            git_manager=self.git_manager,
            config=config
        )
        self.pr_handler = PRHandler(
            github_client=self.github_client,
            gemini_client=self.gemini_client,
            git_manager=self.git_manager,
            config=config
        )
        
        logger.info("Agent initialized successfully")
    
    def run(self) -> int:
        """Run agent workflows.
        
        Steps:
        1. Process assigned issues
        2. Process PRs with changes requested
        3. Log summary
        
        Returns:
            int: Exit code (0 for success, 1 for critical error)
        """
        try:
            logger.info("=" * 60)
            logger.info("GitHub AI Agent starting")
            logger.info("=" * 60)
            
            # Step 1: Process assigned issues
            logger.info("\n--- Processing Assigned Issues ---")
            issue_result = self.issue_handler.process_issues()
            
            # Step 2: Process PRs with changes requested
            logger.info("\n--- Processing PRs with Changes Requested ---")
            pr_result = self.pr_handler.process_prs()
            
            # Step 3: Log summary
            logger.info("\n" + "=" * 60)
            self._log_summary(issue_result, pr_result)
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
        pr_result: ProcessingResult
    ) -> None:
        """Log summary of all operations.
        
        Args:
            issue_result: Result from issue processing
            pr_result: Result from PR processing
        """
        logger.info("EXECUTION SUMMARY")
        logger.info("-" * 60)
        
        # Issue summary
        logger.info(f"Issues Processed: {issue_result.total}")
        logger.info(f"  - Successful: {issue_result.successful}")
        logger.info(f"  - Failed: {issue_result.failed}")
        if issue_result.errors:
            logger.info("  - Errors:")
            for error in issue_result.errors:
                logger.info(f"    * {error}")
        
        logger.info("")
        
        # PR summary
        logger.info(f"PRs Processed: {pr_result.total}")
        logger.info(f"  - Successful: {pr_result.successful}")
        logger.info(f"  - Failed: {pr_result.failed}")
        if pr_result.errors:
            logger.info("  - Errors:")
            for error in pr_result.errors:
                logger.info(f"    * {error}")
        
        logger.info("")
        
        # Overall summary
        total_items = issue_result.total + pr_result.total
        total_successful = issue_result.successful + pr_result.successful
        total_failed = issue_result.failed + pr_result.failed
        
        logger.info(f"TOTAL: {total_items} items processed")
        logger.info(f"  - {total_successful} successful")
        logger.info(f"  - {total_failed} failed")
        
        if total_items == 0:
            logger.info("\nNo issues or PRs to process.")
        elif total_failed == 0:
            logger.info("\n✓ All items processed successfully!")
        else:
            logger.warning(f"\n⚠ {total_failed} items failed. Check logs for details.")
