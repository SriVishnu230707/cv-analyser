import json
import copy

import pymupdf
import pytest
from jsonschema import Draft202012Validator

from backend.main import ROOT
from backend.services import report_export
from backend.tests.test_phase5 import RESUME, JOB, corrections, result, client


def body(format='json'):
    return {'resume_text': RESUME, 'job_description': JOB, 'requirements_confirmed': True, 'category_corrections': corrections(), 'format': format}


def test_json_export_is_recomputed_and_schema_valid():
    response = client.post('/api/report/export', json={**body(), 'scores': {'overall': 100}, 'suggestions': []})
    assert response.status_code == 200
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    report = response.json()
    assert report['scores']['overall'] == 57.5
    assert report['suggestions']
    assert report['analysis_id'][:8] in response.headers['content-disposition']
    Draft202012Validator(json.loads((ROOT / 'contracts/analysis-result-v1.1.schema.json').read_text(encoding='utf-8'))).validate(report)


def test_pdf_is_readable_and_contains_full_findings():
    response = client.post('/api/report/export', json=body('pdf'))
    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/pdf'
    assert response.content.startswith(b'%PDF-')
    with pymupdf.open(stream=response.content, filetype='pdf') as document:
        text = '\n'.join(page.get_text() for page in document)
        assert document.page_count >= 2
        for wording in ['57.5%', 'Docker', 'If you have used', 'Readability checks', 'Prioritized improvement plan', 'Built REST APIs using Python and Flask.', 'uncertain', 'Required Skills']:
            assert wording in text
        assert f'Page {document.page_count} of {document.page_count}' in text
        for number, page in enumerate(document, 1):
            assert 'CV ANALYSER / REVIEWED REPORT' in page.get_text()
            assert f'Page {number} of {len(document)}' in page.get_text()
            assert any(font[4] == 'cvfooter' for font in page.get_fonts())
        assert document.metadata['title'].startswith('CV Analyser')


@pytest.mark.parametrize('change', [{'format': 'docx'}, {'requirements_confirmed': False}, {'category_corrections': []}, {'extraction_context': 'tampered'}, {'resume_text': 'blank'}])
def test_invalid_or_unreviewed_inputs_do_not_export(change):
    response = client.post('/api/report/export', json={**body('pdf'), **change})
    assert response.status_code == 422
    assert response.headers['content-type'] == 'application/json'
    assert 'message' in response.json()


def test_evidence_decisions_survive_export_and_edits_reject_stale_decisions():
    report = result()
    candidate = report['possible_evidence'][0]
    decision = {'requirement_id': candidate['requirement_id'], 'evidence_id': candidate['evidence']['id'], 'decision': 'accept'}
    response = client.post('/api/report/export', json={**body(), 'evidence_decisions': [decision]})
    assert response.json()['scores']['overall'] == 70
    assert any(match['method'] == 'user_confirmed' for match in response.json()['matches'])
    changed = client.post('/api/report/export', json={**body(), 'resume_text': RESUME + '\nUsed Docker to package services.', 'evidence_decisions': [decision]})
    assert changed.status_code == 422


def test_unicode_and_source_markup_are_plain_text_not_active_content():
    report = result()
    phrase = "Resume: R\u00e9sum\u00e9 C++ C# <script>alert('x')</script>"
    report['suggestions'][0]['action'] = phrase
    html = report_export.report_html(report)
    assert '<script>' not in html and '&lt;script&gt;' in html
    with pymupdf.open(stream=report_export.pdf_report(report), filetype='pdf') as document:
        text = '\n'.join(page.get_text() for page in document)
        assert 'R\u00e9sum\u00e9 C++ C#' in text
        assert "<script>alert('x')</script>" in text
        assert all(not page.get_links() for page in document)


def test_long_content_paginates_without_out_of_page_text():
    report = copy.deepcopy(result())
    for index in range(25):
        suggestion = copy.deepcopy(report['suggestions'][0])
        suggestion['action'] = ('A truthful example with a task, tools, and contribution. ' * 10) + ('W' * 400) + f' End marker {index}.'
        report['suggestions'].append(suggestion)
    with pymupdf.open(stream=report_export.pdf_report(report), filetype='pdf') as document:
        assert document.page_count >= 8
        assert 'End marker 24.' in document[-1].get_text()
        for page in document:
            for block in page.get_text('blocks'):
                assert block[0] >= 0 and block[2] <= page.rect.width + 1
                assert block[1] >= 0 and block[3] <= page.rect.height + 1


def test_pdf_limit_is_actionable_and_json_remains_available(monkeypatch):
    monkeypatch.setattr(report_export, 'MAX_PAGES', 1)
    response = client.post('/api/report/export', json=body('pdf'))
    assert response.status_code == 422
    assert response.json()['code'] == 'export_too_large'
    assert client.post('/api/report/export', json=body('json')).status_code == 200
