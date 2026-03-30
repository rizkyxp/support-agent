"""Configuration management for GitHub AI Agent."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from src.utils.errors import ConfigurationError


@dataclass
class Configuration:
    """Agent configuration loaded from environment."""
    
    github_organization: Optional[str]  # Optional - reads all orgs if not specified
    repositories_dir: Path
    github_cli_path: str = "gh"
    default_target_base_branch: str = "main"
    gemini_cli_path: str = "gemini"
    gemini_cli_model: Optional[str] = None  # None = auto-detect
    process_issues: bool = True  # Enable/disable issue processing
    process_prs: bool = True  # Enable/disable PR processing
    auto_request_review: bool = True  # Enable/disable auto-request review after fixing
    data_dir: Path = Path.cwd() / ".agent_data"  # Directory for agent metadata
    
    # Change Protection Settings
    change_protection_enabled: bool = True     # Enable/disable change protection system
    change_protection_mode: str = "warn"       # "warn" (log warning) or "halt" (stop before push)
    dry_run_mode: bool = False                 # Preview changes without pushing
    max_pr_diff_size: int = 50000              # Max characters of PR diff in prompt
    include_pr_diff_in_prompt: bool = True     # Include PR diff context in Gemini prompt
    
    @classmethod
    def load(cls, env_file: Optional[str] = None) -> "Configuration":
        """Load configuration from environment or config file.
        
        Args:
            env_file: Optional path to .env file
            
        Returns:
            Configuration object
            
        Raises:
            ConfigurationError: If required values missing or invalid
        """
        # Load from .env file if exists
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
            
        # Optional: Load override from SQLite Dashboard DB
        db_path = Path.cwd() / ".agent_data" / "dashboard.sqlite"
        if db_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                # Check if table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='global_config'")
                if cursor.fetchone():
                    cursor.execute("SELECT key, value FROM global_config")
                    for row in cursor.fetchall():
                        os.environ[row[0]] = row[1]
                conn.close()
            except Exception as e:
                print(f"Warning: Failed to load config from dashboard db: {e}")

        
        # Load required fields
        github_organization = os.getenv("GITHUB_ORGANIZATION") or os.getenv("GITHUB_ORG")  # Optional
        
        # Load optional fields with defaults
        default_target_base_branch = os.getenv("DEFAULT_TARGET_BASE_BRANCH", "main")
        repositories_dir_str = os.getenv("REPOSITORIES_DIR", ".repositories")
        github_cli_path = os.getenv("GITHUB_CLI_PATH", "gh")
        gemini_cli_path = os.getenv("GEMINI_CLI_PATH", "gemini")
        
        # Auto-detect model if not specified (None = auto-detect from CLI)
        gemini_cli_model_str = os.getenv("GEMINI_CLI_MODEL")
        gemini_cli_model = gemini_cli_model_str if gemini_cli_model_str else None
        
        # Processing mode configuration
        process_issues = os.getenv("PROCESS_ISSUES", "true").lower() in ("true", "1", "yes")
        process_prs = os.getenv("PROCESS_PRS", "true").lower() in ("true", "1", "yes")
        auto_request_review = os.getenv("AUTO_REQUEST_REVIEW", "true").lower() in ("true", "1", "yes")
        
        # Change Protection Settings
        change_protection_enabled = os.getenv("CHANGE_PROTECTION_ENABLED", "true").lower() in ("true", "1", "yes")
        change_protection_mode = os.getenv("CHANGE_PROTECTION_MODE", "warn").lower()
        if change_protection_mode not in ("warn", "halt"):
            change_protection_mode = "warn"
            
        dry_run_mode = os.getenv("DRY_RUN_MODE", "false").lower() in ("true", "1", "yes")
        max_pr_diff_size = int(os.getenv("MAX_PR_DIFF_SIZE", "50000"))
        include_pr_diff_in_prompt = os.getenv("INCLUDE_PR_DIFF_IN_PROMPT", "true").lower() in ("true", "1", "yes")
        
        # Resolve repositories directory path - always relative to project root
        repositories_dir = Path.cwd() / repositories_dir_str
        
        # Create configuration object
        config = cls(
            github_organization=github_organization,
            repositories_dir=repositories_dir,
            github_cli_path=github_cli_path,
            default_target_base_branch=default_target_base_branch,
            gemini_cli_path=gemini_cli_path,
            gemini_cli_model=gemini_cli_model,
            process_issues=process_issues,
            process_prs=process_prs,
            auto_request_review=auto_request_review,
            change_protection_enabled=change_protection_enabled,
            change_protection_mode=change_protection_mode,
            dry_run_mode=dry_run_mode,
            max_pr_diff_size=max_pr_diff_size,
            include_pr_diff_in_prompt=include_pr_diff_in_prompt
        )
        
        # Validate configuration
        config.validate()
        
        return config
    
    def validate(self) -> None:
        """Validate all configuration values.
        
        Raises:
            ConfigurationError: If invalid
        """
        # Create repositories directory if it doesn't exist
        if not self.repositories_dir.exists():
            try:
                self.repositories_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to create repositories directory: {self.repositories_dir}: {e}"
                )
        
        # Create data directory if it doesn't exist
        if not self.data_dir.exists():
            try:
                self.data_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to create data directory: {self.data_dir}: {e}"
                )
