from pdfminer.high_level import extract_text
from pathlib import Path

def load_pdf(path: str) -> str:
    """
    Extracts text from a PDF file and writes it to a processed text file.

    Args:
        path (str): Path to the PDF file.

    Returns:
        bool: True if extraction and writing succeed.
    """
    # Extract text from the PDF at the given path
    text = extract_text(path)

    # Get the file name without extension to create the output file name
    file_name = Path(path).stem + ".txt"
    # Define output path for the processed text file
    output_path = Path(__file__).resolve().parents[2] / "data_processed" / file_name
    # Write the extracted text to the output file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    # Indicate success
    return text

# Example usage: extract text from a specific PDF file
# load_pdf("C:\\...\\doc\\CustomDataStorage.pdf")
