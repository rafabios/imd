import pytest

from row_selection import parse_row_selection


@pytest.mark.parametrize("value", ["", None, "todos", "todas", "all", "*"])
def test_parse_row_selection_accepts_all(value):
    assert parse_row_selection(value, total_rows=20) is None


def test_parse_row_selection_accepts_numbers_ranges_and_duplicates():
    assert parse_row_selection("1, 3, 5-7; 3 10", total_rows=10) == [1, 3, 5, 6, 7, 10]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("abc", "invalida"),
        ("0,2", "maiores"),
        ("8-3", "invertido"),
        ("1,11", "tem 10 linhas"),
    ],
)
def test_parse_row_selection_rejects_invalid_values(value, message):
    with pytest.raises(ValueError, match=message):
        parse_row_selection(value, total_rows=10)


def test_parse_row_selection_limits_expansion():
    with pytest.raises(ValueError, match="maximo"):
        parse_row_selection("1-10001", total_rows=20000)
