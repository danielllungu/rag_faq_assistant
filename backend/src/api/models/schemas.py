from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500, description="User's question")
    generate_variants: bool = Field(default=True, description="Whether to generate question variants")
    num_variants: int = Field(default=3, ge=1, le=5, description="Number of variants to generate")


class SimilarMatch(BaseModel):
    faq_id: int = Field(..., description="FAQ ID from database")
    question: str = Field(..., description="Original FAQ question")
    answer: str = Field(..., description="FAQ answer")
    similarity: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0-1)")
    source: str = Field(..., description="Source of match: 'faq' or 'variant'")
    matched_text: Optional[str] = Field(None, description="The variant text that matched (if from variants table)")


class QuestionResponse(BaseModel):
    answer: str = Field(..., description="The answer to the user's question")
    source: str = Field(..., description="Source: 'database' or 'llm'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    matched_faq: Optional[SimilarMatch] = Field(None, description="Best matching FAQ if found")
    all_matches: List[SimilarMatch] = Field(default_factory=list, description="All similar matches found")
    generated_variants: Optional[List[str]] = Field(None, description="Question variants generated")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")


class HealthCheckResponse(BaseModel):
    status: str
    database: str
    timestamp: datetime
