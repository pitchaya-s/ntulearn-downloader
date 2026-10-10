from ntulearn_downloader.courses import filter_courses_by_time


def test_filter_courses_by_academic_year_and_semester():
    courses = [
        {"id": "1", "title": "AY2025-26 Semester 1"},
        {"id": "2", "title": "2024/25 Semester 2"},
        {"id": "3", "courseId": "26S1"},
    ]

    assert filter_courses_by_time(courses, year=2025, semester=1) == [courses[0]]
    assert filter_courses_by_time(courses, year=2024) == [courses[1]]
    assert filter_courses_by_time(courses, semester=2) == [courses[1]]
    assert filter_courses_by_time(courses, year=2026, semester=1) == [
        courses[0],
        courses[2],
    ]
