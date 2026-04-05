"""
This module provides a function to convert raw extracted PDF text into Markdown format. It applies a sequence of text cleaning and formatting steps, including normalization, list conversion, and heading conversion, to produce Markdown-ready output.
"""
from .text_cleaning import normalize_text, convert_lists, convert_headings


def pdf_text_to_markdown(raw_text: str) -> str:
    """
    Converts raw extracted PDF text to Markdown format by applying normalization, list conversion, and heading formatting.

    Args:
        raw_text (str): The raw text extracted from a PDF file.
    Returns:
        str: The cleaned and formatted Markdown text.
    """
    # Normalize the text (remove page numbers, fix hyphens, etc.)
    text = normalize_text(raw_text)

    # Convert bullet points to Markdown-style lists
    text = convert_lists(text)

    # Convert headings to Markdown format
    text = convert_headings(text)

    return text
