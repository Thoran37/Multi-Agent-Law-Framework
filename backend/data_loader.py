import pypdf
import json
import uuid
from pathlib import Path
from typing import Dict, Any
import re

CASES_DIR = Path("/app/backend/cases")
CASES_DIR.mkdir(exist_ok=True)


def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file bytes."""
    try:
        from io import BytesIO
        pdf_reader = pypdf.PdfReader(BytesIO(file_content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise ValueError(f"Error extracting PDF text: {str(e)}")


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters but keep punctuation
    text = re.sub(r'[^\w\s.,;:!?\'\"()-]', '', text)
    return text.strip()


def save_case(case_data: Dict[str, Any]) -> str:
    """Save case data to JSON file and return case_id."""
    case_id = str(uuid.uuid4())
    case_data['case_id'] = case_id
    
    case_file = CASES_DIR / f"{case_id}.json"
    with open(case_file, 'w', encoding='utf-8') as f:
        json.dump(case_data, f, indent=2, ensure_ascii=False)
    
    return case_id


def load_case(case_id: str) -> Dict[str, Any]:
    """Load case data from JSON file."""
    case_file = CASES_DIR / f"{case_id}.json"
    if not case_file.exists():
        raise FileNotFoundError(f"Case {case_id} not found")
    
    with open(case_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def update_case(case_id: str, updates: Dict[str, Any]) -> None:
    """Update case data with new information."""
    case_data = load_case(case_id)
    case_data.update(updates)
    
    case_file = CASES_DIR / f"{case_id}.json"
    with open(case_file, 'w', encoding='utf-8') as f:
        json.dump(case_data, f, indent=2, ensure_ascii=False)
