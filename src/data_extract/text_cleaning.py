"""
This module provides utility functions for cleaning and formatting extracted text, such as from PDF documents.
It includes normalization, list conversion, and heading formatting for easier downstream processing or Markdown conversion.
"""
import re


def normalize_text(text: str) -> str:
    """
    Cleans and normalizes extracted text by:
    - Removing page numbers, headers, and footers
    - Removing dates and document metadata
    - Removing table of contents formatting
    - Joining hyphenated words split across lines
    - Fixing broken list formatting
    - Reducing excessive blank lines
    - Normalizing whitespace and line breaks

    Args:
        text (str): The raw extracted text.
    Returns:
        str: The normalized text.
    """

    # Remove specific repeated headers (adjust pattern for your documents)
    text = re.sub(r"^PRODUCT\s+PLUS\s+Portal\s*/\s*NET_APP\s*\d*\s*$", "", text, flags=re.MULTILINE | re.IGNORECASE)

    # Remove page numbers like 'Page 1' or 'Page 1/10'
    text = re.sub(r"Page\s*\d+(\s*/\s*\d+)?", "", text, flags=re.IGNORECASE)

    # Remove standalone page numbers (sole digits on a line, typically in footer)
    # More specific pattern to avoid removing valid numbered items
    text = re.sub(r"^\s*\d{1,3}\s*$", "", text, flags=re.MULTILINE)

    # Remove dates in MM/YYYY or DD/MM/YYYY format
    text = re.sub(r"\b\d{1,2}/\d{2,4}\b", "", text)

    # Remove table of contents leader dots with page numbers (e.g., "............ 5")
    text = re.sub(r"\.{3,}\s*\d+\s*$", "", text, flags=re.MULTILINE)

    # Remove lines with only whitespace and special characters (noise from PDFs)
    text = re.sub(r"^\s*[\x00-\x1F\x7F-\x9F]+\s*$", "", text, flags=re.MULTILINE)

    # Join hyphenated words split across lines (preserve intentional hyphens)
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)

    # Fix broken list items: multiple bullets on consecutive lines followed by content
    # This handles cases where bullets are all on separate lines before content
    lines = text.split('\n')
    cleaned_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Check if this is a standalone bullet/dash
        if line in ['-', '•', '○', '●', '▪', '■'] and i + 1 < len(lines):
            # Look ahead to see if we have more bullets or content
            j = i + 1
            # Skip over consecutive standalone bullets
            while j < len(lines) and lines[j].strip() in ['-', '•', '○', '●', '▪', '■']:
                j += 1
            # Now we're at content lines - collect bullets and match with content
            num_bullets = j - i
            if j < len(lines):
                # We have content lines to match with bullets
                for k in range(num_bullets):
                    if j + k < len(lines) and lines[j + k].strip():
                        cleaned_lines.append(f"- {lines[j + k].strip()}")
                    elif k < num_bullets:
                        cleaned_lines.append("-")  # Empty bullet if no content
                i = j + num_bullets
            else:
                # No content after bullets, just keep the bullets
                for k in range(num_bullets):
                    cleaned_lines.append("-")
                i = j
        else:
            cleaned_lines.append(line)
            i += 1
    text = '\n'.join(cleaned_lines)

    # Remove excessive whitespace lines (lines with only spaces/tabs)
    text = re.sub(r"^\s+$", "", text, flags=re.MULTILINE)

    # Reduce multiple blank lines to maximum of two
    text = re.sub(r"\n{4,}", "\n\n\n", text)

    # Fix lines that were incorrectly split mid-sentence (very conservative)
    # Only join if: lowercase letter/comma at end AND leading space + lowercase at start
    # This indicates continuation of same sentence
    text = re.sub(r"([a-z,])\s*\n\s{2,}([a-z])", r"\1 \2", text)

    # Join lines where content clearly continues (ends without punctuation, next starts lowercase)
    # But be more selective - require specific patterns
    text = re.sub(r"([a-z])\s*\n([a-z][a-z]+\s+[a-z])", r"\1 \2", text)

    # Clean up multiple spaces
    text = re.sub(r" {2,}", " ", text)

    # Final cleanup: reduce to max 2 blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def convert_lists(text: str) -> str:
    """
    Converts bullet points (•, -, o, ○, ●) at the start of lines to Markdown-style '- '.
    Handles nested lists and various bullet styles.

    Args:
        text (str): The text to process.
    Returns:
        str: The text with standardized list markers.
    """
    # Replace various bullet points at the start of lines with '- '
    # Handles: •, -, o, ○, ●, ▪, ■, and variations with spaces
    text = re.sub(r"^\s*[•○●▪■]\s+", "- ", text, flags=re.MULTILINE)

    # Handle dashes that are clearly list markers (followed by space and text)
    text = re.sub(r"^(\s*)-\s+([a-zA-Z])", r"\1- \2", text, flags=re.MULTILINE)

    # Handle numbered lists: convert "1." or "1)" to markdown format
    text = re.sub(r"^\s*(\d+)[.)]\s+", r"\1. ", text, flags=re.MULTILINE)

    return text


def convert_headings(text: str) -> str:
    """
    Converts headings to Markdown format with proper hierarchy:
    - Numbered sections (e.g., "1 TITLE", "2.1 TITLE") become headings at appropriate levels
    - Lines in ALL CAPS (short lines, < 80 chars) become level 2 headings (##)
    - Lines in Title Case (short lines) become level 3 headings (###)
    - Avoids converting table of contents entries, list items, and short labels

    Args:
        text (str): The text to process.
    Returns:
        str: The text with Markdown headings.
    """
    lines = text.split("\n")
    md_lines = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            md_lines.append("")
            continue

        # Skip lines that are already markdown headings
        if stripped.startswith("#"):
            md_lines.append(stripped)
            continue

        # Skip list items
        if re.match(r"^\s*[-•○●▪■]\s+", stripped) or re.match(r"^\s*\d+\.\s+", stripped):
            md_lines.append(stripped)
            continue

        # Pattern 1: Numbered sections like "1 PRODUCT DESCRIPTION" or "2.1 USER SETTINGS"
        numbered_heading = re.match(r"^(\d+(?:\.\d+)*)\s+([A-Z\s]{3,60})$", stripped)
        if numbered_heading:
            level_num = numbered_heading.group(1)
            title = numbered_heading.group(2).strip()
            # Determine heading level based on numbering depth
            level = min(level_num.count(".") + 1, 6)  # Max heading level is 6
            md_lines.append(f"{'#' * level} {title.title()}")
            continue

        # Pattern 2: ALL CAPS headings (but not too long, likely headers not headings)
        # Avoid single words or very short uppercase (likely labels)
        if (stripped.isupper() and
            len(stripped) > 3 and
            len(stripped) < 80 and
            len(stripped.split()) >= 2 and
            len(stripped.split()) <= 10 and
            not re.search(r"[.]{3,}", stripped)):  # Skip TOC entries with dots
            md_lines.append(f"## {stripped.title()}")
            continue

        # Pattern 3: Title Case headings (capitalized first letters)
        # Must be short and have multiple words
        if (stripped.istitle() and
            len(stripped.split()) >= 2 and
            len(stripped.split()) <= 10 and
            len(stripped) < 80 and
            not re.search(r"[.]{3,}", stripped)):  # Skip TOC entries
            md_lines.append(f"### {stripped}")
            continue

        # Default: keep line as-is
        md_lines.append(stripped)

    return "\n".join(md_lines)
