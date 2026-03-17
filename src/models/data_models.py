"""Data models for GitHub AI Agent."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Issue:
    """GitHub Issue representation."""
    number: int
    title: str
    body: str
    assignee: str


@dataclass
class PullRequest:
    """GitHub Pull Request representation."""
    number: int
    title: str
    head_branch: str
    base_branch: str
    author: str


@dataclass
class ReviewComment:
    """GitHub Review Comment representation."""
    body: str
    file_path: Optional[str]
    line: Optional[int]
    reviewer: str
    created_at: datetime
    is_resolved: bool = False
    diff_hunk: Optional[str] = None


@dataclass
class SolutionFile:
    """Single file in solution JSON."""
    file_path: str
    content: str


@dataclass
class Solution:
    """AI-generated solution."""
    files: list[SolutionFile]
    
    @classmethod
    def from_json(cls, data: dict) -> "Solution":
        """Parse solution from JSON response.
        
        Args:
            data: JSON dict with structure {"files": [{"file_path": "...", "content": "..."}]}
            
        Returns:
            Solution object
            
        Raises:
            ValueError: If JSON structure is invalid
        """
        if "files" not in data:
            raise ValueError("Solution JSON must contain 'files' key")
        
        if not isinstance(data["files"], list):
            raise ValueError("'files' must be an array")
        
        files = []
        for f in data["files"]:
            if "file_path" not in f or "content" not in f:
                raise ValueError("Each file must have 'file_path' and 'content' keys")
            
            files.append(SolutionFile(
                file_path=f["file_path"],
                content=f["content"]
            ))
        
        return cls(files=files)


@dataclass
class ProcessingResult:
    """Result of processing multiple items."""
    total: int = 0
    successful: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)
    
    def add_success(self) -> None:
        """Record a successful operation."""
        self.successful += 1
    
    def add_failure(self, error: str) -> None:
        """Record a failed operation.
        
        Args:
            error: Error message describing the failure
        """
        self.failed += 1
        self.errors.append(error)
