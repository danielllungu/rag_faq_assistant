import logging
import time
from typing import List, Dict
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from src.api.prompts.ai_router_prompts import get_router_prompt
from src.core.config import config
from src.api.services.retrieval_service import retrieval_service
from src.api.services.variant_service import variant_service
from src.api.prompts.qa_prompts import get_rag_prompt, get_general_prompt
from src.api.models.schemas import QuestionResponse, SimilarMatch

logger = logging.getLogger(__name__)


class QuestionAnsweringService:
    def __init__(self):
        self.retrieval_service = retrieval_service
        self.variant_service = variant_service
        self.config = config

        self.llm = ChatOpenAI(
            model=config.openai.llm_model,
            temperature=0.7,
            api_key=config.openai.api_key
        )

        self.rag_prompt = get_rag_prompt()
        self.general_prompt = get_general_prompt()

        self.router_prompt = get_router_prompt()
        self.llm_router = self.router_prompt | self.llm | StrOutputParser()

        self.rag_chain = self.rag_prompt | self.llm | StrOutputParser()
        self.general_chain = self.general_prompt | self.llm | StrOutputParser()

        self.confidence_threshold = float(
            getattr(config.app, 'confidence_threshold', 0.75)
        )

        self.default_general_answer = "This is not really what I was trained for, therefore I cannot answer. Try again."

        logger.info(f"QA Service initialized with confidence threshold: {self.confidence_threshold}")
        logger.info("Using LangChain for all LLM operations")

    def answer_question(
            self,
            user_question: str,
            generate_variants: bool = True,
            num_variants: int = 3
    ) -> QuestionResponse:
        """
        Main method to answer user questions with hybrid RAG.

        Workflow:
        1. Generate question variants using LangChain (via variant_service)
        2. Create embeddings for original + variants
        3. Search database for similar FAQs
        4. If confidence >= threshold: return DB answer
        5. If confidence < threshold: generate answer with LangChain

        Args:
            user_question: The user's question
            generate_variants: Whether to generate question variants
            num_variants: Number of variants to generate

        Returns:
            QuestionResponse with answer, confidence, and metadata
        """
        start_time = time.time()

        try:
            question_category = self.llm_router.invoke({
                "question": user_question
            })

            if "general" in question_category.lower():
                processing_time = (time.time() - start_time) * 1000

                response = QuestionResponse(
                    answer=self.default_general_answer,
                    source="llm",
                    confidence=1.0,
                    matched_faq=None,
                    all_matches=[],
                    generated_variants=None,
                    processing_time_ms=round(processing_time, 2)
                )

                logger.info(f"Question answered in {processing_time:.2f}ms")
                return response

            variants = []
            if generate_variants:
                logger.info(f"Generating {num_variants} variants for: {user_question}")
                variants = self.variant_service.generate_variants(
                    text=user_question,
                    n=num_variants,
                    temperature=0.7
                )
                logger.info(f"Generated variants: {variants}")

            logger.info("Searching for similar FAQs...")
            matches, embeddings = self.retrieval_service.search_with_metadata(
                user_query=user_question,
                query_variants=variants,
                top_k=5
            )

            best_match = matches[0] if matches else None
            confidence = best_match['similarity'] if best_match else 0.0

            logger.info(f"Best match confidence: {confidence:.4f} (threshold: {self.confidence_threshold})")

            if confidence >= self.confidence_threshold and best_match:
                answer = best_match['answer']
                source = 'database'
                logger.info("Using database answer (confidence above threshold)")
            else:
                logger.info("✗ Confidence below threshold, generating LLM answer")
                answer = self._generate_llm_answer(user_question, matches)
                source = 'llm'

            processing_time = (time.time() - start_time) * 1000

            response = QuestionResponse(
                answer=answer,
                source=source,
                confidence=confidence,
                matched_faq=self._build_similar_match(best_match) if best_match else None,
                all_matches=[self._build_similar_match(m) for m in matches],
                generated_variants=variants if generate_variants else None,
                processing_time_ms=round(processing_time, 2)
            )

            logger.info(f"Question answered in {processing_time:.2f}ms")
            return response

        except Exception as e:
            logger.error(f"Error answering question: {e}", exc_info=True)
            processing_time = (time.time() - start_time) * 1000
            return QuestionResponse(
                answer="I apologize, but I encountered an error processing your question. Please try again.",
                source='error',
                confidence=0.0,
                matched_faq=None,
                all_matches=[],
                generated_variants=None,
                processing_time_ms=round(processing_time, 2)
            )

    def _generate_llm_answer(
            self,
            user_question: str,
            context_matches: List[Dict]
    ) -> str:
        try:
            context_faqs = [
                m for m in context_matches
                if m['similarity'] >= 0.5
            ][:3]

            if context_faqs:
                logger.info(f"Using RAG mode with {len(context_faqs)} context FAQs")
                context_text = self._build_context(context_faqs)

                answer = self.rag_chain.invoke({
                    "context": context_text,
                    "question": user_question
                })
            else:
                logger.info("Using general assistant mode (no relevant context)")

                answer = self.general_chain.invoke({
                    "question": user_question
                })

            answer = answer.strip()
            logger.info("LLM answer generated successfully")
            return answer

        except Exception as e:
            logger.error(f"Failed to generate LLM answer: {e}", exc_info=True)
            return "I apologize, but I'm unable to generate an answer at this time. Please try rephrasing your question or contact support."

    @staticmethod
    def _build_context(matches: List[Dict]) -> str:
        context_parts = []
        for i, match in enumerate(matches, 1):
            context_parts.append(
                f"FAQ {i}:\n"
                f"Q: {match['question']}\n"
                f"A: {match['answer']}\n"
            )
        return "\n".join(context_parts)

    @staticmethod
    def _build_similar_match(match: Dict) -> SimilarMatch:
        return SimilarMatch(
            faq_id=match['faq_id'],
            question=match['question'],
            answer=match['answer'],
            similarity=match['similarity'],
            source=match['source'],
            matched_text=match.get('matched_text')
        )


qa_service = QuestionAnsweringService()
