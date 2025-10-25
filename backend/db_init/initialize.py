import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

env_path = Path(__file__).parent.parent / '.env'
print(env_path)
load_dotenv(env_path)

EMBEDDING_DIM = os.getenv("EMBEDDING_DIMENSIONS", 1536)


class DatabaseInitializer:
    def __init__(self):
        self.db_name = os.getenv('POSTGRES_DB')
        self.db_user = os.getenv('POSTGRES_USER')
        self.db_password = os.getenv('POSTGRES_PASSWORD')
        self.db_host = 'localhost'
        self.db_port = '5432'

    def get_connection_string(self, database=None):
        db = database or self.db_name
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{db}"

    def connect(self, database=None):
        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=database or self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            return conn
        except psycopg2.Error as e:
            logger.error(f"Error connecting to database: {e}")
            raise

    def create_database_if_not_exists(self):
        try:
            conn = self.connect(database='postgres')
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.db_name,)
            )
            exists = cursor.fetchone()

            if not exists:
                cursor.execute(f'CREATE DATABASE "{self.db_name}"')
                logger.info(f"Database '{self.db_name}' created successfully")
            else:
                logger.info(f"Database '{self.db_name}' already exists")

            cursor.close()
            conn.close()

        except psycopg2.Error as e:
            logger.error(f"Error creating database: {e}")
            raise

    def initialize_extensions(self):
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            conn.commit()

            logger.info("pgvector extension created/verified")

            cursor.close()
            conn.close()

        except psycopg2.Error as e:
            logger.error(f"Error creating extensions: {e}")
            raise

    def create_tables(self):
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("DROP TABLE IF EXISTS faq_variants CASCADE;")
            cursor.execute("DROP TABLE IF EXISTS faqs CASCADE;")

            create_faqs_table_query = f"""
            CREATE TABLE faqs (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                question_embedding vector({EMBEDDING_DIM})
            );
            """
            cursor.execute(create_faqs_table_query)
            logger.info("Table 'faqs' created successfully")

            cursor.execute("""
                CREATE INDEX faqs_question_embedding_idx 
                ON faqs 
                USING ivfflat (question_embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            logger.info("Created similarity search index on faqs.question_embedding")

            create_variants_table_query = f"""
            CREATE TABLE faq_variants (
                id SERIAL PRIMARY KEY,
                faq_id INTEGER NOT NULL REFERENCES faqs(id) ON DELETE CASCADE,
                variant TEXT NOT NULL,
                embedding vector({EMBEDDING_DIM})
            );
            """
            cursor.execute(create_variants_table_query)
            logger.info("Table 'faq_variants' created successfully")

            cursor.execute("""
                CREATE INDEX faq_variants_faq_id_idx
                ON faq_variants(faq_id);
            """)
            logger.info("Created index on faq_variants.faq_id")

            cursor.execute("""
                CREATE INDEX faq_variants_embedding_idx
                ON faq_variants 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            """)
            logger.info("Created similarity search index on faq_variants.embedding")

            conn.commit()

            for table_name in ['faqs', 'faq_variants']:
                cursor.execute("""
                    SELECT column_name, data_type, character_maximum_length
                    FROM information_schema.columns 
                    WHERE table_name = %s
                    ORDER BY ordinal_position;
                """, (table_name,))

                columns = cursor.fetchall()
                logger.info(f"\nTable '{table_name}' structure:")
                for col in columns:
                    logger.info(f"  - {col[0]}: {col[1]}")

            cursor.close()
            conn.close()

        except psycopg2.Error as e:
            logger.error(f"Error creating tables: {e}")
            raise

    def verify_setup(self):
        try:
            conn = self.connect()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 1 
                FROM pg_extension 
                WHERE extname = 'vector';
            """)

            if cursor.fetchone():
                logger.info("pgvector extension is installed")
            else:
                logger.error("pgvector extension is NOT installed")
                return False

            cursor.execute("""
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_name = 'faqs';
            """)

            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM faqs;")
                count = cursor.fetchone()[0]
                logger.info(f"'faqs' table exists (current rows: {count})")
            else:
                logger.error("'faqs' table does NOT exist")
                return False

            cursor.execute("""
                SELECT 1 
                FROM information_schema.tables 
                WHERE table_name = 'faq_variants';
            """)

            if cursor.fetchone():
                cursor.execute("SELECT COUNT(*) FROM faq_variants;")
                count = cursor.fetchone()[0]
                logger.info(f"'faq_variants' table exists (current rows: {count})")
            else:
                logger.error("'faq_variants' table does NOT exist")
                return False

            cursor.execute("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename IN ('faqs', 'faq_variants')
                ORDER BY indexname;
            """)
            indexes = cursor.fetchall()
            logger.info("\nIndexes created:")
            for idx in indexes:
                logger.info(f"  - {idx[0]}")

            cursor.close()
            conn.close()

            return True

        except psycopg2.Error as e:
            logger.error(f"Error verifying setup: {e}")
            return False

    def initialize(self):
        logger.info("Starting database initialization...")
        logger.info(f"Database: {self.db_name}")
        logger.info(f"Host: {self.db_host}:{self.db_port}")
        logger.info(f"Embedding dimensions: {EMBEDDING_DIM}")

        try:
            self.create_database_if_not_exists()
            self.initialize_extensions()
            self.create_tables()

            if self.verify_setup():
                logger.info("\n" + "=" * 50)
                logger.info("Database initialization completed successfully!")
                logger.info("=" * 50)
                return True
            else:
                logger.error("\n" + "=" * 50)
                logger.error("Database initialization verification failed")
                logger.error("=" * 50)
                return False

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False


def main():
    initializer = DatabaseInitializer()

    try:
        logger.info("Testing PostgreSQL connection...")
        conn = initializer.connect(database='postgres')
        conn.close()
        logger.info("PostgreSQL is accessible")
    except psycopg2.OperationalError as e:
        logger.error("Cannot connect to PostgreSQL. Is Docker container running?")
        logger.error("Run: cd preprocessing && docker compose up -d")
        logger.error(f"Error: {e}")
        sys.exit(1)

    success = initializer.initialize()

    if success:
        logger.info("\n" + "=" * 50)
        logger.info("Database is ready for FAQ seeding!")
        logger.info("Next step: Run the seed_database.py script")
        logger.info("=" * 50)
    else:
        logger.error("\n" + "=" * 50)
        logger.error("Database initialization failed!")
        logger.error("Please check the errors above and try again")
        logger.error("=" * 50)
        sys.exit(1)


if __name__ == "__main__":
    main()