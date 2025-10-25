import sys
import logging
from pathlib import Path
from typing import List, Tuple, Dict
from src.core.database import db_manager
from src.core.embeddings import embedding_service
from db_init.scripts.llm import llm_service
from src.core.config import config
from db_init.data.faq_data import get_all_faqs

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FAQSeeder:
    def __init__(self):
        self.db = db_manager
        self.embeddings = embedding_service
        self.faqs = get_all_faqs()
        self.llm_service = llm_service
        self.variants_per_question = 3

    def clear_existing_data(self):
        try:
            self.db.execute_update("TRUNCATE TABLE faqs RESTART IDENTITY CASCADE;")
            logger.info("Existing FAQ data cleared (including variants)")
        except Exception as e:
            logger.error(f"Failed to clear existing data: {e}")
            raise

    def prepare_faq_data(self) -> List[Tuple]:
        values = []
        total = len(self.faqs)

        logger.info(f"Generating embeddings for {total} FAQs...")

        for idx, faq in enumerate(self.faqs, 1):
            try:
                embedding = self.embeddings.generate_embedding(faq["question"])
                embedding_vector = self.embeddings.embedding_to_vector(embedding)

                values.append((
                    faq["question"],
                    faq["answer"],
                    embedding_vector.tolist()
                ))

                logger.info(f"  [{idx}/{total}] {faq['question'][:50]}...")

            except Exception as e:
                logger.error(f"  [{idx}/{total}] Failed: {e}")
                raise

        return values

    def insert_faqs(self, values: List[Tuple]) -> List[Dict]:
        query = """
            INSERT INTO faqs (question, answer, question_embedding)
            VALUES %s
            RETURNING id, question
        """

        try:
            inserted_records = self.db.execute_query_with_batch(
                query=query,
                values=values,
                template="(%s, %s, %s::vector)"
            )

            logger.info(f"Inserted {len(inserted_records)} FAQ records")

            result = [{"id": row[0], "question": row[1]} for row in inserted_records]
            return result

        except Exception as e:
            logger.error(f"Failed to insert FAQs: {e}")
            raise

    def generate_and_insert_variants(self, faq_records: List[Dict]):
        total_faqs = len(faq_records)
        total_variants_inserted = 0

        logger.info(f"\nGenerating {self.variants_per_question} variants per FAQ...")

        for idx, faq_record in enumerate(faq_records, 1):
            faq_id = faq_record["id"]
            original_question = faq_record["question"]

            try:
                logger.info(f"\n  [{idx}/{total_faqs}] Processing: {original_question[:60]}...")

                variants = self.llm_service.generate_paraphrases(
                    text=original_question,
                    n=self.variants_per_question,
                    temperature=0.7
                )

                if not variants:
                    logger.warning(f"    No variants generated for FAQ ID {faq_id}")
                    continue

                logger.info(f"    Generated {len(variants)} variants")

                variant_values = []
                for var_idx, variant_text in enumerate(variants, 1):
                    try:
                        variant_embedding = self.embeddings.generate_embedding(variant_text)
                        variant_embedding_vector = self.embeddings.embedding_to_vector(variant_embedding)

                        variant_values.append((
                            faq_id,
                            variant_text,
                            variant_embedding_vector.tolist()
                        ))

                        logger.info(f"{var_idx}. {variant_text[:50]}...")

                    except Exception as e:
                        logger.error(f"      Failed to embed variant {var_idx}: {e}")
                        continue

                if variant_values:
                    inserted_count = self._insert_variants_batch(variant_values)
                    total_variants_inserted += inserted_count
                    logger.info(f"    Inserted {inserted_count} variants for FAQ ID {faq_id}")

            except Exception as e:
                logger.error(f"  [{idx}/{total_faqs}] Failed to process FAQ ID {faq_id}: {e}")
                continue

        logger.info(f"\nTotal variants inserted: {total_variants_inserted}")
        return total_variants_inserted

    def _insert_variants_batch(self, variant_values: List[Tuple]):
        query = """
            INSERT INTO faq_variants (faq_id, variant, embedding)
            VALUES %s
        """

        try:
            count = self.db.batch_insert(
                query=query,
                values=variant_values,
                template="(%s, %s, %s::vector)"
            )
            return count
        except Exception as e:
            logger.error(f"Failed to insert variant batch: {e}")
            raise

    def verify_seeding(self):
        try:
            total_faqs = self.db.get_table_count('faqs')
            logger.info(f"\nTotal FAQs in database: {total_faqs}")

            total_variants = self.db.get_table_count('faq_variants')
            logger.info(f"Total variants in database: {total_variants}")

            if total_faqs > 0:
                avg_variants = total_variants / total_faqs
                logger.info(f" Average variants per FAQ: {avg_variants:.2f}")

            sample_query = """
                SELECT id, question, 
                       substring(answer, 1, 50) as answer_preview,
                       vector_dims(question_embedding) as embedding_dims
                FROM faqs 
                LIMIT 3;
            """

            samples = self.db.execute_query(sample_query)

            if samples:
                logger.info("\n Sample FAQs:")
                for row in samples:
                    logger.info(f"  • ID: {row[0]}")
                    logger.info(f"    Q: {row[1][:60]}...")
                    logger.info(f"    A: {row[2]}...")
                    logger.info(f"    Embedding dims: {row[3]}")

                    variant_query = """
                        SELECT variant, vector_dims(embedding) as embedding_dims
                        FROM faq_variants
                        WHERE faq_id = %s
                    """
                    variants = self.db.execute_query(variant_query, (row[0],))
                    if variants:
                        logger.info(f"    Variants ({len(variants)}):")
                        for v in variants:
                            logger.info(f"      - {v[0][:60]}... (dims: {v[1]})")

        except Exception as e:
            logger.error(f"Verification failed: {e}")

    def test_similarity_search(self):
        test_query = "How can I change my password?"

        try:
            logger.info(f"\nTesting similarity search...")
            logger.info(f"   Query: '{test_query}'")

            query_embedding = self.embeddings.generate_embedding(test_query)

            logger.info("\nSearching in FAQs table:")
            faq_search_query = """
                SELECT question, answer,
                       1 - (question_embedding <=> %s::vector) as similarity
                FROM faqs
                ORDER BY question_embedding <=> %s::vector
                LIMIT 3;
            """

            faq_results = self.db.execute_query(
                faq_search_query,
                (query_embedding, query_embedding)
            )

            if faq_results:
                for idx, row in enumerate(faq_results, 1):
                    logger.info(f"\n  {idx}. Similarity: {row[2]:.4f}")
                    logger.info(f"     Q: {row[0][:80]}...")
                    logger.info(f"     A: {row[1][:80]}...")

            logger.info("\nSearching in FAQ Variants table:")
            variant_search_query = """
                SELECT fv.variant, f.question, f.answer,
                       1 - (fv.embedding <=> %s::vector) as similarity
                FROM faq_variants fv
                JOIN faqs f ON f.id = fv.faq_id
                ORDER BY fv.embedding <=> %s::vector
                LIMIT 3;
            """

            variant_results = self.db.execute_query(
                variant_search_query,
                (query_embedding, query_embedding)
            )

            if variant_results:
                for idx, row in enumerate(variant_results, 1):
                    logger.info(f"\n  {idx}. Similarity: {row[3]:.4f}")
                    logger.info(f"     Variant: {row[0][:80]}...")
                    logger.info(f"     Original Q: {row[1][:80]}...")
                    logger.info(f"     A: {row[2][:80]}...")

        except Exception as e:
            logger.error(f"Similarity search test failed: {e}")

    def seed(self, clear_existing: bool = False):
        try:
            valid, errors = config.validate()
            if not valid:
                logger.error("Configuration errors:")
                for error in errors:
                    logger.error(f"   • {error}")
                return

            self.db.initialize_pool()

            if not self.db.table_exists('faqs'):
                logger.error("Table 'faqs' does not exist. Run initialization script first.")
                return

            if not self.db.table_exists('faq_variants'):
                logger.error("Table 'faq_variants' does not exist. Run initialization script first.")
                return

            if clear_existing:
                self.clear_existing_data()

            logger.info("\n" + "=" * 60)
            logger.info("STEP 1: Inserting FAQs")
            logger.info("=" * 60)
            values = self.prepare_faq_data()
            faq_records = self.insert_faqs(values)

            logger.info("\n" + "=" * 60)
            logger.info("STEP 2: Generating and Inserting Variants")
            logger.info("=" * 60)
            self.generate_and_insert_variants(faq_records)

            logger.info("\n" + "=" * 60)
            logger.info("STEP 3: Verification")
            logger.info("=" * 60)
            self.verify_seeding()

            logger.info("\n" + "=" * 60)
            logger.info("STEP 4: Testing Similarity Search")
            logger.info("=" * 60)
            self.test_similarity_search()

            logger.info("\n" + "=" * 60)
            logger.info("FAQ database seeding completed successfully!")
            logger.info("Your semantic FAQ system with variants is ready to use!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"\nSeeding failed: {e}")
            raise
        finally:
            self.db.close_pool()


def main():
    seeder = FAQSeeder()
    seeder.seed(clear_existing=True)


if __name__ == "__main__":
    main()