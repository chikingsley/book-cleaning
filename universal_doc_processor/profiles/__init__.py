"""Document processing profiles."""

from .academic_paper import create_academic_paper_profile
from .language_textbook import create_language_textbook_profile

__all__ = ["create_academic_paper_profile", "create_language_textbook_profile"]
