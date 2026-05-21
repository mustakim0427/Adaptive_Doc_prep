import fitz
import re

PDF_PATH = "data/SLATEFALL_DOSSIER.pdf"

def extract_sections():
    """
    Opens the PDF and splits it into sections.
    Returns a dict like: { "1": "text...", "2": "text..." }
    """
    doc = fitz.open(PDF_PATH)

    full_text = ""
    for page in doc:
        full_text += page.get_text()

    sections = {}
    lines = full_text.split("\n")

    current_section_id = None
    current_text = []

    for line in lines:
        stripped = line.strip()

        # Detect lines like "Section 1. Identity..." or "Section 10. Glossary..."
        match = re.match(r'^Section\s+(\d{1,2})\.\s+\S', stripped)

        if match:
            # Save previous section
            if current_section_id is not None:
                sections[current_section_id] = "\n".join(current_text).strip()
            current_section_id = match.group(1)  # e.g. "1", "2", "10"
            current_text = [stripped]
        else:
            if current_section_id:
                current_text.append(stripped)

    # Save last section
    if current_section_id and current_text:
        sections[current_section_id] = "\n".join(current_text).strip()

    return sections


def get_section_text(section_ids: list, sections: dict) -> str:
    """
    Given a list of section IDs (e.g. ["3", "7"]),
    returns the combined text of those sections.
    """
    combined = ""
    for sid in section_ids:
        if sid in sections:
            combined += f"\n\n--- Section {sid} ---\n{sections[sid]}"
        else:
            combined += f"\n\n--- Section {sid} --- NOT FOUND"
    return combined


# Quick test
if __name__ == "__main__":
    sections = extract_sections()
    print(f"Total sections found: {len(sections)}")
    for sid, text in sections.items():
        print(f"\n--- Section {sid} ---")
        print(text[:300])
        print("...")