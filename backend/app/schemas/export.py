"""Export schemas for API validation"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, UUID4, Field


class ConversationExportRequest(BaseModel):
    """Schema for conversation export request"""

    format: Literal["pdf", "json"] = Field(
        default="pdf", description="Export format (pdf or json)"
    )
    include_metadata: bool = Field(
        default=True, description="Include metadata (timestamps, crisis info)"
    )
    include_system_messages: bool = Field(
        default=False, description="Include system messages in export"
    )


class ProgressReportRequest(BaseModel):
    """Schema for progress report generation request"""

    format: Literal["pdf", "json"] = Field(default="pdf", description="Report format")
    include_statistics: bool = Field(default=True, description="Include usage statistics")
    include_crisis_history: bool = Field(default=True, description="Include crisis events")
    include_emotion_timeline: bool = Field(default=True, description="Include emotion timeline")
    date_from: Optional[datetime] = Field(None, description="Start date for report")
    date_to: Optional[datetime] = Field(None, description="End date for report")


class AllDataExportRequest(BaseModel):
    """Schema for complete data export request (GDPR compliance)"""

    format: Literal["json", "zip"] = Field(
        default="json", description="Export format (json or zip archive)"
    )
    include_deleted: bool = Field(
        default=False, description="Include soft-deleted data"
    )


class ExportResponse(BaseModel):
    """Schema for export response"""

    success: bool
    export_id: str
    format: str
    file_size_bytes: Optional[int] = None
    download_url: str
    expires_at: datetime
    created_at: datetime


class ExportStatusResponse(BaseModel):
    """Schema for export status check"""

    export_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress_percent: int = Field(ge=0, le=100)
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
