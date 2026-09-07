from ntulearn_downloader.cli import (
    build_parser,
    choose_courses,
    filename_from_url,
    sanitize_component,
)


def test_sanitize_component():
    assert sanitize_component('Week 1: Intro / Notes') == 'Week 1_ Intro _ Notes'
    assert sanitize_component('..') == 'untitled'


def test_filename_from_url():
    assert filename_from_url('https://example.test/a/Lecture%201.pdf?x=1') == 'Lecture 1.pdf'


def test_choose_courses():
    courses = [
        {'id': '_1_1', 'title': 'SC2001 Algorithms'},
        {'id': '_2_1', 'title': 'MH2802 Linear Algebra'},
    ]
    assert choose_courses(courses, ['sc2001']) == [courses[0]]
    assert choose_courses(courses, ['_2_1']) == [courses[1]]
    assert choose_courses(courses, []) == courses


def test_parser_accepts_all():
    parser = build_parser()
    args = parser.parse_args(["--all"])
    assert args.all is True
    assert args.course is None


def test_parser_accepts_course():
    parser = build_parser()
    args = parser.parse_args(["-c", "SC2001"])
    assert args.all is False
    assert args.course == ["SC2001"]
