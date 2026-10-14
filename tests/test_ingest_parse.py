"""Workbook parsing, tested against small hand-built workbooks that mimic the DoS layout."""

import openpyxl
import pytest

from mizan.ingest import dos_cpi

EN_MONTHS = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]


def _write(path, year, values, average, extra_col=False, title=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append([f"الأرقام القياسية لعام {year} (2018=100)"])
    ws.append([title or f"Monthly And cummulative Consumer Price Indices During {year} (2018=100)"])
    ws.append(["مجموعـــــــــات الانفـــــــاق", "الاهمية النسبية", "كانون ثاني"] + ["x"] * 11 + ["المعدل", "Expenditure Groups"])
    ws.append([None, "Relative Imp."] + EN_MONTHS + ["Average"] + (["extra"] if extra_col else []))
    ws.append(["جميع المواد", 100] + values + [None] * (12 - len(values)) + [average, " All Items"])
    ws.append(["1) الاغذية", 26.5] + [50.0] * 12 + [50.0, "Food"])
    wb.save(path)


def test_parses_full_year(tmp_path):
    vals = [100 + i for i in range(12)]
    f = tmp_path / "2020.xlsx"
    _write(f, 2020, vals, sum(vals) / 12)
    p = dos_cpi.parse_workbook(f, 2020)
    assert p.values == {m: float(v) for m, v in zip(range(1, 13), vals)}
    assert p.average == pytest.approx(sum(vals) / 12)
    assert dos_cpi.check_average(p)["ok"] is True
    assert p.notes == []


def test_parses_partial_year_by_header_not_position(tmp_path):
    f = tmp_path / "2026.xlsx"
    _write(f, 2026, [110.0, 111.0, 112.0], 111.0, extra_col=True)
    p = dos_cpi.parse_workbook(f, 2026)
    assert sorted(p.values) == [1, 2, 3]
    assert p.values[3] == 112.0
    assert dos_cpi.check_average(p)["ok"] is True


def test_average_mismatch_is_reported(tmp_path):
    f = tmp_path / "2021.xlsx"
    _write(f, 2021, [100.0] * 12, 105.0)
    assert dos_cpi.check_average(dos_cpi.parse_workbook(f, 2021))["ok"] is False


def test_title_year_typo_is_noted_not_fatal(tmp_path):
    f = tmp_path / "2016.xlsx"
    _write(f, 2016, [100.0] * 12, 100.0, title="Monthly And cummulative Consumer Price Indices During 2015 (2018=100)")
    p = dos_cpi.parse_workbook(f, 2016)
    assert any("different year" in n for n in p.notes)


def test_missing_all_items_row_raises(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["title"])
    ws.append([None, None] + EN_MONTHS + ["Average"])
    ws.append(["x", 1] + [1.0] * 12)
    f = tmp_path / "bad.xlsx"
    wb.save(f)
    with pytest.raises(ValueError, match="All Items"):
        dos_cpi.parse_workbook(f, 2020)


def test_build_series_rejects_gaps(tmp_path):
    bad = dos_cpi.WorkbookParse(2020, "s", "t", {1: 1.0, 3: 3.0}, None)
    with pytest.raises(ValueError, match="contiguous"):
        dos_cpi.build_series([bad])


def test_build_series_orders_years():
    a = dos_cpi.WorkbookParse(2021, "s", "t", {1: 2.0, 2: 3.0}, None)
    b = dos_cpi.WorkbookParse(2020, "s", "t", {m: 1.0 for m in range(1, 13)}, None)
    df = dos_cpi.build_series([a, b])
    assert df["period"].iloc[0] == "2020-01" and df["period"].iloc[-1] == "2021-02" and len(df) == 14
