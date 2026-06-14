"""
This module provides utility functions for cleaning and formatting extracted text, such as from PDF documents.
It includes normalization, list conversion, and heading formatting for easier downstream processing or Markdown conversion.
"""
import re


def normalize_text(text: str) -> str:
    """
    Cleans and normalizes extracted text by:
    - Removing page numbers (e.g., 'Page 1', 'Page 1/10', '102 - ex.')
    - Removing dates (e.g., '02/2021')
    - Removing app/system names (e.g., 'Product Portal')
    - Joining hyphenated words split across lines
    - Reducing multiple blank lines to a maximum of two
    - Replacing single newlines (not part of a paragraph break) with spaces
    - Stripping leading/trailing whitespace

    Args:
        text (str): The raw extracted text.
    Returns:
        str: The normalized text.
    """

    # Remove page numbers like 'Page 1' or 'Page 1/10'
    text = re.sub(r"Page\s*\d+(\s*/\s*\d+)?", "", text, flags=re.IGNORECASE)

    # Remove standalone page numbers (sole digits on a line, typically in footer)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)

    # Remove dates in MM/YYYY format (e.g., '02/2021')
    text = re.sub(r"\b\d{1,2}/\d{4}\b", "", text)

    # Remove app/system names like 'Product Portal'
    text = re.sub(r"^[A-Z][A-Z\s/@\d]*$", "", text, flags=re.MULTILINE)

    # Join hyphenated words split across lines
    text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

    # Reduce multiple blank lines to a maximum of two
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    # Replace single newlines (not part of a paragraph break) with spaces
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

    return text.strip()


def convert_lists(text: str) -> str:
    """
    Converts bullet points (•, -, o) at the start of lines to Markdown-style '- '.
    Args:
        text (str): The text to process.
    Returns:
        str: The text with standardized list markers.
    """
    # Replace bullet points at the start of lines with '- '
    return re.sub(r"^\s*[•\-o]\s+", "- ", text, flags=re.MULTILINE)


def convert_headings(text: str) -> str:
    """
    Converts headings to Markdown format:
    - Lines in ALL CAPS (up to 8 words) become level 2 headings (##)
    - Lines in Title Case (up to 8 words) become level 3 headings (###)
    - Other lines are left unchanged
    Args:
        text (str): The text to process.
    Returns:
        str: The text with Markdown headings.
    """

    lines = text.split("\n")
    md_lines = []

    for line in lines:
        stripped = line.strip()

        # Convert ALL CAPS headings (short lines) to level 2 Markdown headings
        if stripped.isupper() and len(stripped.split()) <= 8:
            md_lines.append(f"## {stripped.title()}")
        # Convert Title Case headings (short lines) to level 3 Markdown headings
        elif stripped.istitle() and len(stripped.split()) <= 8:
            md_lines.append(f"### {stripped}")
        else:
            md_lines.append(stripped)

    return "\n".join(md_lines)
