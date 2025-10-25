import logging
from typing import List
import numpy as np
from openai import OpenAI
from src.core.config import config

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self):
        self.config = config.openai
        if not self.config.validate():
            raise ValueError("OpenAI API key not configured")

        self.client = OpenAI(api_key=self.config.api_key)
        self.model = self.config.embedding_model
        self.dimensions = self.config.embedding_dimensions

    def generate_embedding(self, text: str) -> List[float]:
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding for text: {e}")
            raise

    @staticmethod
    def embedding_to_vector(embedding: List[float]) -> np.ndarray:
        return np.array(embedding, dtype=np.float32)


embedding_service = EmbeddingService()
