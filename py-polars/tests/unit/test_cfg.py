from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterator

import pytest

import polars as pl
from polars.config import _POLARS_CFG_ENV_VARS, _get_float_fmt
from polars.exceptions import StringCacheMismatchError
from polars.testing import assert_frame_equal


@pytest.fixture(autouse=True)
def _environ() -> Iterator[None]:
    """Fixture to restore the environment after/during tests."""
    with pl.StringCache(), pl.Config(restore_defaults=True):
        yield


def test_ascii_tables() -> None:
    df = pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})

    ascii_table_repr = (
        "shape: (3, 3)\n"
        "+-----+-----+-----+\n"
        "| a   | b   | c   |\n"
        "| --- | --- | --- |\n"
        "| i64 | i64 | i64 |\n"
        "+=================+\n"
        "| 1   | 4   | 7   |\n"
        "| 2   | 5   | 8   |\n"
        "| 3   | 6   | 9   |\n"
        "+-----+-----+-----+"
    )
    # note: expect to render ascii only within the given scope
    with pl.Config(set_ascii_tables=True):
        assert repr(df) == ascii_table_repr

    # confirm back to utf8 default after scope-exit
    assert (
        repr(df) == "shape: (3, 3)\n"
        "┌─────┬─────┬─────┐\n"
        "│ a   ┆ b   ┆ c   │\n"
        "│ --- ┆ --- ┆ --- │\n"
        "│ i64 ┆ i64 ┆ i64 │\n"
        "╞═════╪═════╪═════╡\n"
        "│ 1   ┆ 4   ┆ 7   │\n"
        "│ 2   ┆ 5   ┆ 8   │\n"
        "│ 3   ┆ 6   ┆ 9   │\n"
        "└─────┴─────┴─────┘"
    )

    @pl.Config(set_ascii_tables=True)
    def ascii_table() -> str:
        return repr(df)

    assert ascii_table() == ascii_table_repr


def test_hide_header_elements() -> None:
    df = pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})

    pl.Config.set_tbl_hide_column_data_types(True)
    assert (
        str(df) == "shape: (3, 3)\n"
        "┌───┬───┬───┐\n"
        "│ a ┆ b ┆ c │\n"
        "╞═══╪═══╪═══╡\n"
        "│ 1 ┆ 4 ┆ 7 │\n"
        "│ 2 ┆ 5 ┆ 8 │\n"
        "│ 3 ┆ 6 ┆ 9 │\n"
        "└───┴───┴───┘"
    )

    pl.Config.set_tbl_hide_column_data_types(False).set_tbl_hide_column_names(True)
    assert (
        str(df) == "shape: (3, 3)\n"
        "┌─────┬─────┬─────┐\n"
        "│ i64 ┆ i64 ┆ i64 │\n"
        "╞═════╪═════╪═════╡\n"
        "│ 1   ┆ 4   ┆ 7   │\n"
        "│ 2   ┆ 5   ┆ 8   │\n"
        "│ 3   ┆ 6   ┆ 9   │\n"
        "└─────┴─────┴─────┘"
    )


def test_html_tables() -> None:
    df = pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})

    # default: header contains names/dtypes
    header = "<thead><tr><th>a</th><th>b</th><th>c</th></tr><tr><td>i64</td><td>i64</td><td>i64</td></tr></thead>"
    assert header in df._repr_html_()

    # validate that relevant config options are respected
    with pl.Config(tbl_hide_column_names=True):
        header = "<thead><tr><td>i64</td><td>i64</td><td>i64</td></tr></thead>"
        assert header in df._repr_html_()

    with pl.Config(tbl_hide_column_data_types=True):
        header = "<thead><tr><th>a</th><th>b</th><th>c</th></tr></thead>"
        assert header in df._repr_html_()

    with pl.Config(
        tbl_hide_column_data_types=True,
        tbl_hide_column_names=True,
    ):
        header = "<thead></thead>"
        assert header in df._repr_html_()


def test_set_tbl_cols() -> None:
    df = pl.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})

    pl.Config.set_tbl_cols(1)
    assert str(df).split("\n")[2] == "│ a   ┆ … │"
    pl.Config.set_tbl_cols(2)
    assert str(df).split("\n")[2] == "│ a   ┆ … ┆ c   │"
    pl.Config.set_tbl_cols(3)
    assert str(df).split("\n")[2] == "│ a   ┆ b   ┆ c   │"

    df = pl.DataFrame(
        {"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9], "d": [10, 11, 12]}
    )
    pl.Config.set_tbl_cols(2)
    assert str(df).split("\n")[2] == "│ a   ┆ … ┆ d   │"
    pl.Config.set_tbl_cols(3)
    assert str(df).split("\n")[2] == "│ a   ┆ b   ┆ … ┆ d   │"
    pl.Config.set_tbl_cols(-1)
    assert str(df).split("\n")[2] == "│ a   ┆ b   ┆ c   ┆ d   │"


def test_set_tbl_rows() -> None:
    df = pl.DataFrame({"a": [1, 2, 3, 4], "b": [5, 6, 7, 8], "c": [9, 10, 11, 12]})
    ser = pl.Series("ser", [1, 2, 3, 4, 5])

    pl.Config.set_tbl_rows(0)
    assert (
        str(df) == "shape: (4, 3)\n"
        "┌─────┬─────┬─────┐\n"
        "│ a   ┆ b   ┆ c   │\n"
        "│ --- ┆ --- ┆ --- │\n"
        "│ i64 ┆ i64 ┆ i64 │\n"
        "╞═════╪═════╪═════╡\n"
        "│ …   ┆ …   ┆ …   │\n"
        "└─────┴─────┴─────┘"
    )
    assert str(ser) == "shape: (5,)\n" "Series: 'ser' [i64]\n" "[\n" "\t…\n" "]"

    pl.Config.set_tbl_rows(1)
    assert (
        str(df) == "shape: (4, 3)\n"
        "┌─────┬─────┬─────┐\n"
        "│ a   ┆ b   ┆ c   │\n"
        "│ --- ┆ --- ┆ --- │\n"
        "│ i64 ┆ i64 ┆ i64 │\n"
        "╞═════╪═════╪═════╡\n"
        "│ 1   ┆ 5   ┆ 9   │\n"
        "│ …   ┆ …   ┆ …   │\n"
        "└─────┴─────┴─────┘"
    )
    assert str(ser) == "shape: (5,)\n" "Series: 'ser' [i64]\n" "[\n" "\t1\n" "\t…\n" "]"

    pl.Config.set_tbl_rows(2)
    assert (
        str(df) == "shape: (4, 3)\n"
        "┌─────┬─────┬─────┐\n"
        "│ a   ┆ b   ┆ c   │\n"
        "│ --- ┆ --- ┆ --- │\n"
        "│ i64 ┆ i64 ┆ i64 │\n"
        "╞═════╪═════╪═════╡\n"
        "│ 1   ┆ 5   ┆ 9   │\n"
        "│ …   ┆ …   ┆ …   │\n"
        "│ 4   ┆ 8   ┆ 12  │\n"
        "└─────┴─────┴─────┘"
    )
    assert (
        str(ser) == "shape: (5,)\n"
        "Series: 'ser' [i64]\n"
        "[\n"
        "\t1\n"
        "\t…\n"
        "\t5\n"
        "]"
    )

    pl.Config.set_tbl_rows(3)
    assert (
        str(df) == "shape: (4, 3)\n"
        "┌─────┬─────┬─────┐\n"
        "│ a   ┆ b   ┆ c   │\n"
        "│ --- ┆ --- ┆ --- │\n"
        "│ i64 ┆ i64 ┆ i64 │\n"
        "╞═════╪═════╪═════╡\n"
        "│ 1   ┆ 5   ┆ 9   │\n"
        "│ 2   ┆ 6   ┆ 10  │\n"
        "│ 3   ┆ 7   ┆ 11  │\n"
        "│ 4   ┆ 8   ┆ 12  │\n"
        "└─────┴─────┴─────┘"
    )
    assert (
        str(ser) == "shape: (5,)\n"
        "Series: 'ser' [i64]\n"
        "[\n"
        "\t1\n"
        "\t…\n"
        "\t4\n"
        "\t5\n"
        "]"
    )

    pl.Config.set_tbl_rows(4)
    assert (
        str(df) == "shape: (4, 3)\n"
        "┌─────┬─────┬─────┐\n"
        "│ a   ┆ b   ┆ c   │\n"
        "│ --- ┆ --- ┆ --- │\n"
        "│ i64 ┆ i64 ┆ i64 │\n"
        "╞═════╪═════╪═════╡\n"
        "│ 1   ┆ 5   ┆ 9   │\n"
        "│ 2   ┆ 6   ┆ 10  │\n"
        "│ 3   ┆ 7   ┆ 11  │\n"
        "│ 4   ┆ 8   ┆ 12  │\n"
        "└─────┴─────┴─────┘"
    )
    assert (
        str(ser) == "shape: (5,)\n"
        "Series: 'ser' [i64]\n"
        "[\n"
        "\t1\n"
        "\t2\n"
        "\t3\n"
        "\t4\n"
        "\t5\n"
        "]"
    )

    df = pl.DataFrame(
        {
            "a": [1, 2, 3, 4, 5],
            "b": [6, 7, 8, 9, 10],
            "c": [11, 12, 13, 14, 15],
        }
    )

    pl.Config.set_tbl_rows(3)
    assert (
        str(df) == "shape: (5, 3)\n"
        "┌─────┬─────┬─────┐\n"
        "│ a   ┆ b   ┆ c   │\n"
        "│ --- ┆ --- ┆ --- │\n"
        "│ i64 ┆ i64 ┆ i64 │\n"
        "╞═════╪═════╪═════╡\n"
        "│ 1   ┆ 6   ┆ 11  │\n"
        "│ …   ┆ …   ┆ …   │\n"
        "│ 4   ┆ 9   ┆ 14  │\n"
        "│ 5   ┆ 10  ┆ 15  │\n"
        "└─────┴─────┴─────┘"
    )

    pl.Config.set_tbl_rows(-1)
    assert (
        str(ser) == "shape: (5,)\n"
        "Series: 'ser' [i64]\n"
        "[\n"
        "\t1\n"
        "\t2\n"
        "\t3\n"
        "\t4\n"
        "\t5\n"
        "]"
    )

    pl.Config.set_tbl_hide_dtype_separator(True)
    assert (
        str(df) == "shape: (5, 3)\n"
        "┌─────┬─────┬─────┐\n"
        "│ a   ┆ b   ┆ c   │\n"
        "│ i64 ┆ i64 ┆ i64 │\n"
        "╞═════╪═════╪═════╡\n"
        "│ 1   ┆ 6   ┆ 11  │\n"
        "│ 2   ┆ 7   ┆ 12  │\n"
        "│ 3   ┆ 8   ┆ 13  │\n"
        "│ 4   ┆ 9   ┆ 14  │\n"
        "│ 5   ┆ 10  ┆ 15  │\n"
        "└─────┴─────┴─────┘"
    )


def test_set_tbl_formats() -> None:
    df = pl.DataFrame(
        {
            "foo": [1, 2, 3],
            "bar": [6.0, 7.0, 8.0],
            "ham": ["a", "b", "c"],
        }
    )
    pl.Config().set_tbl_formatting("ASCII_MARKDOWN")
    assert str(df) == (
        "shape: (3, 3)\n"
        "| foo | bar | ham |\n"
        "| --- | --- | --- |\n"
        "| i64 | f64 | str |\n"
        "|-----|-----|-----|\n"
        "| 1   | 6.0 | a   |\n"
        "| 2   | 7.0 | b   |\n"
        "| 3   | 8.0 | c   |"
    )

    pl.Config().set_tbl_formatting("ASCII_BORDERS_ONLY_CONDENSED")
    with pl.Config(tbl_hide_dtype_separator=True):
        assert str(df) == (
            "shape: (3, 3)\n"
            "+-----------------+\n"
            "| foo   bar   ham |\n"
            "| i64   f64   str |\n"
            "+=================+\n"
            "| 1     6.0   a   |\n"
            "| 2     7.0   b   |\n"
            "| 3     8.0   c   |\n"
            "+-----------------+"
        )

    # temporarily scope "nothing" style, with no data types
    with pl.Config(
        tbl_formatting="NOTHING",
        tbl_hide_column_data_types=True,
    ):
        assert str(df) == (
            "shape: (3, 3)\n"
            " foo  bar  ham \n"
            " 1    6.0  a   \n"
            " 2    7.0  b   \n"
            " 3    8.0  c   "
        )

    # after scope, expect previous style
    assert str(df) == (
        "shape: (3, 3)\n"
        "+-----------------+\n"
        "| foo   bar   ham |\n"
        "| ---   ---   --- |\n"
        "| i64   f64   str |\n"
        "+=================+\n"
        "| 1     6.0   a   |\n"
        "| 2     7.0   b   |\n"
        "| 3     8.0   c   |\n"
        "+-----------------+"
    )

    # invalid style
    with pytest.raises(ValueError, match="invalid table format name: 'NOPE'"):
        pl.Config().set_tbl_formatting("NOPE")  # type: ignore[arg-type]


def test_set_tbl_width_chars() -> None:
    df = pl.DataFrame(
        {
            "a really long col": [1, 2, 3],
            "b": ["", "this is a string value that will be truncated", None],
            "this is 10": [4, 5, 6],
        }
    )
    assert max(len(line) for line in str(df).split("\n")) == 70

    pl.Config.set_tbl_width_chars(60)
    assert max(len(line) for line in str(df).split("\n")) == 60

    # force minimal table size (will hard-wrap everything; "don't try this at home" :p)
    pl.Config.set_tbl_width_chars(0)
    assert max(len(line) for line in str(df).split("\n")) == 19

    # this check helps to check that column width bucketing
    # is exact; no extraneous character allocation
    df = pl.DataFrame(
        {
            "A": [1, 2, 3, 4, 5],
            "fruits": ["banana", "banana", "apple", "apple", "banana"],
            "B": [5, 4, 3, 2, 1],
            "cars": ["beetle", "audi", "beetle", "beetle", "beetle"],
        },
        schema_overrides={"A": pl.Int64, "B": pl.Int64},
    ).select(pl.all(), pl.all().suffix("_suffix!"))

    with pl.Config(tbl_width_chars=87):
        assert max(len(line) for line in str(df).split("\n")) == 87


def test_shape_below_table_and_inlined_dtype() -> None:
    df = pl.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})

    pl.Config.set_tbl_column_data_type_inline(True).set_tbl_dataframe_shape_below(True)
    pl.Config.set_tbl_formatting("UTF8_FULL", rounded_corners=True)
    assert (
        str(df) == ""
        "╭─────────┬─────────┬─────────╮\n"
        "│ a (i64) ┆ b (i64) ┆ c (i64) │\n"
        "╞═════════╪═════════╪═════════╡\n"
        "│ 1       ┆ 3       ┆ 5       │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 2       ┆ 4       ┆ 6       │\n"
        "╰─────────┴─────────┴─────────╯\n"
        "shape: (2, 3)"
    )

    pl.Config.set_tbl_dataframe_shape_below(False)
    assert (
        str(df) == "shape: (2, 3)\n"
        "╭─────────┬─────────┬─────────╮\n"
        "│ a (i64) ┆ b (i64) ┆ c (i64) │\n"
        "╞═════════╪═════════╪═════════╡\n"
        "│ 1       ┆ 3       ┆ 5       │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 2       ┆ 4       ┆ 6       │\n"
        "╰─────────┴─────────┴─────────╯"
    )
    (
        pl.Config.set_tbl_formatting(None, rounded_corners=False)
        .set_tbl_column_data_type_inline(False)
        .set_tbl_cell_alignment("RIGHT")
    )
    assert (
        str(df) == "shape: (2, 3)\n"
        "┌─────┬─────┬─────┐\n"
        "│   a ┆   b ┆   c │\n"
        "│ --- ┆ --- ┆ --- │\n"
        "│ i64 ┆ i64 ┆ i64 │\n"
        "╞═════╪═════╪═════╡\n"
        "│   1 ┆   3 ┆   5 │\n"
        "│   2 ┆   4 ┆   6 │\n"
        "└─────┴─────┴─────┘"
    )
    with pytest.raises(ValueError):
        pl.Config.set_tbl_cell_alignment("INVALID")  # type: ignore[arg-type]


def test_shape_format_for_big_numbers() -> None:
    df = pl.DataFrame({"a": range(1, 1001), "b": range(1001, 1001 + 1000)})

    pl.Config.set_tbl_column_data_type_inline(True).set_tbl_dataframe_shape_below(True)
    pl.Config.set_tbl_formatting("UTF8_FULL", rounded_corners=True)
    assert (
        str(df) == ""
        "╭─────────┬─────────╮\n"
        "│ a (i64) ┆ b (i64) │\n"
        "╞═════════╪═════════╡\n"
        "│ 1       ┆ 1001    │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 2       ┆ 1002    │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 3       ┆ 1003    │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 4       ┆ 1004    │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ …       ┆ …       │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 997     ┆ 1997    │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 998     ┆ 1998    │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 999     ┆ 1999    │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 1000    ┆ 2000    │\n"
        "╰─────────┴─────────╯\n"
        "shape: (1_000, 2)"
    )

    pl.Config.set_tbl_column_data_type_inline(True).set_tbl_dataframe_shape_below(False)
    assert (
        str(df) == "shape: (1_000, 2)\n"
        "╭─────────┬─────────╮\n"
        "│ a (i64) ┆ b (i64) │\n"
        "╞═════════╪═════════╡\n"
        "│ 1       ┆ 1001    │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 2       ┆ 1002    │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 3       ┆ 1003    │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 4       ┆ 1004    │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ …       ┆ …       │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 997     ┆ 1997    │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 998     ┆ 1998    │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 999     ┆ 1999    │\n"
        "├╌╌╌╌╌╌╌╌╌┼╌╌╌╌╌╌╌╌╌┤\n"
        "│ 1000    ┆ 2000    │\n"
        "╰─────────┴─────────╯"
    )

    pl.Config.set_tbl_rows(0)
    ser = pl.Series("ser", range(1000))
    assert str(ser) == "shape: (1_000,)\n" "Series: 'ser' [i64]\n" "[\n" "\t…\n" "]"

    pl.Config.set_tbl_rows(1)
    pl.Config.set_tbl_cols(1)
    df = pl.DataFrame({str(col_num): 1 for col_num in range(1000)})

    assert (
        str(df) == "shape: (1, 1_000)\n"
        "╭─────────┬───╮\n"
        "│ 0 (i64) ┆ … │\n"
        "╞═════════╪═══╡\n"
        "│ 1       ┆ … │\n"
        "╰─────────┴───╯"
    )


def test_string_cache() -> None:
    df1 = pl.DataFrame({"a": ["foo", "bar", "ham"], "b": [1, 2, 3]})
    df2 = pl.DataFrame({"a": ["foo", "spam", "eggs"], "c": [3, 2, 2]})

    # ensure cache is off when casting to categorical; the join will fail
    pl.enable_string_cache(False)
    assert pl.using_string_cache() is False

    df1a = df1.with_columns(pl.col("a").cast(pl.Categorical))
    df2a = df2.with_columns(pl.col("a").cast(pl.Categorical))
    with pytest.raises(StringCacheMismatchError):
        _ = df1a.join(df2a, on="a", how="inner")

    # now turn on the cache
    pl.enable_string_cache(True)
    assert pl.using_string_cache() is True

    df1b = df1.with_columns(pl.col("a").cast(pl.Categorical))
    df2b = df2.with_columns(pl.col("a").cast(pl.Categorical))
    out = df1b.join(df2b, on="a", how="inner")

    expected = pl.DataFrame(
        {"a": ["foo"], "b": [1], "c": [3]}, schema_overrides={"a": pl.Categorical}
    )
    assert_frame_equal(out, expected)


@pytest.mark.write_disk()
def test_config_load_save(tmp_path: Path) -> None:
    for file in (None, tmp_path / "polars.config", str(tmp_path / "polars.config")):
        # set some config options...
        pl.Config.set_tbl_cols(12)
        pl.Config.set_verbose(True)
        pl.Config.set_fmt_float("full")
        assert os.environ.get("POLARS_VERBOSE") == "1"

        cfg = pl.Config.save(file)
        assert isinstance(cfg, str)
        assert "POLARS_VERBOSE" in pl.Config.state(if_set=True)

        # ...modify the same options...
        pl.Config.set_tbl_cols(10)
        pl.Config.set_verbose(False)
        assert os.environ.get("POLARS_VERBOSE") == "0"

        # ...load back from config...
        if file is not None:
            assert Path(cfg).is_file()
        pl.Config.load(cfg)

        # ...and confirm the saved options were set.
        assert os.environ.get("POLARS_FMT_MAX_COLS") == "12"
        assert os.environ.get("POLARS_VERBOSE") == "1"
        assert _get_float_fmt() == "full"

        # restore all default options (unsets from env)
        pl.Config.restore_defaults()
        for e in ("POLARS_FMT_MAX_COLS", "POLARS_VERBOSE"):
            assert e not in pl.Config.state(if_set=True)
            assert e in pl.Config.state()

        assert os.environ.get("POLARS_FMT_MAX_COLS") is None
        assert os.environ.get("POLARS_VERBOSE") is None
        assert _get_float_fmt() == "mixed"


def test_config_scope() -> None:
    pl.Config.set_verbose(False)
    pl.Config.set_tbl_cols(8)

    initial_state = pl.Config.state()

    with pl.Config() as cfg:
        (
            cfg.set_tbl_formatting(rounded_corners=True)
            .set_verbose(True)
            .set_tbl_hide_dtype_separator(True)
            .set_ascii_tables()
        )
        new_state_entries = set(
            {
                "POLARS_FMT_MAX_COLS": "8",
                "POLARS_FMT_TABLE_FORMATTING": "ASCII_FULL_CONDENSED",
                "POLARS_FMT_TABLE_HIDE_COLUMN_SEPARATOR": "1",
                "POLARS_FMT_TABLE_ROUNDED_CORNERS": "1",
                "POLARS_VERBOSE": "1",
            }.items()
        )
        assert set(initial_state.items()) != new_state_entries
        assert new_state_entries.issubset(set(cfg.state().items()))

    # expect scope-exit to restore original state
    assert pl.Config.state() == initial_state


def test_config_raise_error_if_not_exist() -> None:
    with pytest.raises(AttributeError), pl.Config(i_do_not_exist=True):
        pass


def test_config_state_env_only() -> None:
    pl.Config.set_verbose(False)
    pl.Config.set_fmt_float("full")

    state_all = pl.Config.state(env_only=False)
    state_env_only = pl.Config.state(env_only=True)
    assert len(state_env_only) < len(state_all)
    assert "set_fmt_float" in state_all
    assert "set_fmt_float" not in state_env_only


def test_activate_decimals() -> None:
    with pl.Config() as cfg:
        cfg.activate_decimals(True)
        assert os.environ.get("POLARS_ACTIVATE_DECIMAL") == "1"
        cfg.activate_decimals(False)
        assert "POLARS_ACTIVATE_DECIMAL" not in os.environ


def test_set_streaming_chunk_size() -> None:
    with pl.Config() as cfg:
        cfg.set_streaming_chunk_size(8)
        assert os.environ.get("POLARS_STREAMING_CHUNK_SIZE") == "8"

    with pytest.raises(ValueError), pl.Config() as cfg:
        cfg.set_streaming_chunk_size(0)


def test_set_fmt_str_lengths_invalid_length() -> None:
    with pl.Config() as cfg:
        with pytest.raises(ValueError):
            cfg.set_fmt_str_lengths(0)
        with pytest.raises(ValueError):
            cfg.set_fmt_str_lengths(-2)


@pytest.mark.parametrize(
    ("environment_variable", "config_setting", "value", "expected"),
    [
        ("POLARS_ACTIVATE_DECIMAL", "activate_decimals", True, "1"),
        ("POLARS_AUTO_STRUCTIFY", "set_auto_structify", True, "1"),
        ("POLARS_FMT_MAX_COLS", "set_tbl_cols", 12, "12"),
        ("POLARS_FMT_MAX_ROWS", "set_tbl_rows", 3, "3"),
        ("POLARS_FMT_STR_LEN", "set_fmt_str_lengths", 42, "42"),
        ("POLARS_FMT_TABLE_CELL_ALIGNMENT", "set_tbl_cell_alignment", "RIGHT", "RIGHT"),
        ("POLARS_FMT_TABLE_HIDE_COLUMN_NAMES", "set_tbl_hide_column_names", True, "1"),
        (
            "POLARS_FMT_TABLE_DATAFRAME_SHAPE_BELOW",
            "set_tbl_dataframe_shape_below",
            True,
            "1",
        ),
        (
            "POLARS_FMT_TABLE_FORMATTING",
            "set_ascii_tables",
            True,
            "ASCII_FULL_CONDENSED",
        ),
        (
            "POLARS_FMT_TABLE_FORMATTING",
            "set_tbl_formatting",
            "ASCII_MARKDOWN",
            "ASCII_MARKDOWN",
        ),
        (
            "POLARS_FMT_TABLE_HIDE_COLUMN_DATA_TYPES",
            "set_tbl_hide_column_data_types",
            True,
            "1",
        ),
        (
            "POLARS_FMT_TABLE_HIDE_COLUMN_SEPARATOR",
            "set_tbl_hide_dtype_separator",
            True,
            "1",
        ),
        (
            "POLARS_FMT_TABLE_HIDE_DATAFRAME_SHAPE_INFORMATION",
            "set_tbl_hide_dataframe_shape",
            True,
            "1",
        ),
        (
            "POLARS_FMT_TABLE_INLINE_COLUMN_DATA_TYPE",
            "set_tbl_column_data_type_inline",
            True,
            "1",
        ),
        ("POLARS_STREAMING_CHUNK_SIZE", "set_streaming_chunk_size", 100, "100"),
        ("POLARS_TABLE_WIDTH", "set_tbl_width_chars", 80, "80"),
        ("POLARS_VERBOSE", "set_verbose", True, "1"),
    ],
)
def test_unset_config_env_vars(
    environment_variable: str, config_setting: str, value: Any, expected: str
) -> None:
    assert environment_variable in _POLARS_CFG_ENV_VARS

    with pl.Config(**{config_setting: value}):
        assert os.environ[environment_variable] == expected

    with pl.Config(**{config_setting: None}):  # type: ignore[arg-type]
        assert environment_variable not in os.environ
