from typing import List, Optional, Union

from pydantic import BaseModel, Field, validator


# Schema for file upload
class FileUploadResponse(BaseModel):
    message: str
    data_id: Optional[str]
    filename: Optional[str]


# Schema for analytics queries
class AnalyticsQuery(BaseModel):
    data_id: str = Field(..., description="Unique identifier of the dataset to analyze")
    query: str = Field(..., description="User's query or instruction for the dataset")

    @validator("query")
    def validate_query(cls, value):
        if not value.strip():
            raise ValueError("Query cannot be empty")
        return value


# Schema for analysis result
class AnalysisResult(BaseModel):
    result: Union[str, dict] = Field(
        ..., description="Result of the analysis or computation"
    )
    error: Optional[str] = Field(None, description="Error message, if any")


# Schema for visualization result
class VisualizationResult(BaseModel):
    image_base64: str = Field(
        ..., description="Base64-encoded string of the generated visualization"
    )
    error: Optional[str] = Field(None, description="Error message, if any")


# Schema for chat message
class ChatRequest(BaseModel):
    data_id: str = Field(..., description="Unique identifier of the dataset to analyze")
    message: str = Field(..., description="User's chat message")

    @validator("message")
    def validate_message(cls, value):
        if not value.strip():
            raise ValueError("Message cannot be empty")
        return value


class ChatResponse(BaseModel):
    response: str = Field(..., description="Chatbot's response to the user's message")
    error: Optional[str] = Field(None, description="Error message, if any")


# Schema for report generation
class ReportRequest(BaseModel):
    data_id: str = Field(
        ..., description="Unique identifier of the dataset to generate a report on"
    )
    analysis_results: dict = Field(
        ..., description="Results of the analysis to include in the report"
    )


class ReportResponse(BaseModel):
    report_html: str = Field(..., description="Generated HTML report as a string")
    error: Optional[str] = Field(None, description="Error message, if any")


# Schema for dataset metadata
class DatasetMetadata(BaseModel):
    data_id: str = Field(..., description="Unique identifier for the dataset")
    column_names: List[str] = Field(
        ..., description="List of column names in the dataset"
    )
    row_count: int = Field(..., description="Number of rows in the dataset")
    description: Optional[str] = Field(
        None, description="Additional description of the dataset"
    )


# Combined schema for multiple endpoints
class APIResponse(BaseModel):
    success: bool = Field(..., description="Indicates if the operation was successful")
    data: Optional[
        Union[
            FileUploadResponse,
            AnalysisResult,
            VisualizationResult,
            ChatResponse,
            ReportResponse,
            DatasetMetadata,
        ]
    ] = Field(None, description="The response data")
    message: Optional[str] = Field(None, description="A user-friendly status message")
