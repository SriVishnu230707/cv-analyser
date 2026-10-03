"""Conservative heading detection; text remains editable by the candidate."""
import re
import unicodedata

HEADINGS = {
    "summary": "Summary", "professional summary": "Summary", "profile": "Summary", "objective": "Summary", "about me": "Summary",
    "skills": "Skills", "technical skills": "Skills", "core competencies": "Skills", "technologies": "Skills",
    "experience": "Experience", "work experience": "Experience", "professional experience": "Experience", "employment history": "Experience",
    "projects": "Projects", "personal projects": "Projects", "academic projects": "Projects",
    "education": "Education", "academic background": "Education",
    "certifications": "Certifications", "certificates": "Certifications",
    "achievements": "Achievements", "awards": "Achievements", "publications": "Publications", "languages": "Languages",
}


def normalize_text(text: str) -> str:
    # Preserve paragraph boundaries, punctuation, skill symbols (C++, C#), and Unicode.
    text = unicodedata.normalize("NFC", text).replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ")
    text = "".join(c for c in text if c in "\n\t" or unicodedata.category(c) != "Cc")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def parse_sections(text: str) -> list[dict]:
    sections = []
    name, lines = "Overview", []

    def flush():
        content = "\n".join(lines).strip()
        if content:
            sections.append({"name": name, "text": content})

    for line in text.splitlines():
        heading, separator, inline = line.partition(":")
        key = heading.strip().casefold().rstrip(".")
        section = HEADINGS.get(key)
        if section and (separator or len(line) < 50):
            flush()
            name, lines = section, ([inline.strip()] if separator and inline.strip() else [])
        else:
            lines.append(line)
    flush()
    return sections
