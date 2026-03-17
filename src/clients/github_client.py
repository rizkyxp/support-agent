"""GitHub API client for repository operations."""

import logging
from typing import Optional
from datetime import datetime, timezone

from github import Github, GithubException
from github.Issue import Issue as GHIssue
from github.PullRequest import PullRequest as GHPullRequest

from src.utils.errors import GitHubAPIError
from src.models.data_models import Issue, PullRequest, ReviewComment


logger = logging.getLogger(__name__)


class GitHubClient:
    """Client for communicating with GitHub API."""
    
    def __init__(self, token: str, organization: str = None, repo_name: str = None, max_retries: int = 2):
        """Initialize GitHub client with token.
        
        Args:
            token: GitHub personal access token
            organization: Organization name (for org-wide operations)
            repo_name: Repository name in format 'org/repo-name' (for single repo operations)
            max_retries: Maximum number of retries on transient errors
        """
        self.token = token
        self.organization = organization
        self.repo_name = repo_name
        self.max_retries = max_retries
        
        try:
            self.github = Github(token)
            self.user = self.github.get_user()
            
            # Initialize repo if repo_name provided
            self.repo = None
            if repo_name:
                self.repo = self.github.get_repo(repo_name)
                logger.info(f"GitHub client initialized for repo: {repo_name}, user: {self.user.login}")
            elif organization:
                logger.info(f"GitHub client initialized for organization: {organization}, user: {self.user.login}")
            else:
                logger.info(f"GitHub client initialized for user: {self.user.login}")
                
        except GithubException as e:
            raise GitHubAPIError(f"Failed to initialize GitHub client: {e}")
    
    def set_repository(self, repo_name: str, full_repo_name: str = None) -> None:
        """Set the current repository for operations.
        
        Args:
            repo_name: Repository name (without organization prefix)
            full_repo_name: Full repository name (org/repo). If provided, uses this directly.
        """
        try:
            # Use full_repo_name if provided, otherwise use repo_name as-is
            target_repo = full_repo_name or repo_name
            self.repo_name = target_repo
            self.repo = self.github.get_repo(target_repo)
            logger.info(f"Switched to repository: {target_repo}")
        except GithubException as e:
            raise GitHubAPIError(f"Failed to set repository {target_repo}: {e}")
    
    def get_assigned_issues(self) -> list[Issue]:
        """Get open issues assigned to authenticated user.
        
        Returns:
            list[Issue]: List of Issue objects with number, title, body
        """
        try:
            logger.info("Fetching assigned issues")
            
            # Get all open issues
            open_issues = self.repo.get_issues(state='open')
            
            # Filter issues assigned to authenticated user
            assigned_issues = []
            for gh_issue in open_issues:
                # Skip pull requests (they appear as issues in GitHub API)
                if gh_issue.pull_request:
                    continue
                
                # Check if assigned to current user
                if gh_issue.assignee and gh_issue.assignee.login == self.user.login:
                    issue = Issue(
                        number=gh_issue.number,
                        title=gh_issue.title,
                        body=gh_issue.body or "",
                        assignee=gh_issue.assignee.login
                    )
                    assigned_issues.append(issue)
            
            logger.info(f"Found {len(assigned_issues)} assigned issues")
            return assigned_issues
            
        except GithubException as e:
            raise GitHubAPIError(f"Failed to fetch assigned issues: {e}")
    
    def get_prs_with_changes_requested(self) -> list[PullRequest]:
        """Get PRs created by user with latest review state CHANGES_REQUESTED.
        
        Returns:
            list[PullRequest]: List of PR objects with number, branch, comments
        """
        try:
            logger.info("Fetching PRs with changes requested")
            
            # Get all open PRs
            open_prs = self.repo.get_pulls(state='open')
            
            # Filter PRs created by authenticated user with changes requested
            prs_with_changes = []
            for gh_pr in open_prs:
                # Check if created by current user
                if gh_pr.user.login != self.user.login:
                    continue
                
                # Check review state
                reviews = gh_pr.get_reviews()
                latest_review_state = None
                
                # Get latest review state (reviews are ordered by creation time)
                for review in reviews:
                    latest_review_state = review.state
                
                if latest_review_state == "CHANGES_REQUESTED":
                    pr = PullRequest(
                        number=gh_pr.number,
                        title=gh_pr.title,
                        head_branch=gh_pr.head.ref,
                        base_branch=gh_pr.base.ref,
                        author=gh_pr.user.login
                    )
                    prs_with_changes.append(pr)
            
            logger.info(f"Found {len(prs_with_changes)} PRs with changes requested")
            return prs_with_changes
            
        except GithubException as e:
            raise GitHubAPIError(f"Failed to fetch PRs with changes requested: {e}")
            
    def get_latest_changes_requested_time(self, pr_number: int) -> Optional[datetime]:
        """Get the timestamp of the latest review with CHANGES_REQUESTED state.
        
        Args:
            pr_number: Pull request number
            
        Returns:
            datetime: Timestamp of the latest CHANGES_REQUESTED review, or None if not found
        """
        try:
            logger.info(f"Fetching latest CHANGES_REQUESTED review for PR #{pr_number}")
            gh_pr = self.repo.get_pull(pr_number)
            reviews = gh_pr.get_reviews()
            
            latest_time = None
            for review in reviews:
                if review.state == "CHANGES_REQUESTED":
                    # reviews are generally ordered by creation time, but let's be safe
                    if latest_time is None or review.submitted_at > latest_time:
                        latest_time = review.submitted_at
            
            if latest_time:
                logger.info(f"Latest CHANGES_REQUESTED for PR #{pr_number} was at {latest_time}")
            else:
                logger.info(f"No CHANGES_REQUESTED review found for PR #{pr_number}")
                
            return latest_time
            
        except Exception as e:
            logger.warning(f"Failed to fetch latest CHANGES_REQUESTED time for PR #{pr_number}: {e}")
            return None
            
    def get_pr_details(self, pr_number: int) -> PullRequest:
        """Get detailed Pull Request information.
        
        Args:
            pr_number: Pull request number
            
        Returns:
            PullRequest object
        """
        try:
            logger.info(f"Fetching details for PR #{pr_number}")
            gh_pr = self.repo.get_pull(pr_number)
            
            return PullRequest(
                number=gh_pr.number,
                title=gh_pr.title,
                head_branch=gh_pr.head.ref,
                base_branch=gh_pr.base.ref,
                author=gh_pr.user.login
            )
        except GithubException as e:
            raise GitHubAPIError(f"Failed to fetch PR details for #{pr_number}: {e}")
    
    def get_review_comments(self, pr_number: int) -> list[ReviewComment]:
        """Get all review comments for a PR.
        
        Args:
            pr_number: Pull request number
            
        Returns:
            list[ReviewComment]: Comments with body, file, line info
        """
        try:
            logger.info(f"Fetching all review comments for PR #{pr_number}")
            
            gh_pr = self.repo.get_pull(pr_number)
            
            comments = []
            
            # 1. Get top-level review bodies from ALL reviews
            reviews = gh_pr.get_reviews()
            for review in reviews:
                if review.body and review.body.strip():
                    comment = ReviewComment(
                        body=review.body,
                        file_path=None,
                        line=None,
                        reviewer=review.user.login,
                        created_at=review.submitted_at or datetime.now(timezone.utc)
                    )
                    comments.append(comment)
            
            # 2. Get review comments (inline code-specific comments)
            review_comments = gh_pr.get_review_comments()
            for rc in review_comments:
                comment = ReviewComment(
                    body=rc.body,
                    file_path=rc.path,
                    line=rc.line,
                    reviewer=rc.user.login,
                    created_at=rc.created_at,
                    is_resolved=rc.resolved
                )
                comments.append(comment)
                
            # 3. Get general PR conversation comments (Issue comments)
            issue_comments = gh_pr.get_issue_comments()
            for ic in issue_comments:
                if ic.body and ic.body.strip():
                    comment = ReviewComment(
                        body=ic.body,
                        file_path=None,
                        line=None,
                        reviewer=ic.user.login,
                        created_at=ic.created_at
                    )
                    comments.append(comment)
            
            logger.info(f"Found {len(comments)} total review comments for PR #{pr_number}")
            return comments
            
        except GithubException as e:
            raise GitHubAPIError(f"Failed to fetch review comments for PR #{pr_number}: {e}")
    
    def create_pull_request(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str
    ) -> PullRequest:
        """Create a new Pull Request.
        
        Args:
            title: PR title
            body: PR body/description
            head_branch: Source branch
            base_branch: Target branch
            
        Returns:
            PullRequest object
            
        Raises:
            GitHubAPIError: If PR creation fails
        """
        try:
            logger.info(f"Creating PR: {head_branch} -> {base_branch}")
            
            gh_pr = self.repo.create_pull(
                title=title,
                body=body,
                head=head_branch,
                base=base_branch
            )
            
            pr = PullRequest(
                number=gh_pr.number,
                title=gh_pr.title,
                head_branch=gh_pr.head.ref,
                base_branch=gh_pr.base.ref,
                author=gh_pr.user.login
            )
            
            logger.info(f"Created PR #{pr.number}: {title}")
            return pr
            
        except GithubException as e:
            raise GitHubAPIError(f"Failed to create PR: {e}")
    
    def request_review(self, pr_number: int, reviewers: list[str]) -> None:
        """Re-request review from specified reviewers.
        
        Args:
            pr_number: Pull request number
            reviewers: List of reviewer usernames
            
        Raises:
            GitHubAPIError: If review request fails
        """
        try:
            logger.info(f"Requesting review for PR #{pr_number} from: {reviewers}")
            
            gh_pr = self.repo.get_pull(pr_number)
            gh_pr.create_review_request(reviewers=reviewers)
            
            logger.info(f"Successfully requested review for PR #{pr_number}")
            
        except GithubException as e:
            raise GitHubAPIError(f"Failed to request review for PR #{pr_number}: {e}")
