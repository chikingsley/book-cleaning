"""Universal post-processor for different document types."""

import re

from ..models import ProcessingProfile, QualityMetrics


class UniversalPostProcessor:
    """Universal post-processor that adapts to different document profiles."""

    def process_text(self, text: str, profile: ProcessingProfile) -> tuple[str, QualityMetrics]:
        """Process text according to the specified profile."""
        metrics = QualityMetrics()

        # Split into lines for processing
        lines = text.split("\\n")
        metrics.lines_processed = len(lines)

        # Apply profile-specific processing
        if profile.enable_header_removal:
            lines, headers_removed = self._remove_headers(lines, profile.header_patterns)
            metrics.headers_removed = headers_removed

        if profile.enable_paragraph_merging:
            lines, paragraphs_merged = self._merge_paragraphs(lines, profile)
            metrics.paragraphs_merged = paragraphs_merged

        if profile.enable_table_detection:
            lines, tables_detected = self._detect_tables(lines)
            metrics.tables_detected = tables_detected

        if profile.enable_figure_detection:
            lines, figures_detected = self._detect_figures(lines)
            metrics.figures_detected = figures_detected

        if profile.enable_reference_formatting:
            lines, refs_detected = self._format_references(lines, profile)
            metrics.references_detected = refs_detected

        # Apply general formatting fixes
        lines, formatting_fixes = self._apply_formatting_fixes(lines, profile)
        metrics.formatting_fixes = formatting_fixes

        # Calculate word count
        final_text = "\\n".join(lines)
        metrics.word_count = len(final_text.split())

        return final_text, metrics

    def _remove_headers(self, lines: list[str], patterns: list[str]) -> tuple[list[str], int]:
        """Remove headers based on the provided patterns."""
        cleaned_lines = []
        headers_removed = 0

        for line in lines:
            is_header = False
            for pattern in patterns:
                if re.match(pattern, line.strip()):
                    is_header = True
                    headers_removed += 1
                    break

            if not is_header:
                cleaned_lines.append(line)

        return cleaned_lines, headers_removed

    def _merge_paragraphs(self, lines: list[str], profile: ProcessingProfile) -> tuple[list[str], int]:
        """Intelligently merge lines that belong to the same paragraph."""
        merged_lines = []
        current_paragraph = []
        paragraphs_merged = 0

        for line in lines:
            line = line.rstrip()

            # Skip empty lines
            if not line:
                if current_paragraph:
                    merged_lines.append(" ".join(current_paragraph))
                    current_paragraph = []
                merged_lines.append("")
                continue

            # Check if this is a special line that shouldn't be merged
            if self._is_special_line(line, profile):
                if current_paragraph:
                    merged_lines.append(" ".join(current_paragraph))
                    current_paragraph = []
                merged_lines.append(line)
                continue

            # Check if line should continue previous paragraph
            if current_paragraph and self._should_merge_with_previous(current_paragraph[-1], line):
                # Handle split formatting (bold/italic)
                merged_line = self._fix_split_formatting(current_paragraph[-1], line)
                if merged_line:
                    current_paragraph[-1] = merged_line
                else:
                    current_paragraph.append(line)
                paragraphs_merged += 1
            else:
                # Start new paragraph or continue current
                if current_paragraph and self._ends_sentence(current_paragraph[-1]):
                    merged_lines.append(" ".join(current_paragraph))
                    current_paragraph = [line]
                else:
                    current_paragraph.append(line)

        # Don't forget last paragraph
        if current_paragraph:
            merged_lines.append(" ".join(current_paragraph))

        return merged_lines, paragraphs_merged

    def _is_special_line(self, line: str, profile: ProcessingProfile) -> bool:
        """Check if line is special and shouldn't be merged."""
        # Use profile-specific section patterns if available
        for pattern in profile.section_patterns:
            if re.match(pattern, line.strip()):
                return True

        # General special patterns
        special_patterns = [
            r"^#+\\s",  # Markdown headers
            r"^\\*\\*[A-Z]",  # Bold section headers
            r"^---+$",  # Horizontal rules
            r"^\\|",  # Table rows
            r"^\\d+\\.\\s",  # Numbered lists
            r"^-\\s",  # Bullet points
            r"^\\*\\s",  # Bullet points
            r"^[A-Z][A-Z\\s]+:",  # Speaker labels (ANNE:, RECEPTIONIST:)
            r"^Exercise\\s+\\d+",  # Exercise headers
            r"^\\*\\*Exercise\\s+\\d+",  # Bold exercise headers
            r"^Example:",  # Example labels
            r"^\\*\\*.*\\*\\*$",  # Full bold lines
            r"^Figure\\s+\\d+",  # Figure captions
            r"^Table\\s+\\d+",  # Table captions
            r"^Abstract\\s*$",  # Abstract header
            r"^References\\s*$",  # References header
        ]

        return any(re.match(pattern, line.strip()) for pattern in special_patterns)

    def _should_merge_with_previous(self, prev_line: str, current_line: str) -> bool:
        """Determine if current line should merge with previous."""
        # Don't merge if previous ends with sentence terminator
        if self._ends_sentence(prev_line):
            return False

        # Don't merge if current starts with capital after period
        if re.match(r"^[A-Z]", current_line) and prev_line.rstrip().endswith("."):
            return False

        # Merge if previous line ends mid-word (hyphenated)
        if prev_line.rstrip().endswith("-"):
            return True

        # Merge if current line starts with lowercase
        if re.match(r"^[a-zà-ÿ]", current_line):
            return True

        # Merge if previous line seems incomplete
        return not re.search(r"[.!?:;]$", prev_line.rstrip()) and not self._looks_like_new_section(current_line)

    def _ends_sentence(self, line: str) -> bool:
        """Check if line ends a complete sentence."""
        line = line.rstrip()
        # Check for sentence endings
        if re.search(r"[.!?]\\s*$", line):
            return True
        # Check for colon (often ends introductory text)
        return line.endswith(":")

    def _looks_like_new_section(self, line: str) -> bool:
        """Check if line looks like the start of a new section."""
        return bool(re.match(r"^(Abstract|Introduction|Methods|Results|Discussion|Conclusion|References|Figure|Table|Exercise)", line))

    def _fix_split_formatting(self, prev_line: str, current_line: str) -> str:
        """Fix formatting split across lines."""
        # Check for split bold formatting
        if prev_line.rstrip().endswith("**") and current_line.startswith("**"):
            # Remove the split markers and combine
            prev_clean = prev_line.rstrip()[:-2]
            curr_clean = current_line[2:]
            return f"{prev_clean}{curr_clean}"

        # Check for split italic formatting
        if (prev_line.rstrip().endswith("*") and current_line.startswith("*")
            and not prev_line.rstrip().endswith(" *")):
            prev_clean = prev_line.rstrip()[:-1]
            curr_clean = current_line[1:]
            return f"{prev_clean}{curr_clean}"

        return ""  # No split formatting detected

    def _detect_tables(self, lines: list[str]) -> tuple[list[str], int]:
        """Detect and format tables."""
        # Simple table detection - look for lines with | characters
        tables_detected = 0
        in_table = False

        for line in lines:
            if "|" in line and len(line.split("|")) >= 3:
                if not in_table:
                    tables_detected += 1
                    in_table = True
            else:
                in_table = False

        return lines, tables_detected

    def _detect_figures(self, lines: list[str]) -> tuple[list[str], int]:
        """Detect figure captions."""
        figures_detected = 0

        for line in lines:
            if re.match(r"^Figure\\s+\\d+", line.strip()):
                figures_detected += 1

        return lines, figures_detected

    def _format_references(self, lines: list[str], _profile: ProcessingProfile) -> tuple[list[str], int]:
        """Format references section."""
        refs_detected = 0
        in_references = False

        for line in lines:
            if re.match(r"^References\\s*$", line.strip()):
                in_references = True
            elif in_references and line.strip() and (re.search(r"\d{4}", line) or re.search(r"\bet\s+al\.", line)):
                refs_detected += 1

        return lines, refs_detected

    def _apply_formatting_fixes(self, lines: list[str], _profile: ProcessingProfile) -> tuple[list[str], int]:
        """Apply general formatting fixes."""
        fixes = 0
        cleaned_lines = []

        for line in lines:
            original = line

            # Fix common OCR issues
            line = re.sub(r"\\s+", " ", line)  # Multiple spaces
            line = re.sub(r"([a-z])- ([a-z])", r"\\1\\2", line)  # Broken words
            line = line.strip()

            if line != original:
                fixes += 1

            cleaned_lines.append(line)

        return cleaned_lines, fixes
