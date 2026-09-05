from datetime import datetime, timezone
from instructed_intelligence_agent import interpret_instruction

NOW = datetime(2026, 9, 3, 14, 0, 0, tzinfo=timezone.utc)


def test_low_drawdown_keywords():
    assert interpret_instruction("Focus on the safest strategies with low drawdown", NOW)["kind"] == "low_drawdown"


def test_top_performers_keywords():
    assert interpret_instruction("Give me the top 3 best performing strategies", NOW)["kind"] == "top_performers"


def test_win_rate_keywords():
    assert interpret_instruction("Which strategies have the most consistent win rate?", NOW)["kind"] == "high_win_rate"


def test_limit_extraction():
    assert interpret_instruction("Give me the top 3 best performing strategies", NOW)["limit"] == 3
    assert interpret_instruction("show me 7 strategies", NOW)["limit"] == 7
    assert interpret_instruction("no number here", NOW)["limit"] == 5


def test_strategy_id_extraction():
    result = interpret_instruction("Look at DNA_201308 and DNA_201368 for quality", NOW)
    assert result["strategy_ids"] == ["DNA_201308", "DNA_201368"]


def test_window_last_n_hours():
    result = interpret_instruction("consistent win rate over the last 3 hours", NOW)
    assert result["window_start"] == "2026-09-03T11:00:00+00:00"
    assert result["window_end"] == "2026-09-03T14:00:00+00:00"


def test_window_today():
    result = interpret_instruction("quality picks today", NOW)
    assert result["window_start"] == "2026-09-03T00:00:00+00:00"


def test_window_this_week():
    result = interpret_instruction("biggest profit this week", NOW)
    assert result["window_start"] == "2026-08-27T14:00:00+00:00"


def test_unmatched_instruction_falls_back_safely():
    result = interpret_instruction("asdkjaslkdjaslkdj nonsense text", NOW)
    assert result == {"kind": "quality", "limit": 5, "strategy_ids": [], "window_start": None, "window_end": None}


def test_never_raises_on_empty_string():
    result = interpret_instruction("", NOW)
    assert result["kind"] == "quality"
