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
    
    gemini_api_key: str
    github_organization: Optional[str]  # Optional - reads all orgs if not specified
    repositories_dir: Path
    use_github_cli: bool = True  # Default to GitHub CLI
    github_cli_path: str = "gh"
    github_token: Optional[str] = None  # Optional, for API mode only
    default_target_base_branch: str = "main"
    use_gemini_cli: bool = False
    gemini_cli_path: str = "gemini"
    gemini_cli_model: Optional[str] = None  # None = auto-detect
    process_issues: bool = True  # Enable/disable issue processing
    process_prs: bool = True  # Enable/disable PR processing
    auto_request_review: bool = True  # Enable/disable auto-request review after fixing
    data_dir: Path = Path.cwd() / ".agent_data"  # Directory for agent metadata
    
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
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        github_organization = os.getenv("GITHUB_ORGANIZATION") or os.getenv("GITHUB_ORG")  # Optional
        
        # Check if using GitHub CLI instead of token
        use_github_cli = os.getenv("USE_GITHUB_CLI", "true").lower() in ("true", "1", "yes")
        github_token = os.getenv("GITHUB_TOKEN")  # Optional if using CLI
        
        # Check if using Gemini CLI instead of API (default to true)
        use_gemini_cli = os.getenv("USE_GEMINI_CLI", "true").lower() in ("true", "1", "yes")
        
        # Validate required fields
        if not use_gemini_cli and not gemini_api_key:
            raise ConfigurationError(
                "GEMINI_API_KEY is required (or set USE_GEMINI_CLI=true to use Gemini CLI)"
            )
        if not use_github_cli and not github_token:
            raise ConfigurationError(
                "GITHUB_TOKEN is required (or set USE_GITHUB_CLI=true to use GitHub CLI)"
            )
        
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
        
        # Resolve repositories directory path - always relative to project root
        repositories_dir = Path.cwd() / repositories_dir_str
        
        # Create configuration object
        config = cls(
            gemini_api_key=gemini_api_key or "",  # Empty string if using CLI
            github_organization=github_organization,
            repositories_dir=repositories_dir,
            use_github_cli=use_github_cli,
            github_cli_path=github_cli_path,
            github_token=github_token,
            default_target_base_branch=default_target_base_branch,
            use_gemini_cli=use_gemini_cli,
            gemini_cli_path=gemini_cli_path,
            gemini_cli_model=gemini_cli_model,
            process_issues=process_issues,
            process_prs=process_prs,
            auto_request_review=auto_request_review
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
