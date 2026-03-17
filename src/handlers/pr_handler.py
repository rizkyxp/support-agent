"""Pull Request handling workflow."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.clients.gemini_client import GeminiClient
from src.clients.github_client import GitHubClient
from src.git.git_manager import GitManager
from src.config import Configuration
from src.models.data_models import PullRequest, ProcessingResult, ReviewComment


logger = logging.getLogger(__name__)


class PRHandler:
    """Handler for PR review feedback workflow."""
    
    def __init__(
        self,
        github_client: GitHubClient,
        gemini_client: GeminiClient,
        git_manager: GitManager,
        config: Configuration,
        repo_path: Path = None
    ):
        """Initialize PR handler with dependencies.
        
        Args:
            github_client: GitHub API client
            gemini_client: Gemini API client
            git_manager: Git operations manager
            config: Agent configuration
            repo_path: Path to repository (if None, uses config.repositories_dir)
        """
        self.github_client = github_client
        self.gemini_client = gemini_client
        self.git_manager = git_manager
        self.config = config
        self.repo_path = repo_path or config.repositories_dir
        
        # Track last review request timestamp per PR in central data directory
        self.last_review_request_file = self.config.data_dir / 'last_review_requests.json'
        
        logger.info("PR handler initialized")
    
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

    def process_prs(self, prs_data: list = None) -> ProcessingResult:
        """Process all PRs with changes requested.
        
        For each PR:
        1. Checkout to PR branch
        2. Generate fixes based on review comments
        3. Apply fixes to local files
        4. Commit and push
        5. Re-request review
        
        Args:
            prs_data: Optional list of PR dicts from search. If None, fetches from GitHub.
        
        Returns:
            ProcessingResult: Summary of successful and failed operations
        """
        logger.info("Starting PR processing")
        
        # Get PRs with changes requested
        if prs_data is None:
            try:
                prs = self.github_client.get_prs_with_changes_requested()
            except Exception as e:
                logger.error(f"Failed to fetch PRs with changes requested: {e}")
                result = ProcessingResult(total=0, successful=0, failed=0)
                result.add_failure(f"Failed to fetch PRs: {e}")
                return result
        else:
            # Convert PR dicts to PullRequest objects
            prs = []
            for pr_dict in prs_data:
                try:
                    # Get full PR details including branch names
                    # Both clients now return a PullRequest object
                    pr = self.github_client.get_pr_details(pr_dict['number'])
                    prs.append(pr)
                except Exception as e:
                    logger.error(f"Failed to convert PR #{pr_dict.get('number', '?')}: {e}")
                    continue
        
        if not prs:
            logger.info("No PRs with changes requested found")
            return ProcessingResult(total=0, successful=0, failed=0)
        
        # Process each PR
        result = ProcessingResult(total=len(prs))
        for pr in prs:
            try:
                logger.info(f"Processing PR #{pr.number}: {pr.title}")
                success = self._process_single_pr(pr)
                if success:
                    result.add_success()
                    self._record_run_history("PR", pr.number, "SUCCESS", "Processed PR feedback")
                else:
                    result.add_failure(f"PR #{pr.number} processing returned False")
                    self._record_run_history("PR", pr.number, "FAILED", "Processing returned False")
            except Exception as e:
                logger.error(f"Error processing PR #{pr.number}: {e}", exc_info=True)
                result.add_failure(f"PR #{pr.number}: {str(e)}")
                self._record_run_history("PR", pr.number, "FAILED", str(e))
        
        logger.info(f"PR processing complete: {result.successful}/{result.total} successful")
        return result
    
    def _process_single_pr(self, pr: PullRequest) -> bool:
        """Process a single PR using Gemini CLI.
        
        Workflow:
        1. Checkout to PR branch
        2. Get review comments (only new ones since last review request)
        3. Delegate to Gemini CLI to fix, commit, and push
        4. Re-request review
        5. Save timestamp for next iteration
        
        Args:
            pr: PR to process
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Step 1: Checkout to PR branch and pull latest
            logger.info(f"Checking out to PR branch: {pr.head_branch}")
            self.git_manager.checkout_and_pull(pr.head_branch)
            
            # Step 2: Get filtering boundary
            last_request_time = self._get_last_review_request_time(pr.number)
            remote_time = self.github_client.get_latest_changes_requested_time(pr.number)
            last_commit_time = pr.last_commit_at
            
            # Determine boundary
            filter_boundary = last_request_time
            
            # 1. Incorporate latest Changes Requested time
            if remote_time:
                # Add 5 minute safety buffer before remote_time to capture inline comments 
                # submitted with the review
                from datetime import timedelta
                buffered_remote = remote_time - timedelta(minutes=5)
                
                if filter_boundary is None or buffered_remote > filter_boundary:
                    filter_boundary = buffered_remote
                    logger.info(f"Using buffered remote Changes Requested boundary: {filter_boundary}")

            # 2. Incorporate latest commit time
            # If a commit was made after the last review request or bot action,
            # we should skip any comments before that commit as they are presumably handled.
            if last_commit_time:
                if filter_boundary is None or last_commit_time > filter_boundary:
                    filter_boundary = last_commit_time
                    logger.info(f"Using latest commit boundary: {filter_boundary}")
            
            if not filter_boundary:
                logger.info("No previous filter boundary found, processing all unresolved comments")
            else:
                logger.info(f"Final filtering boundary: {filter_boundary}")
            
            # Step 3: Get review comments
            logger.info("Fetching review comments")
            comments_all = self.github_client.get_review_comments(pr.number)
            
            # Filter comments by timestamp and resolution status
            comments = []
            for comment in comments_all:
                try:
                    # Log basic info for debugging
                    comment_id_str = f"#{comment.id}" if comment.id else "no-id"
                    logger.debug(f"Evaluating comment {comment_id_str} from {comment.reviewer} (created {comment.created_at}, resolved={comment.is_resolved})")
                    
                    # Filter 1: Resolution status
                    if comment.is_resolved:
                        logger.info(f"Skipping comment {comment_id_str}: Already marked as resolved")
                        continue
                        
                    # Filter 2: Timestamp boundary
                    if filter_boundary is not None and comment.created_at <= filter_boundary:
                        logger.info(f"Skipping comment {comment_id_str}: Created before/at filter boundary ({comment.created_at} <= {filter_boundary})")
                        continue
                    
                    # If we passed both filters, include the comment
                    logger.info(f"Accepted comment {comment_id_str} for processing")
                    comments.append(comment)
                    
                except Exception as e:
                    logger.warning(f"Failed to evaluate review comment: {e}")
                    continue
            
            if not comments:
                logger.info("No new review comments found, skipping PR")
                return True
            
            logger.info(f"Found {len(comments)} new review comments to process")
            
            # Step 4: Format review comments for Gemini CLI
            logger.info(f"Formatting {len(comments)} review comments")
            formatted_comments = self._format_review_comments(comments)
            
            # Step 5: Delegate to Gemini CLI to fix, commit, and push
            logger.info("Delegating to Gemini CLI to fix, commit, and push")
            result = self.gemini_client.fix_and_push(
                repo_path=self.repo_path,
                branch_name=pr.head_branch,
                review_comments=formatted_comments
            )
            
            if not result['success']:
                logger.error(f"Gemini CLI failed: {result['message']}")
                return False
            
            logger.info("Gemini CLI successfully fixed and pushed changes")
            
            # Step 6: Resolve the comments that were processed
            logger.info(f"Resolving {len(comments)} processed comments")
            for comment in comments:
                # Only "inline" comments can be resolved. "review" and "issue" comments don't have a resolved state.
                if comment.id and comment.comment_type == "inline":
                    try:
                        self.github_client.resolve_review_comment(comment.id, node_id=comment.node_id)
                    except Exception as e:
                        logger.warning(f"Failed to resolve comment {comment.id}: {e}")
            
            # Step 7: Get reviewers who requested changes
            reviewers = self._get_reviewers_who_requested_changes(comments)
            
            # Step 8: Re-request review (no comment posting)
            if reviewers and self.config.auto_request_review:
                logger.info(f"Re-requesting review from: {reviewers}")
                self.github_client.request_review(pr.number, reviewers)
                
                # Step 9: Save timestamp of this review request
                self._save_review_request_time(pr.number)
                logger.info(f"Saved review request timestamp for PR #{pr.number}")
            elif reviewers:
                logger.info(f"Skipping review re-request automatically due to config flag.")
            
            logger.info(f"Successfully processed PR #{pr.number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to process PR #{pr.number}: {e}", exc_info=True)
            return False
    
    def _get_reviewers_who_requested_changes(self, comments: list[ReviewComment]) -> list[str]:
        """Extract reviewer usernames who requested changes.
        
        Args:
            comments: List of review comments
            
        Returns:
            list[str]: Unique reviewer usernames
        """
        reviewers = set()
        for comment in comments:
            reviewers.add(comment.reviewer)
        return list(reviewers)
    
    def _format_review_comments(self, comments: list[ReviewComment]) -> str:
        """Format review comments for Gemini CLI.
        
        Args:
            comments: List of review comments
            
        Returns:
            str: Formatted review comments
        """
        formatted = []
        for i, comment in enumerate(comments, 1):
            formatted.append(f"Comment {i}:")
            formatted.append(f"Reviewer: {comment.reviewer}")
            if comment.file_path:
                formatted.append(f"File: {comment.file_path}")
            if comment.line:
                formatted.append(f"Line: {comment.line}")
            if comment.diff_hunk:
                formatted.append(f"Code context:\n{comment.diff_hunk}")
            formatted.append(f"Comment: {comment.body}")
            formatted.append("")  # Empty line between comments
        
        return "\n".join(formatted)
    
    def _get_last_review_request_time(self, pr_number: int) -> Optional[datetime]:
        """Get timestamp of last review request for a PR.
        
        Args:
            pr_number: PR number
            
        Returns:
            datetime: Timestamp of last review request, or None if not found
        """
        try:
            if not self.last_review_request_file.exists():
                return None
            
            data = json.loads(self.last_review_request_file.read_text())
            timestamp_str = data.get(str(pr_number))
            
            if timestamp_str:
                dt = datetime.fromisoformat(timestamp_str)
                if dt.tzinfo is None:
                    # Correctly convert local wall-clock time to UTC
                    dt = dt.astimezone(timezone.utc)
                return dt
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to read last review request time: {e}")
            return None
    
    def _save_review_request_time(self, pr_number: int):
        """Save timestamp of review request for a PR.
        
        Args:
            pr_number: PR number
        """
        try:
            # Create directory if needed
            self.last_review_request_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Load existing data
            data = {}
            if self.last_review_request_file.exists():
                try:
                    data = json.loads(self.last_review_request_file.read_text())
                except:
                    pass
            
            # Update timestamp for this PR
            data[str(pr_number)] = datetime.now(timezone.utc).isoformat()
            
            # Save back to file
            self.last_review_request_file.write_text(json.dumps(data, indent=2))
            
        except Exception as e:
            logger.warning(f"Failed to save review request time: {e}")
