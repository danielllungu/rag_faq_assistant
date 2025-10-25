import logging
from fastapi import APIRouter, HTTPException, status, Depends

from src.api.models.schemas import QuestionRequest, QuestionResponse
from src.api.services.qa_service import qa_service
from src.api.services.auth import api_key_auth

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/faq",
    tags=["FAQ"],
    dependencies=[Depends(api_key_auth)]
)


@router.post(
    "/ask",
    response_model=QuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question (Protected)",
    description="Submit a question and get an answer. Requires API Key authentication."
)
async def ask_question(request: QuestionRequest) -> QuestionResponse:
    """
    Authentication Required:
    - `X-API-Key` header with API key

    Parameters:
    - question: Your question (required)
    - generate_variants: Whether to generate question variants (default: true)
    - num_variants: Number of variants to generate 1-5 (default: 3)

    Returns:
    - answer: The answer to your question
    - source: Where the answer came from ('database' or 'llm')
    - confidence: Confidence score (0-1)
    - matched_faq: Best matching FAQ if found
    - all_matches: All similar FAQs found
    - generated_variants: Question variants generated (if enabled)
    - processing_time_ms: Time taken to process the request
    """
    try:
        logger.info(f"Received question: {request.question}")

        response = qa_service.answer_question(
            user_question=request.question,
            generate_variants=request.generate_variants,
            num_variants=request.num_variants
        )

        logger.info(
            f"Question answered: source={response.source}, "
            f"confidence={response.confidence:.4f}, "
            f"time={response.processing_time_ms:.2f}ms"
        )

        return response

    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process question: {str(e)}"
        )


@router.get(
    "/search",
    response_model=QuestionResponse,
    summary="Search FAQs (Protected)",
    description="Search for similar FAQs. **Requires API Key authentication.**"
)
async def search_faqs(
        q: str,
        generate_variants: bool = True,
        num_variants: int = 3
) -> QuestionResponse:
    """
    Search for similar FAQs using a GET request.

    Authentication Required:
    - Include `X-API-Key` header with your API key

    Query Parameters:
    - q: Search query (required)
    - generate_variants: Whether to generate variants (default: true)
    - num_variants: Number of variants (default: 3)
    """
    if not q or not q.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'q' is required and cannot be empty"
        )

    try:
        response = qa_service.answer_question(
            user_question=q,
            generate_variants=generate_variants,
            num_variants=num_variants
        )
        return response

    except Exception as e:
        logger.error(f"Error searching FAQs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search FAQs: {str(e)}"
        )
