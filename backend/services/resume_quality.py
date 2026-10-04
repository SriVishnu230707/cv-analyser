"""Text-based resume improvement checks, separate from job coverage scoring."""
import re

from backend.services.evidence_matcher import positive_action


def assess_quality(text, sections):
    names = {section['name'] for section in sections}
    lines = [line.strip() for section in sections if section['name'] in {'Projects', 'Experience'} for line in section['text'].splitlines() if line.strip()]
    action_lines = [line for line in lines if positive_action(line)]
    lengthy = [line for line in lines if len(line.split()) > 45]
    checks = []

    def add(identifier, title, passed, finding, action):
        checks.append({'id': identifier, 'title': title, 'status': 'pass' if passed else 'review', 'finding': finding, 'action': None if passed else action})

    email = bool(re.search(r'(?<![\w.+-])[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b', text))
    add('contact', 'Contact email', email, 'An email address was detected.' if email else 'No email address was detected in the reviewed text.', 'Add a professional contact email if appropriate. Check the original file first: extraction may omit contact details.')
    add('sections', 'Recognizable section headings', bool(names & {'Skills', 'Experience', 'Projects', 'Education'}), 'Recognizable resume sections were detected.' if names & {'Skills', 'Experience', 'Projects', 'Education'} else 'No standard skills, experience, projects, or education heading was detected.', 'Use clear headings such as Skills, Projects, Experience, and Education where relevant. Check the reading order in the extracted preview.')
    add('examples', 'Experience or project examples', bool(lines), 'Experience or project text was detected.' if lines else 'No text was found under Experience or Projects.', 'Add relevant work, academic, volunteer, or personal project examples you actually completed. Entry-level candidates can use Projects; work history is not mandatory.')
    add('contribution', 'Action and contribution wording', bool(action_lines), f'Experience/project lines with recognized action wording: {len(action_lines)}.', 'Describe your own contribution with a specific action, task, and tools. Preserve team ownership and do not claim tasks you did not perform.')
    add('conciseness', 'Concise experience descriptions', not lengthy, f'{len(lengthy)} experience/project lines exceed 45 words.' if lengthy else 'No experience/project line exceeds the 45-word review threshold.', 'Review long descriptions and split them into focused bullets. Preserve the subject, tools, context, and any documented metrics.')
    return {'version': '1.0.0', 'checks': checks, 'review_count': sum(check['status'] == 'review' for check in checks), 'disclaimer': 'These are text-based editing checks, not an employer ATS test. They do not change the job-match score or inspect the original visual layout.'}
