"""
Tests for the standardized error taxonomy module.

Ensures all error classes follow consistent structure and behavior.
"""

import json

from errors import (
    AmountExceedsLimitError,
    AppError,
    ApprovalRequiredError,
    # Authentication errors
    ChainNotAllowedError,
    # Configuration errors
    ConnectionTimeoutError,
    DailyLossLimitError,
    DataFetchError,
    ErrorCategory,
    ErrorSeverity,
    ExchangeNotAllowedError,
    # Execution errors
    ExecutionModeBlockedError,
    FallingKnifeProtectionError,
    IdempotencyConflictError,
    InsufficientBalanceError,
    InternalError,
    InvalidAddressError,
    InvalidAmountError,
    InvalidAPIKeyError,
    InvalidConfigurationError,
    InvalidPriceError,
    InvalidSymbolError,
    LiveTradingDisabledError,
    # Market data errors
    MaxDrawdownError,
    MissingCredentialsError,
    # Network errors
    NoDataSourceError,
    OrderPlacementError,
    OutlierDataError,
    PermissionDeniedError,
    # Policy errors
    PositionSizeTooLargeError,
    RateLimitError,
    # Base classes
    ReadyTraderError,
    ResourceExhaustedError,
    # Risk errors
    RouterNotAllowedError,
    RPCError,
    SignatureVerificationError,
    SignerAddressNotAllowedError,
    SignerConfigurationError,
    StaleDataError,
    # System errors
    TokenNotAllowedError,
    TradingHaltedError,
    # Validation errors
    WebSocketDisconnectedError,
    # Utilities
    classify_exception,
    json_error_response,
    json_ok_response,
)


class TestReadyTraderErrorBase:
    """Test base ReadyTraderError class."""

    def test_error_creation(self):
        """Test creating a basic error."""
        error = ReadyTraderError(code="TEST_001", message="Test error message", data={"key": "value"})

        assert error.code == "TEST_001"
        assert error.message == "Test error message"
        assert error.data == {"key": "value"}
        assert error.category == ErrorCategory.SYSTEM
        assert error.severity == ErrorSeverity.HIGH

    def test_error_string_representation(self):
        """Test error string output."""
        error = ReadyTraderError(code="TEST_001", message="Test message")
        assert str(error) == "[TEST_001] Test message"

    def test_error_to_dict(self):
        """Test error dictionary conversion."""
        error = ReadyTraderError(
            code="TEST_001",
            message="Test message",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            data={"field": "value"},
            suggestion="Try this instead",
            doc_ref="docs/TEST.md",
        )

        d = error.to_dict()
        assert d["code"] == "TEST_001"
        assert d["message"] == "Test message"
        assert d["category"] == "validation"
        assert d["severity"] == "medium"
        assert d["data"] == {"field": "value"}
        assert d["suggestion"] == "Try this instead"
        assert d["doc_ref"] == "docs/TEST.md"

    def test_error_to_json(self):
        """Test error JSON serialization."""
        error = ReadyTraderError(code="TEST_001", message="Test message")
        json_str = error.to_json()
        parsed = json.loads(json_str)
        assert parsed["code"] == "TEST_001"
        assert parsed["message"] == "Test message"


class TestConfigurationErrors:
    """Test configuration-related error classes."""

    def test_missing_credentials_error(self):
        """Test MissingCredentialsError."""
        error = MissingCredentialsError(credential_name="API_KEY", env_vars=["CEX_API_KEY", "CEX_BINANCE_API_KEY"])

        assert error.code == "CONFIG_101"
        assert "API_KEY" in error.message
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.data["env_vars"] == ["CEX_API_KEY", "CEX_BINANCE_API_KEY"]
        assert error.suggestion is not None

    def test_invalid_configuration_error(self):
        """Test InvalidConfigurationError."""
        error = InvalidConfigurationError(config_name="SIGNER_TYPE", value="invalid", valid_values=["env_private_key", "keystore", "remote"])

        assert error.code == "CONFIG_102"
        assert "SIGNER_TYPE" in error.message
        assert error.data["valid_values"] == ["env_private_key", "keystore", "remote"]

    def test_signer_configuration_error(self):
        """Test SignerConfigurationError."""
        error = SignerConfigurationError(signer_type="keystore", reason="Keystore file not found")

        assert error.code == "CONFIG_103"
        assert error.severity == ErrorSeverity.CRITICAL


class TestPolicyErrors:
    """Test policy-related error classes."""

    def test_chain_not_allowed_error(self):
        """Test ChainNotAllowedError."""
        error = ChainNotAllowedError(chain="polygon", allowed_chains=["ethereum", "base", "arbitrum"])

        assert error.code == "POLICY_201"
        assert "polygon" in error.message
        assert error.data["allowed_chains"] == ["ethereum", "base", "arbitrum"]

    def test_token_not_allowed_error(self):
        """Test TokenNotAllowedError."""
        error = TokenNotAllowedError(token="SHIB", allowed_tokens=["ETH", "USDC", "BTC"])

        assert error.code == "POLICY_202"
        assert "SHIB" in error.message

    def test_exchange_not_allowed_error(self):
        """Test ExchangeNotAllowedError."""
        error = ExchangeNotAllowedError(exchange="ftx", allowed_exchanges=["binance", "kraken"])

        assert error.code == "POLICY_203"

    def test_amount_exceeds_limit_error(self):
        """Test AmountExceedsLimitError."""
        error = AmountExceedsLimitError(amount=1000.0, limit=500.0, limit_name="MAX_TRADE_AMOUNT")

        assert error.code == "POLICY_204"
        assert error.data["amount"] == 1000.0
        assert error.data["limit"] == 500.0

    def test_signer_address_not_allowed_error(self):
        """Test SignerAddressNotAllowedError."""
        error = SignerAddressNotAllowedError(address="0x1234", allowed_addresses=["0xabcd"])

        assert error.code == "POLICY_205"
        assert error.severity == ErrorSeverity.CRITICAL

    def test_router_not_allowed_error(self):
        """Test RouterNotAllowedError."""
        error = RouterNotAllowedError(router="0xbad", chain="ethereum", allowed_routers=["0x1inch"])

        assert error.code == "POLICY_206"
        assert error.severity == ErrorSeverity.CRITICAL


class TestExecutionErrors:
    """Test execution-related error classes."""

    def test_execution_mode_blocked_error(self):
        """Test ExecutionModeBlockedError."""
        error = ExecutionModeBlockedError(venue="cex", execution_mode="dex")

        assert error.code == "EXEC_301"
        assert error.severity == ErrorSeverity.MEDIUM

    def test_live_trading_disabled_error(self):
        """Test LiveTradingDisabledError."""
        error = LiveTradingDisabledError()

        assert error.code == "EXEC_302"
        assert "LIVE_TRADING_ENABLED" in error.message

    def test_trading_halted_error(self):
        """Test TradingHaltedError."""
        error = TradingHaltedError()

        assert error.code == "EXEC_303"
        assert error.severity == ErrorSeverity.CRITICAL

    def test_order_placement_error(self):
        """Test OrderPlacementError."""
        error = OrderPlacementError(exchange="binance", symbol="BTC/USDT", reason="Insufficient margin")

        assert error.code == "EXEC_304"
        assert error.data["exchange"] == "binance"

    def test_insufficient_balance_error(self):
        """Test InsufficientBalanceError."""
        error = InsufficientBalanceError(asset="USDC", required=1000.0, available=500.0)

        assert error.code == "EXEC_305"
        assert error.data["required"] == 1000.0
        assert error.data["available"] == 500.0

    def test_approval_required_error(self):
        """Test ApprovalRequiredError."""
        error = ApprovalRequiredError(request_id="req-123", expires_at=1704067200)

        assert error.code == "EXEC_306"
        assert error.severity == ErrorSeverity.LOW  # Not really an error

    def test_idempotency_conflict_error(self):
        """Test IdempotencyConflictError."""
        error = IdempotencyConflictError(idempotency_key="order-123", previous_result={"order_id": "abc"})

        assert error.code == "EXEC_307"
        assert error.severity == ErrorSeverity.LOW


class TestMarketDataErrors:
    """Test market data error classes."""

    def test_stale_data_error(self):
        """Test StaleDataError."""
        error = StaleDataError(symbol="BTC/USDT", age_ms=60000, max_age_ms=30000)

        assert error.code == "DATA_401"
        assert error.data["age_ms"] == 60000

    def test_data_fetch_error(self):
        """Test DataFetchError."""
        error = DataFetchError(symbol="ETH/USDT", source="binance", reason="Connection refused")

        assert error.code == "DATA_402"

    def test_outlier_data_error(self):
        """Test OutlierDataError."""
        error = OutlierDataError(symbol="BTC/USDT", value=1000000.0, expected_range=(90000.0, 110000.0))

        assert error.code == "DATA_403"

    def test_no_data_source_error(self):
        """Test NoDataSourceError."""
        error = NoDataSourceError(symbol="UNKNOWN/USDT")

        assert error.code == "DATA_404"


class TestNetworkErrors:
    """Test network error classes."""

    def test_connection_timeout_error(self):
        """Test ConnectionTimeoutError."""
        error = ConnectionTimeoutError(endpoint="https://api.binance.com", timeout_sec=30.0)

        assert error.code == "NET_501"
        assert error.data["timeout_sec"] == 30.0

    def test_websocket_disconnected_error(self):
        """Test WebSocketDisconnectedError."""
        error = WebSocketDisconnectedError(exchange="binance", reason="Server closed connection")

        assert error.code == "NET_502"
        assert error.severity == ErrorSeverity.MEDIUM  # Auto-recoverable

    def test_rpc_error(self):
        """Test RPCError."""
        error = RPCError(chain="ethereum", method="eth_sendRawTransaction", error_code=-32000, error_message="replacement transaction underpriced")

        assert error.code == "NET_503"
        assert error.data["error_code"] == -32000


class TestAuthenticationErrors:
    """Test authentication error classes."""

    def test_invalid_api_key_error(self):
        """Test InvalidAPIKeyError."""
        error = InvalidAPIKeyError(exchange="binance")

        assert error.code == "AUTH_601"
        assert error.severity == ErrorSeverity.CRITICAL

    def test_permission_denied_error(self):
        """Test PermissionDeniedError."""
        error = PermissionDeniedError(exchange="kraken", operation="withdraw")

        assert error.code == "AUTH_602"

    def test_signature_verification_error(self):
        """Test SignatureVerificationError."""
        error = SignatureVerificationError(reason="Invalid signature length")

        assert error.code == "AUTH_603"
        assert error.severity == ErrorSeverity.CRITICAL


class TestValidationErrors:
    """Test validation error classes."""

    def test_invalid_symbol_error(self):
        """Test InvalidSymbolError."""
        error = InvalidSymbolError(symbol="INVALID", exchange="binance")

        assert error.code == "VAL_701"
        assert error.severity == ErrorSeverity.MEDIUM

    def test_invalid_amount_error(self):
        """Test InvalidAmountError."""
        error = InvalidAmountError(amount=-1.0, reason="Amount must be positive")

        assert error.code == "VAL_702"

    def test_invalid_price_error(self):
        """Test InvalidPriceError."""
        error = InvalidPriceError(price=0.0, reason="Price must be > 0 for limit orders")

        assert error.code == "VAL_703"

    def test_invalid_address_error(self):
        """Test InvalidAddressError."""
        error = InvalidAddressError(address="0xabc", expected_format="40 hex characters")

        assert error.code == "VAL_704"


class TestSystemErrors:
    """Test system error classes."""

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        error = RateLimitError(key="binance:orders", limit=10, window_seconds=60, current_count=15)

        assert error.code == "SYS_801"
        assert error.severity == ErrorSeverity.MEDIUM

    def test_resource_exhausted_error(self):
        """Test ResourceExhaustedError."""
        error = ResourceExhaustedError(resource="memory", limit="4GB")

        assert error.code == "SYS_802"
        assert error.severity == ErrorSeverity.CRITICAL

    def test_internal_error(self):
        """Test InternalError."""
        error = InternalError(component="backtest_engine", reason="Division by zero")

        assert error.code == "SYS_803"


class TestRiskErrors:
    """Test risk management error classes."""

    def test_position_size_too_large_error(self):
        """Test PositionSizeTooLargeError."""
        error = PositionSizeTooLargeError(position_pct=0.08, max_pct=0.05)

        assert error.code == "RISK_901"
        assert "8.0%" in error.message

    def test_daily_loss_limit_error(self):
        """Test DailyLossLimitError."""
        error = DailyLossLimitError(daily_loss_pct=-0.06, limit_pct=-0.05)

        assert error.code == "RISK_902"

    def test_max_drawdown_error(self):
        """Test MaxDrawdownError."""
        error = MaxDrawdownError(drawdown_pct=0.12, limit_pct=0.10)

        assert error.code == "RISK_903"
        assert error.severity == ErrorSeverity.CRITICAL

    def test_falling_knife_protection_error(self):
        """Test FallingKnifeProtectionError."""
        error = FallingKnifeProtectionError(sentiment_score=-0.7, threshold=-0.5)

        assert error.code == "RISK_904"
        assert error.severity == ErrorSeverity.MEDIUM


class TestExceptionClassification:
    """Test the classify_exception utility."""

    def test_classify_ready_trader_error(self):
        """Test that ReadyTraderError passes through."""
        original = InvalidSymbolError(symbol="TEST", exchange="test")
        classified = classify_exception(original)
        assert classified is original

    def test_classify_ccxt_auth_error(self):
        """Test CCXT AuthenticationError classification."""
        import ccxt

        error = ccxt.AuthenticationError("Invalid API key")
        classified = classify_exception(error)
        assert classified.code == "AUTH_601"

    def test_classify_ccxt_network_error(self):
        """Test CCXT NetworkError classification."""
        import ccxt

        error = ccxt.NetworkError("Connection failed")
        classified = classify_exception(error)
        assert classified.code == "NET_501"

    def test_classify_ccxt_bad_symbol(self):
        """Test CCXT BadSymbol classification."""
        import ccxt

        error = ccxt.BadSymbol("Invalid symbol")
        classified = classify_exception(error)
        assert isinstance(classified, InvalidSymbolError)

    def test_classify_unknown_error(self):
        """Test unknown exception classification."""
        error = RuntimeError("Something unexpected")
        classified = classify_exception(error)
        assert classified.code == "SYS_803"


class TestJsonResponses:
    """Test JSON response utilities."""

    def test_json_error_response(self):
        """Test json_error_response utility."""
        error = InvalidSymbolError(symbol="TEST", exchange="test")
        response = json_error_response(error)

        assert response["ok"] is False
        assert response["error"]["code"] == "VAL_701"
        assert "message" in response["error"]

    def test_json_ok_response(self):
        """Test json_ok_response utility."""
        response = json_ok_response({"result": "success"})

        assert response["ok"] is True
        assert response["data"]["result"] == "success"

    def test_json_ok_response_empty(self):
        """Test json_ok_response with no data."""
        response = json_ok_response()

        assert response["ok"] is True
        assert response["data"] == {}


class TestLegacyAppError:
    """Test backward compatibility with AppError."""

    def test_app_error_compatibility(self):
        """Test that AppError still works."""
        error = AppError("legacy_error", "Legacy message", {"key": "value"})

        assert error.code == "legacy_error"
        assert error.message == "Legacy message"
        assert error.data == {"key": "value"}
        assert isinstance(error, ReadyTraderError)
