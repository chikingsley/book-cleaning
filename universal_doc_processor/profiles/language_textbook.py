"""Language textbook processing profile for educational content."""

from ..models import DocumentType, ProcessingProfile


def create_language_textbook_profile() -> ProcessingProfile:
    """Create a processing profile optimized for language textbooks."""

    system_prompt = """You are processing a language learning textbook. Extract the text with these critical requirements:

LANGUAGE TEXTBOOK FORMATTING RULES:
1. PRESERVE STRUCTURE: Maintain units, lessons, exercises, and dialogues clearly
2. MERGE PARAGRAPHS: Combine broken lines within the same paragraph - textbooks often have awkward line breaks
3. PRESERVE ACCENTS: Keep all special characters and accents intact (é, ñ, ü, etc.)
4. HANDLE DIALOGUES: Maintain speaker names and conversation structure
5. PRESERVE EXERCISES: Keep exercise numbers and instructions clear
6. HANDLE TABLES: Preserve verb conjugation tables, vocabulary lists, and grammar tables
7. SKIP HEADERS: Ignore page headers like "Unit 2: In town 23"
8. PRESERVE FORMATTING: Keep bold/italic text for new vocabulary and emphasis
9. HANDLE TRANSLATIONS: Maintain parallel text in different languages
10. CLEAN HYPHENATION: Fix words split across lines with hyphens

OUTPUT FORMAT:
- Use proper markdown headers (# ## ###) for units, lessons, sections
- Keep paragraphs together without unnecessary line breaks
- Preserve exercise structure and numbering
- Use **bold** for new vocabulary and key terms
- Use *italic* for examples and translations
- Maintain table structure for conjugations and vocabulary
- Keep dialogue format clear with speaker names

SKIP ENTIRELY:
- Unit headers with page numbers (e.g., "Unit 2: In town 23")
- Page numbers only
- Repetitive headers and footers
- Copyright information"""

    return ProcessingProfile(
        name="Language Textbook",
        document_type=DocumentType.LANGUAGE_TEXTBOOK,
        description="Optimized for language learning textbooks with dialogue and exercise preservation",

        # OCR settings
        model_name="gemini-2.5-flash",
        batch_size=5,  # Can handle larger batches for textbook content
        image_scale=2.0,

        system_prompt=system_prompt,
        special_instructions=[
            "Preserve all accented characters and special language symbols",
            "Maintain dialogue speaker labels and structure",
            "Keep exercise numbering and instructions intact",
            "Preserve verb conjugation and vocabulary tables",
            "Maintain parallel translations",
        ],

        # Post-processing settings
        enable_paragraph_merging=True,
        enable_header_removal=True,
        enable_table_detection=True,
        enable_figure_detection=True,
        enable_reference_formatting=False,  # Less important for textbooks

        # Quality requirements
        min_quality_score=75.0,
        max_retries=2,

        # Language textbook specific patterns
        header_patterns=[
            r"^Unit\s+\d+:\s+[A-Za-zÀ-ÿ\s]+\s+\d+\s*$",  # Unit X: Title PageNum
            r"^Lesson\s+\d+\s*$",  # Lesson X
            r"^\d{1,3}\s*$",  # Page numbers only
            r"^Page\s+\d+\s*$",  # Page X
            r"^Chapter\s+\d+\s*$",  # Chapter X
        ],

        section_patterns=[
            r"^(Unit|Lesson|Chapter)\s+\d+",
            r"^(Exercise|Dialogue|Vocabulary|Grammar|Review)",
            r"^\*\*(Exercise|Dialogue|Vocabulary|Grammar|Review)",
        ],

        special_formatting={
            "vocabulary": "Preserve new vocabulary highlighting",
            "dialogues": "Maintain speaker structure",
            "exercises": "Keep exercise formatting",
            "tables": "Preserve conjugation and vocabulary tables",
            "accents": "Maintain all special characters",
        }
    )
