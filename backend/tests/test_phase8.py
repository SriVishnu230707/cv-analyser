import json
import re
import pytest
from backend.tests.test_phase5 import result, client, corrections
from backend.services.evidence_matcher import rules
from backend.services.skill_extractor import CATALOG, skill_mentions


def test_catalog_aliases_are_unambiguous_and_exactly_traceable():
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    assert catalog['version'] == '1.1.0'
    assert len(catalog['skills']) == 71
    aliases = [alias.casefold() for skill in catalog['skills'] for alias in skill['aliases']]
    assert len(aliases) == len(set(aliases))
    for skill in catalog['skills']:
        for alias in skill['aliases']:
            mentions = skill_mentions(alias)
            assert [m['name'] for m in mentions] == [skill['name']]
            assert alias[mentions[0]['start']:mentions[0]['end']] == alias


def test_distinct_new_skills_and_near_matches():
    assert [m['name'] for m in skill_mentions('SQLAlchemy, SQL, SvelteKit, Svelte, ASP.NET Core, .NET')] == ['SQLAlchemy', 'SQL', 'SvelteKit', 'Svelte', 'ASP.NET Core', '.NET']
    assert not skill_mentions('mySvelteTool, Kafkaesque, PowerBIZ, internet, nest, hugging face')


@pytest.mark.parametrize('alias', ['sklearn', 'kafka', 'dotnet', 'pyspark', 'powerbi'])
def test_new_alias_credit_and_learning_gate(alias):
    job = 'Required: ' + alias + '. ' + 'Our team creates reliable customer tools. ' * 3
    assert result('Skills\n' + alias + '\nEducation\nCompleted an introductory course.', job)['scores']['overall'] == 100
    report = result('Skills\nLearning ' + alias + '\nEducation\nCompleted an introductory course.', job)
    assert report['scores']['overall'] == 0
    assert not report['matches'] and not report['possible_evidence']


NEW_TASKS = [('Monitor service health using Prometheus.', 'Monitored service health using Prometheus.'), ('Optimize SQL queries.', 'Optimized SQL queries.'), ('Automate CI/CD pipelines using Jenkins.', 'Automated CI/CD pipelines using Jenkins.'), ('Build data pipelines using Apache Airflow.', 'Built data pipelines using Apache Airflow.')]


@pytest.mark.parametrize('task,evidence', NEW_TASKS)
def test_new_tasks_have_verbatim_evidence_and_versioned_rules(task, evidence):
    job = task + ' ' + 'Our team creates reliable customer tools. ' * 3
    report = result('Projects\n' + evidence + '\nEducation\nCompleted an introductory course.', job)
    automatic = [m for m in report['matches'] if m['method'] == 'rule']
    assert len(automatic) == 1
    assert automatic[0]['evidence']['text'] == evidence
    assert report['rule_version'] == '1.1.1'
    assert report['taxonomy_version'] == '1.1.0'
    assert report['scores']['overall'] == 100


@pytest.mark.parametrize('task,evidence', NEW_TASKS)
def test_new_tasks_reject_negation_learning_and_other_tasks(task, evidence):
    job = task + ' ' + 'Our team creates reliable customer tools. ' * 3
    for source in ['Never ' + evidence.lower(), 'Learning to ' + evidence.lower(), 'Built Python command line tools.']:
        report = result('Projects\n' + source + '\nEducation\nCompleted an introductory course.', job)
        assert not [m for m in report['matches'] if m['method'] == 'rule']


def test_new_task_proposals_preserve_confirmation_gate_and_exports():
    job = ('Monitor service health using Prometheus. ' + 'Our team creates reliable customer tools. ' * 3).strip()
    resume = 'Projects\nTracked application metrics using Prometheus.\nEducation\nCompleted an introductory course.'
    report = result(resume, job)
    assert report['scores']['overall'] == 0
    candidate = report['possible_evidence'][0]
    decision = {'requirement_id': candidate['requirement_id'], 'evidence_id': candidate['evidence']['id'], 'decision': 'accept'}
    body = {'resume_text': resume, 'job_description': job, 'requirements_confirmed': True, 'category_corrections': corrections(job), 'evidence_decisions': [decision], 'format': 'json'}
    response = client.post('/api/report/export', json=body)
    assert response.status_code == 200
    assert response.json()['scores']['overall'] == 100
    assert response.json()['matches'][0]['method'] == 'user_confirmed'
    assert response.json()['taxonomy_version'] == '1.1.0'


def test_rules_are_unique_and_regexes_compile():
    catalog = rules()
    assert catalog['version'] == '1.1.1'
    assert len({r['id'] for r in catalog['rules']}) == len(catalog['rules']) == 10
    for rule in catalog['rules']:
        re.compile(rule['action']); re.compile(rule['object'])
