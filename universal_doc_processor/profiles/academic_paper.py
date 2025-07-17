"""Academic paper processing profile for research papers."""

from ..models import DocumentType, ProcessingProfile


def create_academic_paper_profile() -> ProcessingProfile:
    """Create a processing profile optimized for academic papers."""

    system_prompt = """You are processing an academic research paper. Extract the text with these critical requirements:

ACADEMIC PAPER FORMATTING RULES:
1. PRESERVE STRUCTURE: Maintain clear sections (Abstract, Introduction, Methods, Results, Discussion, References)
2. MERGE PARAGRAPHS: Combine broken lines within the same paragraph - academic text often has awkward line breaks
3. PRESERVE CITATIONS: Keep in-text citations intact (Author, Year) or [1] style references
4. HANDLE FIGURES/TABLES: When you encounter "Figure X" or "Table X", preserve the caption and description
5. MATHEMATICAL NOTATION: Preserve any mathematical expressions, equations, or formulas
6. SKIP HEADERS/FOOTERS: Ignore page numbers, journal names, author names in headers/footers
7. PRESERVE FORMATTING: Keep bold/italic text for emphasis, especially for key terms and section headers
8. HANDLE REFERENCES: Maintain reference list formatting at the end
9. PRESERVE TECHNICAL TERMS: Keep specialized vocabulary and acronyms intact
10. CLEAN HYPHENATION: Fix words split across lines with hyphens

OUTPUT FORMAT:
- Use proper markdown headers (# ## ###) for sections
- Keep paragraphs together without unnecessary line breaks
- Preserve lists and bullet points
- Use **bold** and *italic* markdown formatting
- Maintain table structure where possible
- Keep figure/table captions with their content

SKIP ENTIRELY:
- Page headers with journal/author information
- Page numbers
- Copyright notices
- Repetitive footers"""

    return ProcessingProfile(
        name="Academic Paper",
        document_type=DocumentType.ACADEMIC_PAPER,
        description="Optimized for academic research papers with proper citation and reference handling",

        # OCR settings optimized for dense academic text
        model_name="gemini-2.5-flash",
        batch_size=3,  # Smaller batches for better accuracy on dense text
        image_scale=2.0,

        system_prompt=system_prompt,
        special_instructions=[
            "Pay special attention to mathematical formulas and equations",
            "Preserve all citation formats (both in-text and reference lists)",
            "Maintain figure and table captions",
            "Keep technical terminology intact",
            "Preserve author names and affiliations in the document body (not headers)",
        ],

        # Post-processing settings
        enable_paragraph_merging=True,
        enable_header_removal=True,
        enable_table_detection=True,
        enable_figure_detection=True,
        enable_reference_formatting=True,

        # Quality requirements
        min_quality_score=80.0,  # Higher standard for academic content
        max_retries=3,

        # Academic paper specific patterns
        header_patterns=[
            r"^\d+\s*$",  # Page numbers only
            r"^[A-Z\s]+\s+\d+\s*$",  # JOURNAL NAME 123
            r"^.*\s+et\s+al\.\s*$",  # Author et al. headers
            r"^.*\s+\d{4}\s*$",  # Author 2024 headers
            r"^Proceedings\s+of.*",  # Conference proceedings headers
            r"^Copyright.*",  # Copyright notices
            r"^IEEE.*",  # IEEE headers
            r"^ACL.*",  # ACL conference headers
        ],

        section_patterns=[
            r"^(Abstract|Introduction|Related Work|Methodology|Methods|Results|Discussion|Conclusion|References|Acknowledgments)",
            r"^\d+\.?\s+(Introduction|Methodology|Results|Discussion|Conclusion)",
        ],

        special_formatting={
            "equations": "Preserve mathematical notation",
            "citations": "Maintain citation integrity",
            "figures": "Keep figure captions",
            "tables": "Preserve table structure",
        }
    )
