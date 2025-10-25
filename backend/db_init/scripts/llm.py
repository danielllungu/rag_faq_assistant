import json
import logging
import re
from typing import List, Optional
from openai import OpenAI, APIError, RateLimitError, APITimeoutError
from src.core.config import config

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.cfg = config.openai
        if not getattr(self.cfg, "validate", None) or not self.cfg.validate():
            raise ValueError("OpenAI API key / config not set")

        self.client = OpenAI(api_key=self.cfg.api_key)
        self.model: str = self.cfg.llm_model

        self.default_temperature: float = 0.7
        self.default_max_tokens: int = 300
        self.default_seed: Optional[int] = None

    def generate_paraphrases(
        self,
        text: str,
        n: int = 3,
        temperature: Optional[float] = None,
        seed: Optional[int] = None,
        max_tokens: Optional[int] = None,
    ) -> List[str]:
        if not text or not text.strip():
            return []

        n = max(1, min(int(n), 10))
        temperature = self.default_temperature if temperature is None else float(temperature)
        max_tokens = self.default_max_tokens if max_tokens is None else int(max_tokens)
        seed = self.default_seed if seed is None else seed

        system_msg = (
            "You are a helpful assistant that rewrites user questions/queries.\n"
            "You must only return a JSON array of distinct, natural paraphrases "
            "that preserve the original intent. No explanations."
        )

        user_msg = (
            f"Rewrite the following user query into {n} distinct paraphrases that keep the same intent. "
            "Use different wording and structure. Keep each under 120 characters. In case the user's query is not a question, rewrite it as a natural question. "
            "Return ONLY a JSON array of strings.\n\n"
            "JSON output format example:\n"
            "{ \"paraphrases\": [\"<paraphrase 1>\", \"<paraphrase 2>\", \"<paraphrase 3>\"] }\n\n"
            f"The user query is: \"{text}\"\n"
        )

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                seed=seed
            )
        except (APIError, RateLimitError, APITimeoutError) as e:
            logger.error(f"LLM paraphrase call failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected LLM error: {e}")
            raise

        raw = resp.choices[0].message.content if resp.choices else "[]"

        paraphrases: List[str] = []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "paraphrases" in parsed and isinstance(parsed["paraphrases"], list):
                paraphrases = [str(x) for x in parsed["paraphrases"]]
            elif isinstance(parsed, list):
                paraphrases = [str(x) for x in parsed]
            else:
                array_like = parsed.get("data") if isinstance(parsed, dict) else None
                if isinstance(array_like, list):
                    paraphrases = [str(x) for x in array_like]
        except Exception:
            logger.warning("Could not parse model output as JSON array.")
            paraphrases = []

        seen = set()
        cleaned: List[str] = []
        for p in paraphrases:
            p = re.sub(r"\s+", " ", p or "").strip()
            if p and p.lower() not in seen:
                seen.add(p.lower())
                cleaned.append(p)

        if len(cleaned) > n:
            cleaned = cleaned[:n]

        return cleaned


llm_service = LLMService()
