import importlib
import json
import logging
import os
import sqlite3
import urllib.error
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

# Ensure environment variable is set for module import
os.environ.setdefault("CORE_API_KEY", "test-api-key")

import loan.settlement
from loan.repository import ContractRepository
from loan.settlement import PENALTY_RATE, send_quote, settlement_quote


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE contracts (contract_no TEXT, principal INT, annual_rate TEXT, tenor_months INT)")
    conn.execute("INSERT INTO contracts VALUES ('K-001', 12000000, '0.12', 12)")
    return conn


def test_quote(db_conn):
    result = settlement_quote(ContractRepository(db_conn), "K-001", 3)
    assert result == 9_180_000
    assert isinstance(result, int)
    assert not isinstance(result, float)


def test_quote_returns_integer_rupiah_with_rounding(db_conn):
    # principal 75, 1 month tenor, 0 months paid -> remaining = 75
    # 75 * 1.02 = 76.50 -> ROUND_HALF_UP rounds to 77
    db_conn.execute("INSERT INTO contracts VALUES ('K-ODD', 75, '0.10', 1)")
    result = settlement_quote(ContractRepository(db_conn), "K-ODD", 0)
    assert result == 77
    assert isinstance(result, int)
    assert not isinstance(result, float)


def test_penalty_rate_is_decimal():
    assert isinstance(PENALTY_RATE, Decimal)
    assert PENALTY_RATE == Decimal("0.02")


def test_repository_parameterized_query_prevents_sql_injection(db_conn):
    repo = ContractRepository(db_conn)
    # If the query were vulnerable to SQL injection, 'NONEXISTENT' OR '1'='1' would match K-001
    assert repo.find("NONEXISTENT' OR '1'='1") is None


def test_repository_find_not_found_returns_none(db_conn):
    repo = ContractRepository(db_conn)
    assert repo.find("DOES-NOT-EXIST") is None


def test_quote_contract_not_found_raises_value_error(db_conn):
    repo = ContractRepository(db_conn)
    with pytest.raises(ValueError, match="contract not found"):
        settlement_quote(repo, "DOES-NOT-EXIST", 1)


def test_missing_core_api_key_fails_at_startup(monkeypatch):
    monkeypatch.delenv("CORE_API_KEY", raising=False)
    with pytest.raises(KeyError):
        importlib.reload(loan.settlement)

    monkeypatch.setenv("CORE_API_KEY", "test-api-key")
    importlib.reload(loan.settlement)


def test_send_quote_does_not_log_api_key(caplog):
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        with caplog.at_level(logging.INFO):
            send_quote("K-001", 9_180_000)

    assert "test-api-key" not in caplog.text
    assert "sending quote for K-001" in caplog.text


def test_send_quote_sets_timeout_and_checks_status():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        send_quote("K-001", 9_180_000)

        assert mock_urlopen.call_count == 1
        req, kwargs = mock_urlopen.call_args
        assert kwargs.get("timeout") == 10

        actual_req = req[0]
        assert actual_req.full_url == "https://core-banking.internal/quotes"
        assert actual_req.headers["Authorization"] == "Bearer test-api-key"
        assert json.loads(actual_req.data.decode("utf-8")) == {"contract_no": "K-001", "amount": 9_180_000}


def test_send_quote_raises_on_connection_error():
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        with pytest.raises(urllib.error.URLError):
            send_quote("K-001", 9_180_000)


def test_send_quote_raises_on_non_2xx_status():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.status = 500
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        with pytest.raises(RuntimeError, match="status: 500"):
            send_quote("K-001", 9_180_000)
