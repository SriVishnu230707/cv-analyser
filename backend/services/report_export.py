"""In-memory PDF rendering of a server-recomputed report, with escaped source text."""
import re
from html import escape
from io import BytesIO

import pymupdf

MAX_PAGES = 100
CSS = """
body { font-family: sans-serif; font-size: 10pt; color: #263b32; line-height: 1.45; }
h1 { font-size: 24pt; color: #235d4f; margin-bottom: 6pt; }
h2 { font-size: 15pt; color: #235d4f; margin-top: 22pt; margin-bottom: 8pt; }
h3 { font-size: 11pt; margin-top: 14pt; margin-bottom: 5pt; }
p { margin-top: 4pt; margin-bottom: 7pt; }
.score { font-size: 30pt; color: #235d4f; }
.meta { font-size: 8pt; color: #667869; }
blockquote { margin: 7pt 0 10pt 12pt; padding-left: 10pt; border-left: 2pt solid #b6cdb3; }
table { width: 100%; border-collapse: collapse; margin: 12pt 0; }
th, td { padding: 7pt; border-bottom: 1pt solid #dbe5d5; text-align: left; font-size: 9pt; }
"""


def text(value):
    # Escape every token before soft-wrapping long strings. Source text never becomes HTML.
    pieces = re.split(r'(\s+)', str(value))
    wrapped = ['&#8203;'.join(escape(piece[i:i + 24]) for i in range(0, len(piece), 24)) if len(piece) > 32 and not piece.isspace() else escape(piece) for piece in pieces]
    return ''.join(wrapped).replace('\n', '<br>')


def paragraph(value, style=''):
    return f'<p class="{style}">{text(value)}</p>'


def excerpt(evidence):
    return paragraph(f"Resume evidence - {evidence['section']}", 'meta') + f"<blockquote>{text(evidence['text'])}</blockquote>"


def report_html(report):
    parts = ['<h1>CV Analyser</h1>', paragraph('Reviewed job-match report', 'meta'), paragraph(f"Analysis ID: {report['analysis_id']}", 'meta')]
    overall = report['scores']['overall']
    parts += [paragraph('Estimated ATS alignment / job match'), paragraph(f'{overall:.1f}%' if overall is not None else 'Not scored', 'score')]
    parts += [paragraph('An application estimate, not an employer ATS result or hiring probability. Skill evidence does not verify proficiency.')]
    parts += [paragraph(f"Policy: {report['scoring_policy_version']} | Dictionary: {report['taxonomy_version']} | Rules: {report['rule_version']}", 'meta')]
    if report.get('ai_analysis'):
        parts.append(paragraph(f"AI advice: {report['ai_analysis']['model']} | Semantic proposals: {report['ai_analysis']['embedding_model']} | Generation: {report['ai_analysis']['generation_id']}", 'meta'))
    parts.append('<table><tr><th>Component</th><th>Coverage</th><th>Credited / total</th><th>Effective weight</th></tr>')
    for name, component in report['scores']['components'].items():
        coverage = f"{component['score']:.1f}%" if component['score'] is not None else 'Not applicable'
        parts.append(f"<tr><td>{text(name.replace('_', ' ').title())}</td><td>{coverage}</td><td>{component['credited_weight']} / {component['total_weight']}</td><td>{100 * component['effective_weight']:.1f}%</td></tr>")
    parts.append('</table>')
    parts += [paragraph(f"{report['informational_requirement_count']} informational or excluded requirements. Possible evidence earns no points until confirmed. Readability and qualifications do not contribute score points.")]
    matches = {m['requirement_id']: m for m in report['matches']}
    qualifications = {q['requirement_id']: q for q in report['qualifications']}
    names = {r['id']: r['name'] for r in report['requirements']}
    parts.append('<h2>Requirements and evidence</h2>')
    if not report['requirements']:
        parts.append(paragraph('No assessable requirements were found.'))
    for requirement in report['requirements']:
        identifier = requirement['id']
        match = matches.get(identifier)
        qualification = qualifications.get(identifier)
        outcome = match['status'] if match else qualification['status'] if qualification else 'not evidenced in this resume' if requirement['included_in_score'] else 'informational / excluded'
        parts += [f"<h3>{text(requirement['name'])}</h3>", paragraph(f"{requirement['category'].replace('_', ' ')} | {outcome.replace('_', ' ')}", 'meta')]
        for source in requirement['sources']:
            parts += [paragraph(f"Job wording - line {source['line_number']}", 'meta'), f"<blockquote>{text(source['text'])}</blockquote>"]
        if match:
            parts += [paragraph(f"Match method: {match['method'].replace('_', ' ')}", 'meta'), excerpt(match['evidence'])]
        if qualification:
            parts.append(paragraph(qualification['reason']))
            if qualification['evidence']:
                parts.append(excerpt(qualification['evidence']))
        for candidate in report['possible_evidence']:
            if candidate['requirement_id'] == identifier:
                parts += [paragraph(f"Possible evidence - {candidate['decision']} (automatic credit: none)", 'meta'), excerpt(candidate['evidence']), paragraph(candidate['reason'])]
    parts += ['<h2>Readability checks</h2>', paragraph(report['readability']['status'].replace('_', ' '))]
    parts.extend(paragraph(issue) for issue in report['readability']['issues'])
    if report.get('resume_quality'):
        parts.append('<h2>Resume quality and editing checks</h2>')
        parts.append(paragraph(report['resume_quality']['disclaimer']))
        for check in report['resume_quality']['checks']:
            parts += [f"<h3>{text(check['title'])} - {check['status']}</h3>", paragraph(check['finding'])]
            if check['action']:
                parts.append(paragraph(check['action']))
    parts.append('<h2>Prioritized improvement plan</h2>')
    if not report['suggestions']:
        parts.append(paragraph('No actionable findings were identified by the current rules.'))
    for suggestion in report['suggestions']:
        parts += [f"<h3>{text(suggestion['priority'].title() + ' priority - ' + suggestion['kind'].replace('_', ' '))}</h3>"]
        parts.append(paragraph('Requirements: ' + '; '.join(names[i] for i in suggestion['requirement_ids']), 'meta') if suggestion['requirement_ids'] else '')
        parts += [paragraph(suggestion['rationale']), paragraph(suggestion['action'])]
        if suggestion['evidence']:
            parts.append(excerpt(suggestion['evidence']))
        if suggestion['rewrite']:
            parts += [paragraph('Optional wording from your existing facts:'), f"<blockquote>{text(suggestion['rewrite'])}</blockquote>", paragraph('Review before using. This wording has not been applied to your resume.', 'meta')]
    parts.append('<h2>Report notes</h2>')
    parts.extend(paragraph(note) for note in report['warnings'])
    return '<html><body>' + ''.join(parts) + '</body></html>'


def pdf_report(report):
    output = BytesIO()
    page_box = pymupdf.Rect(0, 0, 595, 842)

    def rectangle(number, _filled):
        if number >= MAX_PAGES:
            raise ValueError('The PDF would exceed 100 pages. Download JSON instead or shorten the inputs.')
        return page_box, pymupdf.Rect(44, 52, 551, 790), None

    with pymupdf.DocumentWriter(output) as writer:
        pymupdf.Story(report_html(report), user_css=CSS).write(writer, rectangle)
    with pymupdf.open(stream=output.getvalue(), filetype='pdf') as document:
        document.set_metadata({'title': 'CV Analyser - Reviewed job-match report', 'creator': 'CV Analyser'})
        footer_font = pymupdf.Font('helv').buffer
        for number, page in enumerate(document, 1):
            page.insert_font(fontname='cvfooter', fontbuffer=footer_font)
            page.insert_text((44, 29), 'CV ANALYSER / REVIEWED REPORT', fontname='cvfooter', fontsize=8, color=(.35, .45, .36))
            page.insert_text((44, 815), f'Application estimate | Page {number} of {len(document)}', fontname='cvfooter', fontsize=8, color=(.35, .45, .36))
        return document.tobytes(garbage=4, deflate=True)
