"""Gemini CLI client for code generation using local Gemini CLI."""

import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from src.utils.errors import GeminiAPIError, JSONParseError
from src.models.data_models import Solution


logger = logging.getLogger(__name__)


class GeminiCLIClient:
    """Client for communicating with Gemini via CLI (for Pro accounts)."""
    
    def __init__(
        self,
        cli_path: str = "gemini",
        model: Optional[str] = None,
        max_retries: int = 3
    ):
        """Initialize Gemini CLI client.
        
        Args:
            cli_path: Path to gemini CLI executable (default: "gemini" in PATH)
            model: Model to use (default: auto-detect from CLI or gemini-3-flash)
            max_retries: Maximum number of retries on failure (default: 3)
        """
        self.cli_path = cli_path
        self.max_retries = max_retries
        
        # Auto-detect model if not specified
        if model is None:
            self.model = self._auto_detect_model()
        else:
            self.model = model
        
        # Verify CLI is available
        try:
            result = subprocess.run(
                [self.cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"Gemini CLI client initialized: {result.stdout.strip()}")
                logger.info(f"Using model: {self.model}")
            else:
                logger.warning(f"Gemini CLI may not be properly configured: {result.stderr}")
        except FileNotFoundError:
            raise GeminiAPIError(
                f"Gemini CLI not found at '{self.cli_path}'. "
                "Please install: https://github.com/google-gemini/generative-ai-cli"
            )
        except Exception as e:
            logger.warning(f"Could not verify Gemini CLI: {e}")
    
    def _auto_detect_model(self) -> str:
        """Auto-detect best available model from CLI.
        
        Returns:
            str: Model name to use (returns "auto" to let CLI choose)
        """
        # Use "auto" mode - let Gemini CLI choose the best model
        logger.info("Using auto mode - Gemini CLI will choose the best model")
        return "auto"
    
    def generate_solution(
        self,
        prompt: str,
        system_instruction: Optional[str] = None
    ) -> dict:
        """Generate code solution from prompt using Gemini CLI.
        
        Args:
            prompt: User prompt describing the problem
            system_instruction: Optional system instruction for behavior control
            
        Returns:
            dict: Solution JSON with structure:
                {
                    "files": [
                        {
                            "file_path": "path/to/file.py",
                            "content": "updated file content"
                        }
                    ]
                }
        
        Raises:
            GeminiAPIError: If CLI call fails after retries
            JSONParseError: If response is not valid JSON
        """
        # Default system instruction if not provided
        if system_instruction is None:
            system_instruction = self._get_default_system_instruction()
        
        # Combine system instruction with prompt
        full_prompt = f"{system_instruction}\n\n{prompt}"
        
        # Retry logic
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Gemini CLI call attempt {attempt + 1}/{self.max_retries}")
                
                # Create temporary file for prompt (to handle large prompts)
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(full_prompt)
                    prompt_file = f.name
                
                try:
                    # Call Gemini CLI
                    # Format: gemini -m <model> -p <prompt>
                    # Read prompt from file
                    with open(prompt_file, 'r') as f:
                        prompt_text = f.read()
                    
                    cmd = [
                        self.cli_path,
                        "-m", self.model,
                        "-p", prompt_text
                    ]
                    
                    logger.debug(f"Running command: {self.cli_path} -m {self.model} -p <prompt>")
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=120  # 2 minutes timeout
                    )
                    
                    if result.returncode != 0:
                        error_msg = result.stderr or "Unknown error"
                        logger.error(f"Gemini CLI error: {error_msg}")
                        raise GeminiAPIError(f"Gemini CLI failed: {error_msg}")
                    
                    response_text = result.stdout.strip()
                    logger.debug(f"Gemini CLI raw response length: {len(response_text)} chars")
                    
                    # Clean up response - remove MCP warnings and other prefixes
                    response_text = self._clean_response(response_text)
                    logger.debug(f"Cleaned response: {response_text[:200]}...")
                    
                finally:
                    # Cleanup temp file
                    Path(prompt_file).unlink(missing_ok=True)
                
                # Try to parse as JSON
                try:
                    solution_json = json.loads(response_text)
                    logger.info("Successfully parsed Gemini CLI response as JSON")
                    return solution_json
                except json.JSONDecodeError:
                    # Try to extract JSON from markdown code blocks
                    logger.warning("Failed to parse response as JSON, attempting markdown extraction")
                    solution_json = self._extract_json_from_markdown(response_text)
                    if solution_json:
                        logger.info("Successfully extracted JSON from markdown")
                        return solution_json
                    
                    # If last attempt, raise error
                    if attempt == self.max_retries - 1:
                        raise JSONParseError(f"Failed to parse Gemini CLI response as JSON: {response_text[:200]}")
                    
                    # Otherwise, retry with stricter prompt
                    logger.warning(f"Retry {attempt + 1}/{self.max_retries} with stricter prompt")
                    full_prompt = self._get_stricter_prompt(prompt)
                    
            except subprocess.TimeoutExpired:
                logger.error("Gemini CLI call timed out")
                if attempt == self.max_retries - 1:
                    raise GeminiAPIError("Gemini CLI call timed out after 2 minutes")
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Gemini CLI call failed after {self.max_retries} attempts: {e}")
                    raise GeminiAPIError(f"Gemini CLI call failed: {e}")
                logger.warning(f"Gemini CLI error, retrying: {e}")
        
        raise GeminiAPIError("Gemini CLI call failed after all retries")
    
    def _clean_response(self, response: str) -> str:
        """Clean up Gemini CLI response by removing prefixes and warnings.
        
        Args:
            response: Raw response from Gemini CLI
            
        Returns:
            Cleaned response text
        """
        import re
        
        # Remove common prefixes
        prefixes_to_remove = [
            r'MCP issues detected\. Run /mcp list for status\.',
            r'Loaded cached credentials\.',
            r'Loading extension:.*',
            r'Server .*? supports .*',
            r'\[MCP error\].*',
        ]
        
        cleaned = response
        for prefix_pattern in prefixes_to_remove:
            cleaned = re.sub(prefix_pattern, '', cleaned, flags=re.MULTILINE)
        
        # Remove leading/trailing whitespace and newlines
        cleaned = cleaned.strip()
        
        # Try to find JSON object in the response
        # Look for { ... } pattern
        json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if json_match:
            return json_match.group(0)
        
        return cleaned
    
    def _get_default_system_instruction(self) -> str:
        """Get default system instruction for JSON-only output."""
        return """You are a code generation assistant. You MUST respond with ONLY valid JSON, nothing else.

CRITICAL: Your entire response must be ONLY the JSON object below. No explanations, no markdown, no text before or after.

Output format:
{
  "files": [
    {
      "file_path": "relative/path/to/file.py",
      "content": "complete updated file content"
    }
  ]
}

Rules:
- Return ONLY the JSON object
- Include complete file content, not diffs
- Use relative paths from repository root
- Ensure all syntax is correct
- NO explanations or additional text"""
    
    def _get_stricter_prompt(self, original_prompt: str) -> str:
        """Get stricter prompt emphasizing JSON-only output."""
        return f"""{self._get_default_system_instruction()}

IMPORTANT: Your response must be ONLY valid JSON. Do not include any text before or after the JSON.

{original_prompt}

Remember: Return ONLY the JSON object."""
    
    def _extract_json_from_markdown(self, response: str) -> Optional[dict]:
        """Extract JSON from markdown code blocks if present.
        
        Args:
            response: Response text that may contain JSON in markdown
            
        Returns:
            Parsed JSON dict if found, None otherwise
        """
        import re
        
        # Try to find JSON in markdown code blocks
        patterns = [
            r'```json\s*\n(.*?)\n```',  # ```json ... ```
            r'```\s*\n(.*?)\n```',       # ``` ... ```
            r'`(.*?)`',                   # `...`
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        return None

    def _get_prompt_template(self, template_id: str, default_template: str, **kwargs) -> str:
        """Fetch prompt template from database (if available) and format it, else use default."""
        try:
            import sqlite3
            db_path = Path.cwd() / ".agent_data" / "dashboard.sqlite"
            if db_path.exists():
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='prompt_templates'")
                if cursor.fetchone():
                    cursor.execute("SELECT template_text FROM prompt_templates WHERE id=?", (template_id,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        return row[0].format(**kwargs)
                conn.close()
        except Exception as e:
            logger.warning(f"Could not load custom prompt template for {template_id}, using default: {e}")
        
        # Fallback to default
        try:
            return default_template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing formatting key in prompt template: {e}")
            return default_template

    def fix_and_push(
        self,
        repo_path: Path,
        branch_name: str,
        review_comments: str
    ) -> dict:
        """Use Gemini CLI to fix code based on review comments and push changes."""
        feedback_file = repo_path / ".gemini_feedback.md"
        try:
            logger.info(f"Using Gemini CLI to fix and push changes to {branch_name}")
            
            # Write review comments to a feedback file
            feedback_file.write_text(review_comments, encoding='utf-8')
            logger.debug(f"Wrote review comments to {feedback_file}")
            
            # Construct prompt for Gemini CLI
            default_pr_prompt = """You are a developer working on a Pull Request. You have received review comments.
To fix the issues, please:
1. Read the review comments from `.gemini_feedback.md` in the root directory.
2. IMPORTANT: Read any context files in the `.agents/` or `.context/` directory (if they exist) to understand project standards and architecture.
3. Read the other relevant files in the repository to understand the context.
4. Fix all issues mentioned in the `.gemini_feedback.md` file, ensuring your code adheres to the project standards found in step 2.
5. Create an appropriate commit message based on what you fixed.
6. Commit the changes. **CRITICAL: NEVER commit or stage the `.gemini_feedback.md` file.**
7. Push to branch: {branch_name}

Proceed with fixing the issues, committing, and pushing."""

            prompt = self._get_prompt_template("pr_feedback", default_pr_prompt, branch_name=branch_name)

            # Run Gemini CLI in the repository directory with YOLO mode (auto-approve)
            cmd = [
                self.cli_path,
                "-m", self.model,
                "-p", prompt,
                "--yolo"  # Auto-approve all actions
            ]
            
            logger.debug(f"Running Gemini CLI in {repo_path}")
            
            result = subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error"
                logger.error(f"Gemini CLI error: {error_msg}")
                return {
                    'success': False,
                    'message': f"Gemini CLI failed: {error_msg}"
                }
            
            output = result.stdout.strip()
            logger.info("Gemini CLI completed fix and push")
            logger.debug(f"Output: {output[:500]}...")
            
            return {
                'success': True,
                'message': 'Successfully fixed and pushed changes',
                'output': output
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Gemini CLI timed out")
            return {
                'success': False,
                'message': 'Gemini CLI timed out after 5 minutes'
            }
        except Exception as e:
            logger.error(f"Error running Gemini CLI: {e}")
            return {
                'success': False,
                'message': f"Error: {e}"
            }
        finally:
            # Clean up the feedback file regardless of success or failure
            try:
                if feedback_file.exists():
                    feedback_file.unlink()
                    logger.debug(f"Cleaned up {feedback_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up {feedback_file}: {e}")

    def solve_issue_and_push(
        self,
        repo_path: Path,
        branch_name: str,
        issue_number: int,
        issue_title: str,
        issue_body: str
    ) -> dict:
        """Use Gemini CLI to solve a GitHub issue and push changes."""
        try:
            logger.info(f"Using Gemini CLI to solve issue #{issue_number} and push to {branch_name}")
            
            # Construct prompt for Gemini CLI
            default_issue_prompt = """You are a developer working on resolving a GitHub Issue. Here are the details:

Issue #{issue_number}: {issue_title}

Description:
{issue_body}

Please:
1. IMPORTANT: Read any context files in the `.agents/` or `.context/` directory (if they exist) to understand project standards and architecture.
2. Read the relevant files in the repository to understand the codebase.
3. Implement the fix or feature described in the issue, ensuring your code adheres to the project standards found in step 1.
4. Create an appropriate commit message that references issue #{issue_number}
5. Commit the changes
6. Push to branch: {branch_name}

Proceed with implementing the solution, committing, and pushing."""

            prompt = self._get_prompt_template(
                "issue_resolution", 
                default_issue_prompt, 
                issue_number=issue_number,
                issue_title=issue_title,
                issue_body=issue_body,
                branch_name=branch_name
            )
            
            # Run Gemini CLI in the repository directory with YOLO mode (auto-approve)
            cmd = [
                self.cli_path,
                "-m", self.model,
                "-p", prompt,
                "--yolo"  # Auto-approve all actions
            ]
            
            logger.debug(f"Running Gemini CLI in {repo_path}")
            
            result = subprocess.run(
                cmd,
                cwd=str(repo_path),
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error"
                logger.error(f"Gemini CLI error: {error_msg}")
                return {
                    'success': False,
                    'message': f"Gemini CLI failed: {error_msg}"
                }
            
            output = result.stdout.strip()
            logger.info("Gemini CLI completed issue resolution and push")
            logger.debug(f"Output: {output[:500]}...")
            
            return {
                'success': True,
                'message': f'Successfully resolved issue #{issue_number} and pushed changes',
                'output': output
            }
            
        except subprocess.TimeoutExpired:
            logger.error("Gemini CLI timed out")
            return {
                'success': False,
                'message': 'Gemini CLI timed out after 5 minutes'
            }
        except Exception as e:
            logger.error(f"Error running Gemini CLI: {e}")
            return {
                'success': False,
                'message': f"Error: {e}"
            }
