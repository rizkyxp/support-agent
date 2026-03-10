"""Webhook server for GitHub events."""

import logging
import hmac
import hashlib
from flask import Flask, request, jsonify
from typing import Optional
import threading
import queue

from src.config import Configuration
from src.multi_repo_agent import MultiRepoAgent


logger = logging.getLogger(__name__)


class WebhookServer:
    """GitHub webhook server for event-driven processing."""
    
    def __init__(self, config: Configuration, webhook_secret: Optional[str] = None, port: int = 5000):
        """Initialize webhook server.
        
        Args:
            config: Agent configuration
            webhook_secret: GitHub webhook secret for signature verification
            port: Port to run server on (default: 5000)
        """
        self.config = config
        self.webhook_secret = webhook_secret
        self.port = port
        self.app = Flask(__name__)
        self.event_queue = queue.Queue()
        self.agent = MultiRepoAgent(config)
        
        # Setup routes
        self._setup_routes()
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self._process_events, daemon=True)
        self.worker_thread.start()
        
        logger.info(f"Webhook server initialized on port {port}")
    
    def _setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/webhook', methods=['POST'])
        def webhook():
            """Handle GitHub webhook events."""
            try:
                # Verify signature if secret is set
                if self.webhook_secret:
                    if not self._verify_signature(request):
                        logger.warning("Invalid webhook signature")
                        return jsonify({'error': 'Invalid signature'}), 401
                
                # Get event type
                event_type = request.headers.get('X-GitHub-Event')
                payload = request.json
                
                logger.info(f"Received webhook event: {event_type}")
                
                # Process relevant events
                if event_type == 'pull_request_review':
                    self._handle_pr_review(payload)
                elif event_type == 'issues':
                    self._handle_issue(payload)
                else:
                    logger.debug(f"Ignoring event type: {event_type}")
                
                return jsonify({'status': 'ok'}), 200
                
            except Exception as e:
                logger.error(f"Error processing webhook: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'queue_size': self.event_queue.qsize()
            }), 200
    
    def _verify_signature(self, request) -> bool:
        """Verify GitHub webhook signature.
        
        Args:
            request: Flask request object
            
        Returns:
            bool: True if signature is valid
        """
        signature = request.headers.get('X-Hub-Signature-256')
        if not signature:
            return False
        
        # Compute expected signature
        mac = hmac.new(
            self.webhook_secret.encode(),
            msg=request.data,
            digestmod=hashlib.sha256
        )
        expected_signature = 'sha256=' + mac.hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(signature, expected_signature)
    
    def _handle_pr_review(self, payload: dict):
        """Handle pull request review event.
        
        Args:
            payload: Webhook payload
        """
        action = payload.get('action')
        review = payload.get('review', {})
        pr = payload.get('pull_request', {})
        repo = payload.get('repository', {})
        
        # Only process "changes_requested" reviews
        if action == 'submitted' and review.get('state') == 'changes_requested':
            repo_name = repo.get('full_name')
            pr_number = pr.get('number')
            pr_author = pr.get('user', {}).get('login')
            
            # Check if PR is authored by the authenticated user
            # (We'll process this in the worker thread)
            logger.info(f"PR #{pr_number} in {repo_name} has changes requested")
            
            self.event_queue.put({
                'type': 'pr_review',
                'repo': repo_name,
                'pr_number': pr_number,
                'pr_author': pr_author
            })
    
    def _handle_issue(self, payload: dict):
        """Handle issue event.
        
        Args:
            payload: Webhook payload
        """
        action = payload.get('action')
        issue = payload.get('issue', {})
        repo = payload.get('repository', {})
        assignee = payload.get('assignee', {})
        
        # Only process "assigned" events
        if action == 'assigned':
            repo_name = repo.get('full_name')
            issue_number = issue.get('number')
            assignee_login = assignee.get('login')
            
            logger.info(f"Issue #{issue_number} in {repo_name} assigned to {assignee_login}")
            
            self.event_queue.put({
                'type': 'issue_assigned',
                'repo': repo_name,
                'issue_number': issue_number,
                'assignee': assignee_login
            })
    
    def _process_events(self):
        """Process events from queue (runs in background thread)."""
        logger.info("Event processor started")
        
        while True:
            try:
                # Get event from queue (blocking)
                event = self.event_queue.get()
                
                logger.info(f"Processing event: {event['type']} for {event['repo']}")
                
                # Process the specific repository
                self._process_repository(event['repo'])
                
                self.event_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing event: {e}", exc_info=True)
    
    def _process_repository(self, repo_full_name: str):
        """Process a specific repository.
        
        Args:
            repo_full_name: Full repository name (org/repo)
        """
        try:
            # Extract repo name (without org)
            repo_name = repo_full_name.split('/')[-1]
            
            # Set repository in GitHub client
            self.agent.github_client.set_repository(repo_name)
            
            # Check if there's work to do
            issues = self.agent.github_client.get_assigned_issues()
            prs = self.agent.github_client.get_prs_with_changes_requested()
            
            if not issues and not prs:
                logger.info(f"No work to do for {repo_name}")
                return
            
            logger.info(f"Processing {repo_name}: {len(issues)} issues, {len(prs)} PRs")
            
            # Ensure repository is cloned
            repo_path = self.agent.repo_manager.ensure_repository_cloned(repo_name)
            
            # Initialize Git manager
            from src.git.git_manager import GitManager
            git_manager = GitManager(repo_path=repo_path)
            
            # Initialize handlers
            from src.handlers.issue_handler import IssueHandler
            from src.handlers.pr_handler import PRHandler
            
            issue_handler = IssueHandler(
                github_client=self.agent.github_client,
                gemini_client=self.agent.gemini_client,
                git_manager=git_manager,
                config=self.config,
                repo_path=repo_path
            )
            pr_handler = PRHandler(
                github_client=self.agent.github_client,
                gemini_client=self.agent.gemini_client,
                git_manager=git_manager,
                config=self.config,
                repo_path=repo_path
            )
            
            # Process issues
            if issues:
                logger.info(f"Processing {len(issues)} issues")
                issue_handler.process_issues()
            
            # Process PRs
            if prs:
                logger.info(f"Processing {len(prs)} PRs")
                pr_handler.process_prs()
            
            logger.info(f"✓ Completed processing {repo_name}")
            
        except Exception as e:
            logger.error(f"Error processing repository {repo_full_name}: {e}", exc_info=True)
    
    def run(self):
        """Run the webhook server."""
        logger.info(f"Starting webhook server on port {self.port}")
        logger.info("Listening for GitHub events:")
        logger.info("  - pull_request_review (changes_requested)")
        logger.info("  - issues (assigned)")
        
        self.app.run(host='0.0.0.0', port=self.port, debug=False)
