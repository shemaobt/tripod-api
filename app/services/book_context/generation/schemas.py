from pydantic import BaseModel, Field


class VerseRefSchema(BaseModel):
    chapter: int
    verse: int


class ChapterOutline(BaseModel):
    chapter: int
    title: str
    summary: str
    key_events: list[str] = Field(default_factory=list)


class StructuralOutlineSchema(BaseModel):
    book_arc: str
    chapters: list[ChapterOutline] = Field(default_factory=list)
    literary_structure: str = ""


class ArcEntrySchema(BaseModel):
    at: VerseRefSchema
    state: str


class ParticipantSchema(BaseModel):
    name: str
    english_gloss: str = ""
    entity_type: str = "person"
    type: str = "named"
    entry_verse: VerseRefSchema
    exit_verse: VerseRefSchema | None = None
    appears_in: list[VerseRefSchema] = Field(default_factory=list)
    appearance_count: int = 0
    role_in_book: str = ""
    relationships: list[str] = Field(default_factory=list)
    what_audience_knows_at_entry: str = ""
    arc: list[ArcEntrySchema] = Field(default_factory=list)
    status_at_end: str = ""


class ParticipantRegisterSchema(BaseModel):
    participants: list[ParticipantSchema] = Field(default_factory=list)


class EpisodeStatusSchema(BaseModel):
    at: VerseRefSchema
    status: str


class DiscourseThreadSchema(BaseModel):
    label: str
    opened_at: VerseRefSchema
    resolved_at: VerseRefSchema | None = None
    question: str
    status_by_episode: list[EpisodeStatusSchema] = Field(default_factory=list)


class DiscourseThreadsSchema(BaseModel):
    threads: list[DiscourseThreadSchema] = Field(default_factory=list)


class PlaceSchema(BaseModel):
    name: str
    english_gloss: str = ""
    entity_type: str = "place"
    first_appears: VerseRefSchema
    type: str = ""
    meaning_and_function: str = ""
    appears_in: list[VerseRefSchema] = Field(default_factory=list)
    appearance_count: int = 0


class ObjectSchema(BaseModel):
    name: str
    first_appears: VerseRefSchema
    what_it_is: str = ""
    meaning_across_scenes: str = ""
    appears_in: list[VerseRefSchema] = Field(default_factory=list)


class InstitutionSchema(BaseModel):
    name: str
    first_invoked: VerseRefSchema
    what_it_is: str = ""
    role_in_book: str = ""
    appears_in: list[VerseRefSchema] = Field(default_factory=list)


class GenreContextSchema(BaseModel):
    primary_genre: str = ""
    sub_genres: list[str] = Field(default_factory=list)
    narrative_voice: str = ""
    temporal_setting: str = ""
    audience_positioning: str = ""


class MaintenanceNotesSchema(BaseModel):
    generation_notes: str = ""
    known_limitations: list[str] = Field(default_factory=list)


class ContextSectionsSchema(BaseModel):
    theological_spine: str = ""
    places: list[PlaceSchema] = Field(default_factory=list)
    objects: list[ObjectSchema] = Field(default_factory=list)
    institutions: list[InstitutionSchema] = Field(default_factory=list)
    genre_context: GenreContextSchema = Field(default_factory=GenreContextSchema)
    maintenance_notes: MaintenanceNotesSchema = Field(default_factory=MaintenanceNotesSchema)
