import logging
from typing import List, Dict, Tuple
import numpy as np
from src.core.database import db_manager
from src.core.embeddings import embedding_service

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self):
        self.db = db_manager
        self.embeddings = embedding_service

    def search_similar_faqs(
            self,
            query_embeddings: List[np.ndarray],
            top_k: int = 5
    ) -> List[Dict]:
        """
        Search for similar FAQs using multiple query embeddings.
        Searches both faqs and faq_variants tables.

        Args:
            query_embeddings: List of embedding vectors to search with
            top_k: Number of top results to return per query

        Returns:
            List of dictionaries with match information, deduplicated and sorted by similarity
        """
        all_matches = []

        for embedding in query_embeddings:
            faq_matches = self._search_faqs_table(embedding, top_k)
            all_matches.extend(faq_matches)

            variant_matches = self._search_variants_table(embedding, top_k)
            all_matches.extend(variant_matches)

        deduplicated = self._deduplicate_matches(all_matches)

        deduplicated.sort(key=lambda x: x['similarity'], reverse=True)

        return deduplicated[:top_k]

    def _search_faqs_table(self, embedding: np.ndarray, top_k: int) -> List[Dict]:
        """Search in the main faqs table."""
        query = """
            SELECT 
                id,
                question,
                answer,
                1 - (question_embedding <=> %s::vector) as similarity
            FROM faqs
            ORDER BY question_embedding <=> %s::vector
            LIMIT %s;
        """

        try:
            embedding_list = embedding.tolist()
            results = self.db.execute_query(
                query,
                (embedding_list, embedding_list, top_k)
            )

            matches = []
            for row in results:
                matches.append({
                    'faq_id': row[0],
                    'question': row[1],
                    'answer': row[2],
                    'similarity': float(row[3]),
                    'source': 'faq',
                    'matched_text': None
                })

            return matches

        except Exception as e:
            logger.error(f"Error searching faqs table: {e}")
            return []

    def _search_variants_table(self, embedding: np.ndarray, top_k: int) -> List[Dict]:
        """Search in the faq_variants table and join with faqs."""
        query = """
            SELECT 
                f.id,
                f.question,
                f.answer,
                fv.variant,
                1 - (fv.embedding <=> %s::vector) as similarity
            FROM faq_variants fv
            JOIN faqs f ON f.id = fv.faq_id
            ORDER BY fv.embedding <=> %s::vector
            LIMIT %s;
        """

        try:
            embedding_list = embedding.tolist()
            results = self.db.execute_query(
                query,
                (embedding_list, embedding_list, top_k)
            )

            matches = []
            for row in results:
                matches.append({
                    'faq_id': row[0],
                    'question': row[1],
                    'answer': row[2],
                    'similarity': float(row[4]),
                    'source': 'variant',
                    'matched_text': row[3]
                })

            return matches

        except Exception as e:
            logger.error(f"Error searching faq_variants table: {e}")
            return []

    @staticmethod
    def _deduplicate_matches(matches: List[Dict]) -> List[Dict]:
        """
        Deduplicate matches by faq_id, keeping the one with highest similarity.
        """
        faq_map = {}

        for match in matches:
            faq_id = match['faq_id']

            if faq_id not in faq_map or match['similarity'] > faq_map[faq_id]['similarity']:
                faq_map[faq_id] = match

        return list(faq_map.values())

    def search_with_metadata(
            self,
            user_query: str,
            query_variants: List[str],
            top_k: int = 5
    ) -> Tuple[List[Dict], List[np.ndarray]]:
        """
        Perform search with full metadata.

        Args:
            user_query: Original user question
            query_variants: Generated question variants
            top_k: Number of results to return

        Returns:
            Tuple of (matches, embeddings)
        """
        all_queries = [user_query] + query_variants

        embeddings = []
        for query in all_queries:
            embedding = self.embeddings.generate_embedding(query)
            embedding_vector = self.embeddings.embedding_to_vector(embedding)
            embeddings.append(embedding_vector)

        matches = self.search_similar_faqs(embeddings, top_k=top_k)

        return matches, embeddings


retrieval_service = RetrievalService()
