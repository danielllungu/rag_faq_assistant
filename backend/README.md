# FAQ RAG Assistant

A RAG system for FAQ management, built with FastAPI, PostgreSQL with pgvector, and LangChain.

## Overview

The system consists of two main components:

1. **Database Initialization** (`db_init/`) - Sets up and seeds the PostgreSQL database with FAQ data
2. **FastAPI Application** (`src/`) - REST API for RAG-based question answering

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- OpenAI API Key (for embeddings and LLM operations)

Install required Python packages:

```bash
pip install -r requirements.txt
```

## Setup Instructions

### Step 1: Environment Configuration

Create a `.env` file in the **root directory** with the following variables:

```env
OPENAI_API_KEY=<your_openai_api_key>

API_KEYS=key1,key2,key3  # API keys for authenticating requests

POSTGRES_DB=faq_db
POSTGRES_USER=user
POSTGRES_PASSWORD=admin

EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o
EMBEDDING_DIMENSIONS=1536

CONFIDENCE_THRESHOLD=0.75  # Similarity threshold for FAQ matching
```

### Step 2: Start PostgreSQL Database

From the project root directory, start the PostgreSQL database with Docker Compose:

```bash
docker-compose up -d
```

### Step 3: Initialize and Seed Database

Initialize the database schema and extensions:

```bash
python db_init/initialize.py
```

Seed the database with FAQ data and embeddings:

```bash
python -m db_init.scripts.seed_database
```

### Step 4: Run the Application

Build the Docker image:

```bash
docker build -t faq-rag-app -f Dockerfile .
```

Run the containerized application:

```bash
docker run --rm --name faq-app \
  -p 8000:8000 \
  --env-file ./.env \
  -e DB_HOST=host.docker.internal \
  faq-rag-app
```

Once running, the API will be available at `http://localhost:8000`

