"""Pydantic models for the table filler system."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FieldType(str, Enum):
    """Supported field types."""

    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    CURRENCY = "currency"
    PERCENTAGE = "percentage"
    PHONE = "phone"
    EMAIL = "email"
    ID_NUMBER = "id_number"


class ProcessingStatus(str, Enum):
    """Processing status for verification results."""

    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class FormField(BaseModel):
    """Configuration for a single form field."""

    name: str = Field(..., description="Field name (unique identifier)")
    description: str = Field(default="", description="What this field represents")
    field_type: FieldType = Field(default=FieldType.TEXT, description="Data type")
    required: bool = Field(default=False, description="Whether field is required")
    validation_rules: dict[str, Any] = Field(
        default_factory=dict, description="Optional validation rules"
    )
    aliases: list[str] = Field(
        default_factory=list, description="Alternative names for this field in documents"
    )


class FieldValue(BaseModel):
    """Extracted value for a single field."""

    value: str | None = Field(default=None, description="Extracted value")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confidence score 0.0-1.0"
    )
    source_text: str | None = Field(
        default=None, description="Original text from which value was extracted"
    )
    page_number: int | None = Field(
        default=None, description="Page number where value was found"
    )


class ExtractionResult(BaseModel):
    """Result of field extraction for a single PDF."""

    pdf_path: str = Field(..., description="Source PDF path")
    fields: dict[str, FieldValue] = Field(
        default_factory=dict, description="Extracted field values"
    )
    ocr_page_count: int = Field(default=0, description="Number of pages processed")
    extraction_notes: str = Field(default="", description="Notes from extraction process")


class VerificationIssue(BaseModel):
    """A single verification issue found by the checker."""

    field_name: str = Field(..., description="Name of the problematic field")
    issue_type: str = Field(
        ...,
        description="Type: hallucination, misattribution, missing, format_error, inconsistent",
    )
    message: str = Field(..., description="Description of the issue")
    original_value: str | None = Field(default=None, description="Original extracted value")
    corrected_value: str | None = Field(default=None, description="Suggested correction")


class VerificationResult(BaseModel):
    """Result of verification for a single extraction."""

    status: ProcessingStatus = Field(..., description="Overall verification status")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall confidence score"
    )
    issues: list[VerificationIssue] = Field(
        default_factory=list, description="List of issues found"
    )
    corrected_fields: dict[str, FieldValue] = Field(
        default_factory=dict, description="Corrected field values if any"
    )
    verification_notes: str = Field(default="", description="Notes from verification")


class SinglePdfResult(BaseModel):
    """Complete processing result for a single PDF."""

    pdf_path: str = Field(..., description="Source PDF path")
    status: ProcessingStatus = Field(..., description="Final status")
    confidence: float = Field(default=0.0, description="Final confidence score")
    final_record: dict[str, FieldValue] = Field(
        default_factory=dict, description="Final extracted record"
    )
    issues: list[VerificationIssue] = Field(
        default_factory=list, description="Issues found during processing"
    )
    error: str | None = Field(default=None, description="Error message if failed")


class BatchResult(BaseModel):
    """Aggregated results from batch processing."""

    total_count: int = Field(..., description="Total PDFs processed")
    successful: list[SinglePdfResult] = Field(
        default_factory=list, description="Successfully processed PDFs"
    )
    needs_review: list[SinglePdfResult] = Field(
        default_factory=list, description="PDFs needing human review"
    )
    failed: list[SinglePdfResult] = Field(
        default_factory=list, description="Failed PDFs"
    )

    @property
    def successful_count(self) -> int:
        return len(self.successful)

    @property
    def needs_review_count(self) -> int:
        return len(self.needs_review)

    @property
    def failed_count(self) -> int:
        return len(self.failed)
