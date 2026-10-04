import pytest

from backend.tests.test_phase5 import result
from backend.services.qualification_matcher import qualification_findings


@pytest.mark.parametrize('separator', ['. ', '; ', ' but '])
def test_an_unrelated_action_does_not_demonstrate_a_skill(separator):
    resume = 'Projects\nBuilt JavaScript applications' + separator + 'Python.\nEducation\nCompleted an introductory course.'
    job = 'Required: Python. ' + 'Our team builds useful customer tools. ' * 3
    report = result(resume, job)
    assert report['scores']['overall'] == 0
    assert not report['matches']
    assert report['possible_evidence']


@pytest.mark.parametrize('wording', ['Python (learning)', 'Python - currently studying', 'Python: learning'])
def test_learning_after_the_skill_does_not_earn_credit(wording):
    report = result('Skills\n' + wording + '\nEducation\nCompleted an introductory course.', 'Required: Python. ' + 'Our team builds useful customer tools. ' * 3)
    assert not report['matches']
    assert not report['possible_evidence']


@pytest.mark.parametrize('wording', ['Masterclass in computer science.', "Unfinished master's degree in computer science.", "Working towards a master's degree in computer science.", 'Master of computer sciences.'])
def test_unrelated_or_unfinished_education_does_not_meet_degree(wording):
    finding = qualification_findings([{'name': 'Education', 'text': wording}], [{'id': 'q1', 'category': 'qualification', 'name': 'Master degree in computer science required.'}], 'hash')[0]
    assert finding['status'] == 'not_evidenced'
    assert finding['evidence'] is None


def test_degree_inflections_match_the_same_explicit_type():
    finding = qualification_findings([{'name': 'Education', 'text': 'Completed Master degree in computer science.'}], [{'id': 'q1', 'category': 'qualification', 'name': "Master's degree in computer science required."}], 'hash')[0]
    assert finding['status'] == 'met'


@pytest.mark.parametrize('wording', ['Built Java command line tools. REST APIs.', 'Built REST APIs. Java.', 'Built REST APIs; Java.'])
def test_responsibility_actions_and_tools_cannot_cross_clauses(wording):
    report = result('Projects\n' + wording + '\nEducation\nCompleted an introductory course.', 'Build REST APIs using Java. ' + 'Our team creates reliable customer tools. ' * 3)
    assert not report['matches']
    assert report['possible_evidence']
