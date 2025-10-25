from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate


ROUTER_SYSTEM_PROMPT = """You are a routing classifier for incoming user's questions.
Your task: Decide whether the question is IT related (includes Support IT, platform usage support) Chat, or General.

Definitions
- IT: Anything about computers, software, programming, platform usages, login/logout/create account procedures, 
credentials, profile details, web platform operations, support for troubleshooting. 
- Chat: greetings, small talk.
- General: Everything else (HR, legal, finance, travel, cooking, health, philosophy, literature, general math, etc.).

Rules:
1. Output **exactly one word**: 'IT', 'Chat', or 'General' (no punctuation, quotes, or explanations).
2. If any substantial part of the question is IT/support/tech-tool related, output 'IT'.
3. If the question is a greeting or small talk, output 'Chat'.
3. If the question is clearly non-IT related nor Chat, output 'General'.
"""

ROUTER_USER_TEMPLATE = """
Carefully analyze the provided user's question and determine if it is IT related (including Support IT), Chat (chit-chat, greetings) or General (anything else).
If the question is IT or Support IT related, route it to the "IT" category.
If the question is a greeting or small talk, route it to the "Chat" category.
Otherwise, route it to the "General" category.

User question: {question}

Output "IT", "Chat", or "General" only.
"""


def get_router_prompt() -> ChatPromptTemplate:
    system_message = SystemMessagePromptTemplate.from_template(ROUTER_SYSTEM_PROMPT)
    human_message = HumanMessagePromptTemplate.from_template(ROUTER_USER_TEMPLATE)

    return ChatPromptTemplate.from_messages([
        system_message,
        human_message
    ])


