"""Core data models for the universal document processor."""

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Supported document types."""
    ACADEMIC_PAPER = "academic_paper"
    LANGUAGE_TEXTBOOK = "language_textbook"
    GENERIC = "generic"
    CUSTOM = "custom"


class QualityMetrics(BaseModel):
    """Quality metrics for processed documents."""
    paragraphs_merged: int = 0
    headers_removed: int = 0
    formatting_fixes: int = 0
    lines_processed: int = 0
    tables_detected: int = 0
    figures_detected: int = 0
    references_detected: int = 0
    processing_time_seconds: float = 0
    pages_processed: int = 0
    word_count: int = 0

    def calculate_score(self) -> float:
        """Calculate overall quality score (0-100)."""
        if self.lines_processed == 0:
            return 0.0

        # Simple scoring based on processing efficiency
        merge_efficiency = 1.0 - (self.paragraphs_merged / max(self.lines_processed, 1))
        formatting_ratio = self.formatting_fixes / max(self.lines_processed, 1)

        # Higher score = better processing (fewer manual fixes needed)
        score = (merge_efficiency * 60) + (formatting_ratio * 20) + 20
        return min(100.0, max(0.0, score))


class ProcessingProfile(BaseModel):
    """Configuration profile for different document types."""
    name: str
    document_type: DocumentType
    description: str = ""

    # OCR Configuration
    model_name: str = "gemini-2.5-flash"
    batch_size: int = 5
    image_scale: float = 2.0

    # Processing Instructions for LLM
    system_prompt: str
    special_instructions: list[str] = Field(default_factory=list)

    # Post-processing Configuration
    enable_paragraph_merging: bool = True
    enable_header_removal: bool = True
    enable_table_detection: bool = True
    enable_figure_detection: bool = True
    enable_reference_formatting: bool = True

    # Quality thresholds
    min_quality_score: float = 75.0
    max_retries: int = 2

    # Document-specific patterns
    header_patterns: list[str] = Field(default_factory=list)
    section_patterns: list[str] = Field(default_factory=list)
    special_formatting: dict[str, str] = Field(default_factory=dict)


class ProcessingRequest(BaseModel):
    """Request for document processing."""
    input_path: Path
    output_path: Path | None = None
    profile: ProcessingProfile
    start_page: int | None = None
    end_page: int | None = None
    force_reprocess: bool = False


class ProcessingResult(BaseModel):
    """Result of document processing."""
    success: bool
    input_path: Path
    output_path: Path | None = None
    metrics: QualityMetrics
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    processing_time: float = 0
    batch_results: list[dict[str, Any]] = Field(default_factory=list)


class BatchProcessingRequest(BaseModel):
    """Request for batch processing multiple documents."""
    input_directory: Path
    output_directory: Path
    profile: ProcessingProfile
    file_patterns: list[str] = Field(default_factory=lambda: ["*.pdf"])
    recursive: bool = True
    max_parallel: int = 1


class BenchmarkTest(BaseModel):
    """Benchmark test configuration."""
    name: str
    description: str
    test_files: list[Path]
    expected_metrics: QualityMetrics
    profile: ProcessingProfile
