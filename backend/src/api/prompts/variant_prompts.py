from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate


VARIANT_GENERATION_SYSTEM_PROMPT = """You are a helpful assistant that rewrites user questions into natural paraphrases.

Your task:
- Generate {n} distinct paraphrases of the user's question
- Preserve the original intent and meaning
- Use different wording and sentence structure
- Keep each paraphrase under 120 characters
- If the input is not a question, rewrite it as a natural question
- Return ONLY a valid JSON object with a "paraphrases" array

Output format:
{{
  "paraphrases": ["paraphrase 1", "paraphrase 2", "paraphrase 3"]
}}

Important:
- No explanations, no additional text
- Just the JSON object
- All paraphrases must be distinct and natural questions"""


VARIANT_GENERATION_USER_TEMPLATE = """Generate {n} distinct paraphrases for the following question:

Question: "{text}"

Remember:
- Keep the same meaning and intent
- Use different wording and structure
- Keep each under 120 characters
- Return only the JSON object with "paraphrases" array"""


def get_variant_generation_prompt() -> ChatPromptTemplate:
    system_message = SystemMessagePromptTemplate.from_template(
        VARIANT_GENERATION_SYSTEM_PROMPT
    )

    human_message = HumanMessagePromptTemplate.from_template(
        VARIANT_GENERATION_USER_TEMPLATE
    )

    return ChatPromptTemplate.from_messages([
        system_message,
        human_message
    ])

