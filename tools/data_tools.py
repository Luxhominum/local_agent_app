from pathlib import Path
import csv
from pypdf import PdfReader
from typing import List, Dict, Any

def read_pdf_text(file_path: str, max_pages: int = 15) -> str:
    """Extracts text from a PDF document for analysis and summarization."""
    try:
        p = Path(file_path).expanduser().resolve()
        if not p.exists() or not p.is_file():
            return f"Error: PDF file '{file_path}' not found."
            
        reader = PdfReader(str(p))
        total_pages = len(reader.pages)
        pages_to_read = min(total_pages, max_pages)
        
        extracted = []
        for i in range(pages_to_read):
            text = reader.pages[i].extract_text()
            if text:
                extracted.append(f"--- PAGE {i+1} ---\n{text.strip()}")
                
        header = f"PDF: {p.name} (Read {pages_to_read} of {total_pages} pages)\n"
        body = "\n\n".join(extracted)
        return header + (body if body else "No readable text extracted from PDF.")
    except Exception as e:
        return f"Error reading PDF '{file_path}': {str(e)}"

def inspect_csv_or_excel(file_path: str, max_rows: int = 10) -> str:
    """Reads headers, row count, and sample rows from a CSV or tabular data file."""
    try:
        p = Path(file_path).expanduser().resolve()
        if not p.exists() or not p.is_file():
            return f"Error: File '{file_path}' not found."
            
        if p.suffix.lower() == ".csv":
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f)
                rows = list(reader)
                
            if not rows:
                return f"CSV file '{p.name}' is empty."
                
            headers = rows[0]
            sample = rows[1:max_rows+1]
            
            output = [
                f"CSV File: {p.name}",
                f"Total Rows: {len(rows)-1} | Columns: {len(headers)}",
                f"Headers: {', '.join(headers)}",
                "\nSample Data (First few rows):"
            ]
            for idx, r in enumerate(sample, 1):
                output.append(f"Row {idx}: {r}")
                
            return "\n".join(output)
        else:
            return f"File extension '{p.suffix}' not supported by CSV inspector. Supported: .csv"
    except Exception as e:
        return f"Error analyzing data file '{file_path}': {str(e)}"
