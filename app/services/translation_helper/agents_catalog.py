from typing import TypedDict

from app.db.models.translation_helper import AgentId


class AgentCatalogEntry(TypedDict):
    icon: str
    short: str
    starters: list[str]


AGENT_CATALOG: dict[AgentId, AgentCatalogEntry] = {
    AgentId.STORYTELLER: {
        "icon": "book-open",
        "short": "A story to illuminate the concept",
        "starters": [
            "Tell me the story of the Good Samaritan",
            "Story of Joseph for an oral audience",
            "How would you tell the Prodigal Son?",
        ],
    },
    AgentId.CONVERSATION: {
        "icon": "messages-square",
        "short": "Talk through it in plain dialogue",
        "starters": [
            'What does "grace" mean in Ephesians 2?',
            "Help me understand the parable of the sower",
            "Walk me through Paul's argument in Romans 8",
        ],
    },
    AgentId.ORAL: {
        "icon": "mic-vocal",
        "short": "Say it in clear, natural oral language",
        "starters": [
            "Say Matthew 5:1-12 in clear spoken language",
            "Read John 3:16 the way an elder would say it",
            "Speak Psalm 23 as comfort",
        ],
    },
    AgentId.HEALTH: {
        "icon": "activity",
        "short": "Guided quarterly project review",
        "starters": [
            "Start a quarterly health check",
            "Where are we losing momentum?",
            "Review our last consultant check",
        ],
    },
    AgentId.BACKTRANS: {
        "icon": "git-compare",
        "short": "Compare back-translation against source",
        "starters": [
            "Check this back-translation of John 3:16",
            "Compare Tikuna draft of Genesis 1",
            "Find places I drifted from the source",
        ],
    },
}


def get_catalog_entry(agent_id: AgentId) -> AgentCatalogEntry:
    return AGENT_CATALOG[agent_id]
