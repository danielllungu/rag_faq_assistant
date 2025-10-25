import json
import logging
import re
from typing import List

from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from src.core.config import config
from src.api.prompts.variant_prompts import get_variant_generation_prompt

logger = logging.getLogger(__name__)


class VariantGenerationService:
    def __init__(self):
        self.config = config

        self.llm = ChatOpenAI(
            model=config.openai.llm_model,
            temperature=0.7,
            api_key=config.openai.api_key,
            max_tokens=300
        )

        self.prompt_template = get_variant_generation_prompt()

        self.chain = self.prompt_template | self.llm | StrOutputParser()

        logger.info("Variant Generation Service initialized")

    def generate_variants(
            self,
            text: str,
            n: int = 3,
            temperature: float = 0.7
    ) -> List[str]:
        if not text or not text.strip():
            logger.warning("Empty text provided for variant generation")
            return []

        n = max(1, min(int(n), 10))

        temperature = max(0.0, min(float(temperature), 1.0))

        try:
            logger.info(f"Generating {n} variants for: {text[:50]}...")

            self.llm.temperature = temperature

            response = self.chain.invoke({
                "text": text,
                "n": n
            })

            variants = self._parse_response(response, n)

            logger.info(f"Successfully generated {len(variants)} variants")
            return variants

        except Exception as e:
            logger.error(f"Failed to generate variants: {e}", exc_info=True)
            return []

    def _parse_response(self, response: str, expected_count: int) -> List[str]:
        """
        Parse the LLM response to extract variants.

        Args:
            response: Raw response string from LLM
            expected_count: Expected number of variants

        Returns:
            List of cleaned, deduplicated variant strings
        """
        variants = []

        try:
            parsed = json.loads(response)

            variants = [str(x) for x in parsed["paraphrases"]]

        except json.JSONDecodeError:
            logger.warning("Response is not valid JSON, trying regex extraction")

            match = re.search(r'\[[\s\S]*?]', response)
            if match:
                try:
                    variants = [str(x) for x in json.loads(match.group(0))]
                except Exception:
                    logger.warning("Could not extract variants from response")

        cleaned_variants = self._clean_variants(variants, expected_count)

        return cleaned_variants

    @staticmethod
    def _clean_variants(variants: List[str], expected_count: int) -> List[str]:
        """
        Clean and deduplicate variant strings.
        """
        seen = set()
        cleaned = []

        for variant in variants:
            variant = re.sub(r'\s+', ' ', variant or '').strip()

            variant = variant.strip('"\'')

            if not variant or variant.lower() in seen:
                continue

            seen.add(variant.lower())
            cleaned.append(variant)

            if len(cleaned) >= expected_count:
                break

        return cleaned


variant_service = VariantGenerationService()
