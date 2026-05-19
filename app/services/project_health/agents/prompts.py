# ruff: noqa: E501, RUF001 — prompts contain en-dashes and curly quotes that
# are part of the model contract and must not be reformatted. The constant
# blocks below are interpolated into editable templates at runtime; the
# templates themselves live in the database (or in _default_prompts.py if not
# yet seeded).
from __future__ import annotations

import string

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project_health import PHLanguage
from app.services.project_health.prompts.get_prompt_template import get_prompt_template

DOMAIN_LABELS: dict[str, dict[PHLanguage, str]] = {
    "local_leadership": {
        PHLanguage.EN: "Local Leadership & Ownership",
        PHLanguage.PT: "Liderança Local e Apropriação",
        PHLanguage.ES: "Liderazgo Local y Apropiación",
        PHLanguage.FR: "Leadership Local et Appropriation",
        PHLanguage.ID: "Kepemimpinan Lokal dan Kepemilikan",
        PHLanguage.SW: "Uongozi wa Ndani na Umiliki",
    },
    "capacity_training": {
        PHLanguage.EN: "Capacity, Training & Multiplication",
        PHLanguage.PT: "Capacidade, Treinamento e Multiplicação",
        PHLanguage.ES: "Capacidad, Formación y Multiplicación",
        PHLanguage.FR: "Capacité, Formation et Multiplication",
        PHLanguage.ID: "Kapasitas, Pelatihan dan Multiplikasi",
        PHLanguage.SW: "Uwezo, Mafunzo na Kuzidisha",
    },
    "church_community": {
        PHLanguage.EN: "Church & Community Engagement",
        PHLanguage.PT: "Engajamento da Igreja e Comunidade",
        PHLanguage.ES: "Participación de la Iglesia y Comunidad",
        PHLanguage.FR: "Engagement de l'Église et Communauté",
        PHLanguage.ID: "Keterlibatan Gereja dan Komunitas",
        PHLanguage.SW: "Ushiriki wa Kanisa na Jamii",
    },
    "resources_infrastructure": {
        PHLanguage.EN: "Resources & Oral Exegetical Infrastructure",
        PHLanguage.PT: "Recursos e Infraestrutura Exegética Oral",
        PHLanguage.ES: "Recursos e Infraestructura Exegética Oral",
        PHLanguage.FR: "Ressources et Infrastructure Exégétique Orale",
        PHLanguage.ID: "Sumber Daya dan Infrastruktur Eksegesis Oral",
        PHLanguage.SW: "Rasilimali na Miundombinu ya Tafsiri ya Mdomo",
    },
    "strategic_planning": {
        PHLanguage.EN: "Strategic Planning & Risk Management",
        PHLanguage.PT: "Planejamento Estratégico e Gestão de Riscos",
        PHLanguage.ES: "Planificación Estratégica y Gestión de Riesgos",
        PHLanguage.FR: "Planification Stratégique et Gestion des Risques",
        PHLanguage.ID: "Perencanaan Strategis dan Manajemen Risiko",
        PHLanguage.SW: "Mipango ya Kimkakati na Usimamizi wa Hatari",
    },
    "collaboration": {
        PHLanguage.EN: "Collaboration Without Unhealthy Dependency",
        PHLanguage.PT: "Colaboração sem Dependência Prejudicial",
        PHLanguage.ES: "Colaboración sin Dependencia Perjudicial",
        PHLanguage.FR: "Collaboration sans Dépendance Malsaine",
        PHLanguage.ID: "Kolaborasi Tanpa Ketergantungan Tidak Sehat",
        PHLanguage.SW: "Ushirikiano Bila Utegemezi Usiofaa",
    },
    "pace_trajectory": {
        PHLanguage.EN: "Pace & Trajectory (3–5 Year Horizon)",
        PHLanguage.PT: "Ritmo e Trajetória (Horizonte de 3–5 Anos)",
        PHLanguage.ES: "Ritmo y Trayectoria (Horizonte de 3–5 Años)",
        PHLanguage.FR: "Rythme et Trajectoire (Horizon 3–5 Ans)",
        PHLanguage.ID: "Kecepatan dan Lintasan (Horizon 3–5 Tahun)",
        PHLanguage.SW: "Kasi na Mwelekeo (Upeo wa Miaka 3–5)",
    },
}


LANGUAGE_INSTRUCTIONS: dict[PHLanguage, str] = {
    PHLanguage.EN: "Speak in English. Use simple, clear sentences. Avoid jargon.",
    PHLanguage.PT: "Fale em português. Use frases simples e claras. Evite jargão.",
    PHLanguage.ES: "Habla en español. Usa frases simples y claras. Evita jerga.",
    PHLanguage.FR: "Parlez en français. Utilisez des phrases simples et claires. Évitez le jargon.",
    PHLanguage.ID: "Berbicara dalam Bahasa Indonesia. Gunakan kalimat sederhana dan jelas.",
    PHLanguage.SW: "Zungumza kwa Kiswahili. Tumia sentensi rahisi na wazi.",
}


REPORT_LANGUAGE_INSTRUCTIONS: dict[PHLanguage, str] = {
    PHLanguage.EN: "Write in English.",
    PHLanguage.PT: "Escreva em português.",
    PHLanguage.ES: "Escribe en español.",
    PHLanguage.FR: "Écrivez en français.",
    PHLanguage.ID: "Tulis dalam Bahasa Indonesia.",
    PHLanguage.SW: "Andika kwa Kiswahili.",
}


OBT_DOMAIN_GUIDANCE = """
- local_leadership: local leadership, local champions, local decision-making, community accountability, validation processes
- capacity_training: translator training, facilitator training, mentoring, education, multiplication, long-term team growth
- church_community: community desire for Scripture, church support, community ownership, wider participation
- resources_infrastructure: financial and practical resources, oral exegetical resources, bridge-language resources, recording and distribution logistics
- strategic_planning: vision from the beginning, translation brief or plan, cultivation before new starts, sustainability built in from the start, risk planning, advocacy balanced with capacity
- collaboration: connection to other networks, partner relationships, field collaboration, healthy support without unhealthy dependency
- pace_trajectory: 3-5 year progress, All-Access Goal pace, milestones, resilience, ability to continue translation steadily
"""


OBT_INTERNAL_ASSUMPTIONS = """
- Oral Bible Translation is oral by design. Oral preference is not a weakness.
- Do not treat limited literacy, non-use of computers, or non-written workflows as a problem by themselves.
- In OBT, mother-tongue translators and local communities are the protagonists; facilitators come alongside them.
- Strong OBT health usually includes community ownership, local leadership, training, oral exegetical support, realistic pace, and sustainable resourcing.
"""


REQUIRED_OPENING_DETAILS = """
- respondent_name: the full name of the main interviewee or spokesperson
- participants_present: the full name of each person present in the interview, or a clear statement that only one person is present
- language_name: the name of the translation language
- language_code_or_unknown: the language code if they know it, or a clear statement that they do not know it
- team_size: the size of the broader project team
- team_roles: the role or function of each person present, and how the wider team is organized if it is larger than the people in the room
"""


def _domain_list(language: PHLanguage) -> str:
    return "\n".join(f"- {key}: {labels[language]}" for key, labels in DOMAIN_LABELS.items())


async def _render(db: AsyncSession, prompt_key: str, mapping: dict[str, str]) -> str:
    template = await get_prompt_template(db, prompt_key)
    return string.Template(template).safe_substitute(mapping)


async def facilitator_system_prompt(
    db: AsyncSession, language: PHLanguage, coverage_hints: str
) -> str:
    return await _render(
        db,
        "facilitator_system",
        {
            "language_instructions": LANGUAGE_INSTRUCTIONS[language],
            "obt_assumptions": OBT_INTERNAL_ASSUMPTIONS,
            "obt_domain_guidance": OBT_DOMAIN_GUIDANCE,
            "required_opening_details": REQUIRED_OPENING_DETAILS,
            "domain_list": _domain_list(language),
            "coverage_hints": coverage_hints,
        },
    )


async def coverage_planner_prompt(db: AsyncSession, language: PHLanguage) -> str:
    return await _render(
        db,
        "coverage_planner",
        {
            "obt_domain_guidance": OBT_DOMAIN_GUIDANCE,
            "required_opening_details": REQUIRED_OPENING_DETAILS,
            "language": language.value,
        },
    )


async def evidence_mapper_prompt(db: AsyncSession) -> str:
    return await _render(db, "evidence_mapper", {"obt_domain_guidance": OBT_DOMAIN_GUIDANCE})


async def scoring_prompt(db: AsyncSession) -> str:
    return await _render(db, "scoring", {"obt_domain_guidance": OBT_DOMAIN_GUIDANCE})


async def interview_context_prompt(db: AsyncSession) -> str:
    return await _render(db, "interview_context", {})


async def team_report_prompt(db: AsyncSession, language: PHLanguage) -> str:
    return await _render(
        db,
        "team_report",
        {"report_language_instructions": REPORT_LANGUAGE_INSTRUCTIONS[language]},
    )


async def admin_report_prompt(db: AsyncSession) -> str:
    return await _render(db, "admin_report", {})


async def guardrail_prompt(db: AsyncSession) -> str:
    return await _render(db, "guardrail", {})
