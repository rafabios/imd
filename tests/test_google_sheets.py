from google_sheets import normalize_google_sheet_csv_url


def test_regular_google_sheet_link_becomes_csv_export():
    source = "https://docs.google.com/spreadsheets/d/abc_123/edit?usp=sharing#gid=456"

    assert normalize_google_sheet_csv_url(source) == (
        "https://docs.google.com/spreadsheets/d/abc_123/export?format=csv&gid=456"
    )


def test_google_sheet_link_without_gid_uses_first_tab():
    source = "https://docs.google.com/spreadsheets/d/abc_123/edit"

    assert normalize_google_sheet_csv_url(source) == (
        "https://docs.google.com/spreadsheets/d/abc_123/export?format=csv&gid=0"
    )


def test_published_google_sheet_link_becomes_published_csv():
    source = "https://docs.google.com/spreadsheets/d/e/2PACX-demo/pubhtml?gid=9&single=true"

    assert normalize_google_sheet_csv_url(source) == (
        "https://docs.google.com/spreadsheets/d/e/2PACX-demo/pub?output=csv&gid=9&single=true"
    )


def test_non_google_source_is_preserved():
    assert normalize_google_sheet_csv_url("C:/listas/faixas.csv") == "C:/listas/faixas.csv"
    assert normalize_google_sheet_csv_url("https://example.test/faixas.csv") == "https://example.test/faixas.csv"
    assert normalize_google_sheet_csv_url(None) == ""
