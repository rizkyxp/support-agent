"""GitHub CLI client for GitHub operations."""

import json
import logging
import subprocess
from typing import List, Dict, Optional

from src.utils.errors import GitHubAPIError


logger = logging.getLogger(__name__)

# Global flag to track if auth check has been done
_auth_checked = False


class GitHubCLIClient:
    """Client for GitHub operations using GitHub CLI (gh)."""
    
    def __init__(self, cli_path: str = "gh", organization: Optional[str] = None, skip_auth_check: bool = False):
        """Initialize GitHub CLI client.
        
        Args:
            cli_path: Path to gh CLI executable (default: "gh" in PATH)
            organization: GitHub organization name
            skip_auth_check: Skip authentication check (for thread-safe instances)
        """
        global _auth_checked
        
        self.cli_path = cli_path
        self.organization = organization
        self.current_repo = None
        
        # Only verify CLI once (first instance)
        if not skip_auth_check and not _auth_checked:
            try:
                result = subprocess.run(
                    [self.cli_path, "auth", "status"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info("GitHub CLI authenticated successfully")
                    logger.info(f"Organization: {organization}")
                    _auth_checked = True
                else:
                    raise GitHubAPIError(
                        f"GitHub CLI not authenticated. Run: {self.cli_path} auth login"
                    )
            except FileNotFoundError:
                raise GitHubAPIError(
                    f"GitHub CLI not found at '{self.cli_path}'. "
                    "Please install: https://cli.github.com/"
                )
            except Exception as e:
                logger.warning(f"Could not verify GitHub CLI: {e}")
    
    def set_repository(self, repo_name: str, full_repo_name: str = None):
        """Set current repository.
        
        Args:
            repo_name: Repository name (without organization)
            full_repo_name: Full repository name (org/repo). If None, uses self.organization
        """
        if full_repo_name:
            self.current_repo = full_repo_name
        elif self.organization:
            self.current_repo = f"{self.organization}/{repo_name}"
        else:
            # If no organization and no full_repo_name, we can't set repository
            raise GitHubAPIError(f"Cannot set repository {repo_name}: no organization specified and no full_repo_name provided")
        logger.debug(f"Set current repository: {self.current_repo}")
    
    def get_organization_repositories(self) -> List[str]:
        """Get all repositories in organization.
        
        Returns:
            List of repository names (without organization prefix)
        """
        try:
            cmd = [
                self.cli_path, "repo", "list", self.organization,
                "--json", "name",
                "--limit", "1000"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise GitHubAPIError(f"Failed to list repositories: {result.stderr}")
            
            repos = json.loads(result.stdout)
            repo_names = [repo['name'] for repo in repos]
            
            logger.info(f"Found {len(repo_names)} repositories in {self.organization}")
            return repo_names
            
        except Exception as e:
            logger.error(f"Error getting organization repositories: {e}")
            raise GitHubAPIError(f"Failed to get repositories: {e}")
    
    def search_assigned_issues_in_org(self) -> Dict[str, List[Dict]]:
        """Search for issues assigned to authenticated user across organization.
        
        Uses gh search to find all assigned issues in one command.
        
        Returns:
            Dict mapping repo names to list of issues
        """
        try:
            # Get current username
            whoami_cmd = [self.cli_path, "api", "user", "--jq", ".login"]
            whoami_result = subprocess.run(
                whoami_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            username = whoami_result.stdout.strip()
            
            # Build search query as separate arguments
            cmd = [self.cli_path, "search", "issues"]
            
            # Add organization filter if specified
            if self.organization:
                cmd.append(f"org:{self.organization}")
            
            # Add other filters
            cmd.extend([
                f"assignee:{username}",
                "is:open",
                "is:issue",
                "--json", "number,title,body,url,repository",
                "--limit", "1000"
            ])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"Failed to search issues: {result.stderr}")
                return {}
            
            issues = json.loads(result.stdout)
            
            # Group by repository
            issues_by_repo = {}
            for issue in issues:
                repo_name = issue['repository']['name']
                if repo_name not in issues_by_repo:
                    issues_by_repo[repo_name] = []
                issues_by_repo[repo_name].append(issue)
            
            logger.info(f"Found {len(issues)} assigned issues across {len(issues_by_repo)} repositories")
            return issues_by_repo
            
        except Exception as e:
            logger.error(f"Error searching assigned issues: {e}")
            return {}
    
    def search_prs_with_changes_requested_in_org(self) -> Dict[str, List[Dict]]:
        """Search for PRs with changes requested across organization.
        
        Uses gh search to find all PRs with changes requested in one command.
        
        Returns:
            Dict mapping repo names to list of PRs
        """
        try:
            # Get current username
            whoami_cmd = [self.cli_path, "api", "user", "--jq", ".login"]
            whoami_result = subprocess.run(
                whoami_cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            username = whoami_result.stdout.strip()
            logger.info(f"Searching PRs for user: {username}")
            
            # Build search query as separate arguments
            cmd = [self.cli_path, "search", "prs"]
            
            # Add organization filter if specified
            if self.organization:
                cmd.append(f"org:{self.organization}")
            
            # Add other filters
            cmd.extend([
                f"author:{username}",
                "is:open",
                "review:changes_requested",
                "--json", "number,title,body,url,repository,author",
                "--limit", "1000"
            ])
            
            logger.debug(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"Failed to search PRs: {result.stderr}")
                logger.debug(f"Command output: {result.stdout}")
                return {}
            
            prs = json.loads(result.stdout)
            logger.debug(f"Raw search result: {len(prs)} PRs found")
            
            # Group by repository
            prs_by_repo = {}
            for pr in prs:
                repo_name = pr['repository']['name']
                if repo_name not in prs_by_repo:
                    prs_by_repo[repo_name] = []
                prs_by_repo[repo_name].append(pr)
                logger.debug(f"  PR #{pr['number']} in {repo_name}: {pr['title']}")
            
            logger.info(f"Found {len(prs)} PRs with changes requested across {len(prs_by_repo)} repositories")
            return prs_by_repo
            
        except Exception as e:
            logger.error(f"Error searching PRs with changes requested: {e}")
            return {}
    
    def get_assigned_issues(self) -> List[Dict]:
        """Get issues assigned to authenticated user in current repository.
        
        Returns:
            List of issue dictionaries
        """
        if not self.current_repo:
            raise GitHubAPIError("No repository set. Call set_repository() first.")
        
        try:
            # Use gh issue list with assignee filter
            cmd = [
                self.cli_path, "issue", "list",
                "--repo", self.current_repo,
                "--assignee", "@me",
                "--state", "open",
                "--json", "number,title,body,url,labels",
                "--limit", "100"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"Failed to get issues: {result.stderr}")
                return []
            
            issues = json.loads(result.stdout)
            logger.debug(f"Found {len(issues)} assigned issues in {self.current_repo}")
            return issues
            
        except Exception as e:
            logger.error(f"Error getting assigned issues: {e}")
            return []
    
    def get_prs_with_changes_requested(self) -> List[Dict]:
        """Get PRs with changes requested for authenticated user.
        
        Returns:
            List of PR dictionaries
        """
        if not self.current_repo:
            raise GitHubAPIError("No repository set. Call set_repository() first.")
        
        try:
            # Use gh pr list with author and review-requested filters
            cmd = [
                self.cli_path, "pr", "list",
                "--repo", self.current_repo,
                "--author", "@me",
                "--state", "open",
                "--json", "number,title,url,reviewDecision,reviews",
                "--limit", "100"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"Failed to get PRs: {result.stderr}")
                return []
            
            all_prs = json.loads(result.stdout)
            
            # Filter PRs with changes requested
            # Check both reviewDecision and individual reviews
            prs_with_changes = []
            for pr in all_prs:
                # Check reviewDecision field
                if pr.get('reviewDecision') == 'CHANGES_REQUESTED':
                    prs_with_changes.append(pr)
                    continue
                
                # Also check individual reviews for CHANGES_REQUESTED state
                reviews = pr.get('reviews', [])
                if any(review.get('state') == 'CHANGES_REQUESTED' for review in reviews):
                    prs_with_changes.append(pr)
            
            logger.debug(f"Found {len(prs_with_changes)} PRs with changes requested in {self.current_repo}")
            return prs_with_changes
            
        except Exception as e:
            logger.error(f"Error getting PRs with changes requested: {e}")
            return []
    
    def get_issue(self, issue_number: int) -> Dict:
        """Get issue details.
        
        Args:
            issue_number: Issue number
            
        Returns:
            Issue dictionary
        """
        if not self.current_repo:
            raise GitHubAPIError("No repository set. Call set_repository() first.")
        
        try:
            cmd = [
                self.cli_path, "issue", "view", str(issue_number),
                "--repo", self.current_repo,
                "--json", "number,title,body,url"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise GitHubAPIError(f"Failed to get issue: {result.stderr}")
            
            issue = json.loads(result.stdout)
            return issue
            
        except Exception as e:
            logger.error(f"Error getting issue #{issue_number}: {e}")
            raise GitHubAPIError(f"Failed to get issue: {e}")
    
    def create_pull_request(
        self,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main"
    ) -> Dict:
        """Create a pull request.
        
        Args:
            title: PR title
            body: PR body/description
            head_branch: Source branch
            base_branch: Target branch (default: main)
            
        Returns:
            PR dictionary with url
        """
        if not self.current_repo:
            raise GitHubAPIError("No repository set. Call set_repository() first.")
        
        try:
            cmd = [
                self.cli_path, "pr", "create",
                "--repo", self.current_repo,
                "--title", title,
                "--body", body,
                "--base", base_branch,
                "--head", head_branch
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise GitHubAPIError(f"Failed to create PR: {result.stderr}")
            
            pr_url = result.stdout.strip()
            logger.info(f"Created PR: {pr_url}")
            
            return {'url': pr_url}
            
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            raise GitHubAPIError(f"Failed to create PR: {e}")
    
    def get_pr_details(self, pr_number: int) -> Dict:
        """Get detailed PR information including branch names.
        
        Args:
            pr_number: PR number
            
        Returns:
            Dict with PR details including headRefName and baseRefName
        """
        if not self.current_repo:
            raise GitHubAPIError("No repository set. Call set_repository() first.")
        
        try:
            cmd = [
                self.cli_path, "pr", "view", str(pr_number),
                "--repo", self.current_repo,
                "--json", "number,title,headRefName,baseRefName,author"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise GitHubAPIError(f"Failed to get PR details: {result.stderr}")
            
            pr_details = json.loads(result.stdout)
            return pr_details
            
        except Exception as e:
            logger.error(f"Error getting PR details #{pr_number}: {e}")
            raise GitHubAPIError(f"Failed to get PR details: {e}")
    
    def get_review_comments(self, pr_number: int) -> List[Dict]:
        """Get review comments for a PR (alias for get_pr_review_comments).
        
        Args:
            pr_number: PR number
            
        Returns:
            List of review comment dictionaries
        """
        return self.get_pr_review_comments(pr_number)
    
    def get_pr_review_comments(self, pr_number: int) -> List[Dict]:
        """Get all review comments for a PR.
        
        Fetches:
        1. Top-level review bodies (from all reviews)
        2. Inline code review comments (file-specific, line-specific)
        3. General PR conversation comments
        
        Args:
            pr_number: PR number
            
        Returns:
            List of review comment dictionaries with keys:
                - body: Comment text
                - author: Reviewer username
                - submittedAt: Timestamp
                - file_path: (optional) File path for inline comments
                - line: (optional) Line number for inline comments
        """
        if not self.current_repo:
            raise GitHubAPIError("No repository set. Call set_repository() first.")
        
        all_comments = []
        
        # 1. Get top-level review bodies from ALL reviews
        try:
            cmd = [
                self.cli_path, "pr", "view", str(pr_number),
                "--repo", self.current_repo,
                "--json", "reviews",
                "--jq", '.reviews[] | {body: .body, author: .author.login, submittedAt: .submittedAt, state: .state}'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            review = json.loads(line)
                            # Only include if body is not empty and not just common state changes without messages
                            if review.get('body', '').strip():
                                all_comments.append(review)
                        except json.JSONDecodeError:
                            continue
            else:
                logger.warning(f"Failed to get PR reviews: {result.stderr}")
        except Exception as e:
            logger.warning(f"Error getting top-level reviews: {e}")
        
        # 2. Get inline code review comments (file-specific, line-specific)
        try:
            cmd = [
                self.cli_path, "api",
                f"repos/{self.current_repo}/pulls/{pr_number}/comments",
                "--jq", '.[] | {body: .body, author: .user.login, submittedAt: .created_at, file_path: .path, line: .line, original_line: .original_line, diff_hunk: .diff_hunk}'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            comment = json.loads(line)
                            # Use original_line as fallback if line is None
                            if comment.get('line') is None:
                                comment['line'] = comment.get('original_line')
                            # Remove helper fields
                            comment.pop('original_line', None)
                            all_comments.append(comment)
                        except json.JSONDecodeError:
                            continue
            else:
                logger.warning(f"Failed to get inline review comments: {result.stderr}")
        except Exception as e:
            logger.warning(f"Error getting inline review comments: {e}")

        # 3. Get general PR conversation comments (Issue comments)
        try:
            cmd = [
                self.cli_path, "pr", "view", str(pr_number),
                "--repo", self.current_repo,
                "--json", "comments",
                "--jq", '.comments[] | {body: .body, author: .author.login, submittedAt: .createdAt}'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            comment = json.loads(line)
                            if comment.get('body', '').strip():
                                all_comments.append(comment)
                        except json.JSONDecodeError:
                            continue
            else:
                logger.warning(f"Failed to get PR general comments: {result.stderr}")
        except Exception as e:
            logger.warning(f"Error getting PR general comments: {e}")
        
        logger.debug(f"Found {len(all_comments)} total review comments for PR #{pr_number}")
        return all_comments
    
    def get_pr_diff(self, pr_number: int) -> str:
        """Get diff for a PR.
        
        Args:
            pr_number: PR number
            
        Returns:
            PR diff as string
        """
        if not self.current_repo:
            raise GitHubAPIError("No repository set. Call set_repository() first.")
        
        try:
            cmd = [
                self.cli_path, "pr", "diff", str(pr_number),
                "--repo", self.current_repo
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                raise GitHubAPIError(f"Failed to get PR diff: {result.stderr}")
            
            diff = result.stdout
            logger.debug(f"Got diff for PR #{pr_number} ({len(diff)} bytes)")
            return diff
            
        except Exception as e:
            logger.error(f"Error getting PR diff: {e}")
            raise GitHubAPIError(f"Failed to get PR diff: {e}")
    
    def get_pr_files(self, pr_number: int) -> List[str]:
        """Get list of files changed in a PR.
        
        Args:
            pr_number: PR number
            
        Returns:
            List of file paths
        """
        if not self.current_repo:
            raise GitHubAPIError("No repository set. Call set_repository() first.")
        
        try:
            cmd = [
                self.cli_path, "pr", "view", str(pr_number),
                "--repo", self.current_repo,
                "--json", "files",
                "--jq", ".files[].path"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.warning(f"Failed to get PR files: {result.stderr}")
                return []
            
            files = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            logger.debug(f"Found {len(files)} files in PR #{pr_number}")
            return files
            
        except Exception as e:
            logger.error(f"Error getting PR files: {e}")
            return []
    
    def request_review(self, pr_number: int, reviewers: List[str]):
        """Request review on a PR (alias for request_pr_review).
        
        Args:
            pr_number: PR number
            reviewers: List of reviewer usernames
        """
        return self.request_pr_review(pr_number, reviewers)
    
    def request_pr_review(self, pr_number: int, reviewers: List[str]):
        """Request review on a PR.
        
        Args:
            pr_number: PR number
            reviewers: List of reviewer usernames
        """
        if not self.current_repo:
            raise GitHubAPIError("No repository set. Call set_repository() first.")
        
        try:
            for reviewer in reviewers:
                cmd = [
                    self.cli_path, "api",
                    f"repos/{self.current_repo}/pulls/{pr_number}/requested_reviewers",
                    "-X", "POST",
                    "-f", f"reviewers[]={reviewer}"
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    logger.info(f"Requested review from {reviewer} on PR #{pr_number}")
                else:
                    logger.warning(f"Failed to request review from {reviewer}: {result.stderr}")
                    
        except Exception as e:
            logger.error(f"Error requesting PR review: {e}")

    def add_pr_comment(self, pr_number: int, comment: str):
        """Add a comment to a PR.
        
        Args:
            pr_number: PR number
            comment: Comment text (supports markdown)
        """
        if not self.current_repo:
            raise GitHubAPIError("No repository set. Call set_repository() first.")
        
        try:
            cmd = [
                self.cli_path, "pr", "comment", str(pr_number),
                "--repo", self.current_repo,
                "--body", comment
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                logger.info(f"Added comment to PR #{pr_number}")
            else:
                logger.warning(f"Failed to add comment to PR #{pr_number}: {result.stderr}")
                raise GitHubAPIError(f"Failed to add comment: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Error adding PR comment: {e}")
            raise GitHubAPIError(f"Failed to add comment: {e}")
