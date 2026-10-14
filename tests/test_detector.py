import pytest
from scamshield.detector import is_scam


def test_detect_keyword():
    assert is_scam("Congratulations, you are a winner of a prize")


def test_safe_text():
    assert not is_scam("Hello friend, let's catch up this weekend")


def test_short_link():
    assert is_scam("Check this out: https://bit.ly/abc123")
