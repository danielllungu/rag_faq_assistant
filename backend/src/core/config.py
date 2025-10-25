import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path)


@dataclass
class DatabaseConfig:
    host: str = 'localhost'
    port: str = '5432'
    database: str = 'faq_db'
    user: str = 'user'
    password: Optional[str] = None

    @classmethod
    def from_env(cls):
        return cls(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('POSTGRES_DB', 'faq_db'),
            user=os.getenv('POSTGRES_USER', 'user'),
            password=os.getenv('POSTGRES_PASSWORD')
        )

    def get_connection_params(self) -> dict:
        """Get connection parameters for psycopg2."""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'user': self.user,
            'password': self.password
        }


@dataclass
class OpenAIConfig:
    api_key: Optional[str] = None
    embedding_model: str = 'text-embedding-3-small'
    embedding_dimensions: int = 1536
    llm_model: str = 'gpt-4o'

    @classmethod
    def from_env(cls):
        return cls(
            api_key=os.getenv('OPENAI_API_KEY'),
            embedding_model=os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small'),
            embedding_dimensions=int(os.getenv('EMBEDDING_DIMENSIONS', '1536')),
            llm_model=os.getenv('LLM_MODEL', 'gpt-4o')
        )

    def validate(self) -> bool:
        return bool(self.api_key)


@dataclass
class AppConfig:
    similarity_threshold: float = 0.75

    @classmethod
    def from_env(cls):
        return cls(
            similarity_threshold=float(os.getenv('CONFIDENCE_THRESHOLD', '0.75'))
        )


class Config:
    def __init__(self):
        self.database = DatabaseConfig.from_env()
        self.openai = OpenAIConfig.from_env()
        self.app = AppConfig.from_env()

    def validate(self) -> tuple[bool, list[str]]:
        errors = []

        if not self.database.password:
            errors.append("Database password not set")

        if not self.openai.validate():
            errors.append("OpenAI API key not set")

        return len(errors) == 0, errors


config = Config()
