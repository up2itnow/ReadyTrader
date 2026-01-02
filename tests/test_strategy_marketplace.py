"""
Tests for the enhanced strategy marketplace.
"""

from __future__ import annotations

import pytest

from strategy.marketplace import StrategyRegistry


@pytest.fixture
def temp_registry(tmp_path):
    """Create a temporary strategy registry."""
    db_path = str(tmp_path / "strategies.db")
    return StrategyRegistry(db_path=db_path)


class TestStrategyRegistration:
    """Test strategy registration functionality."""

    def test_register_strategy(self, temp_registry):
        """Test basic strategy registration."""
        strategy = temp_registry.register_strategy(
            name="RSI Mean Reversion",
            author="agent_zero",
            pnl=15.5,
            sharpe=1.2,
            summary="Buys oversold, sells overbought",
            config={"rsi_period": 14, "oversold": 30, "overbought": 70},
            category="mean_reversion",
            tags=["rsi", "crypto", "btc"],
        )

        assert strategy.strategy_id is not None
        assert strategy.name == "RSI Mean Reversion"
        assert strategy.author == "agent_zero"
        assert strategy.backtest_pnl_pct == 15.5
        assert strategy.category == "mean_reversion"
        assert "rsi" in strategy.tags

    def test_register_with_code(self, temp_registry):
        """Test strategy registration with code."""
        code = """
def on_candle(price, rsi, state):
    if rsi < 30:
        return 'buy'
    elif rsi > 70:
        return 'sell'
    return 'hold'
"""
        strategy = temp_registry.register_strategy(
            name="Test Strategy",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={},
            strategy_code=code,
        )

        assert strategy.strategy_code == code


class TestStrategyRetrieval:
    """Test strategy retrieval functionality."""

    def test_get_strategy(self, temp_registry):
        """Test getting a strategy by ID."""
        strategy = temp_registry.register_strategy(
            name="Test",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={},
        )

        retrieved = temp_registry.get_strategy(strategy.strategy_id)
        assert retrieved is not None
        assert retrieved.name == "Test"

    def test_get_nonexistent_strategy(self, temp_registry):
        """Test getting a nonexistent strategy."""
        assert temp_registry.get_strategy("nonexistent") is None

    def test_list_strategies(self, temp_registry):
        """Test listing strategies."""
        # Register multiple strategies
        for i in range(5):
            temp_registry.register_strategy(
                name=f"Strategy {i}",
                author="test",
                pnl=float(i * 10),
                sharpe=float(i) / 2,
                summary=f"Strategy {i}",
                config={},
            )

        strategies = temp_registry.list_strategies(limit=10)
        assert len(strategies) == 5

    def test_list_by_category(self, temp_registry):
        """Test listing strategies by category."""
        temp_registry.register_strategy(
            name="Strategy 1",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={},
            category="mean_reversion",
        )
        temp_registry.register_strategy(
            name="Strategy 2",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={},
            category="trend_following",
        )

        mr_strategies = temp_registry.list_strategies(category="mean_reversion")
        assert len(mr_strategies) == 1
        assert mr_strategies[0].category == "mean_reversion"

    def test_list_by_author(self, temp_registry):
        """Test listing strategies by author."""
        temp_registry.register_strategy(
            name="Strategy 1",
            author="alice",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={},
        )
        temp_registry.register_strategy(
            name="Strategy 2",
            author="bob",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={},
        )

        alice_strategies = temp_registry.list_strategies(author="alice")
        assert len(alice_strategies) == 1
        assert alice_strategies[0].author == "alice"

    def test_search_strategies(self, temp_registry):
        """Test searching strategies."""
        temp_registry.register_strategy(
            name="RSI Strategy",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Uses RSI indicator",
            config={},
            tags=["rsi", "momentum"],
        )
        temp_registry.register_strategy(
            name="MACD Strategy",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Uses MACD crossover",
            config={},
            tags=["macd", "trend"],
        )

        rsi_results = temp_registry.list_strategies(search="RSI")
        assert len(rsi_results) == 1
        assert "RSI" in rsi_results[0].name


class TestStrategyDownload:
    """Test strategy download functionality."""

    def test_download_increments_counter(self, temp_registry):
        """Test that download increments counter."""
        strategy = temp_registry.register_strategy(
            name="Test",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={"param": "value"},
            strategy_code="def on_candle(): pass",
        )

        assert strategy.downloads == 0

        result = temp_registry.download_strategy(strategy.strategy_id)
        assert result is not None
        assert result["strategy_code"] == "def on_candle(): pass"

        # Download again and check counter increased
        temp_registry.download_strategy(strategy.strategy_id)
        updated = temp_registry.get_strategy(strategy.strategy_id)
        assert updated.downloads == 2


class TestStrategyReviews:
    """Test strategy review functionality."""

    def test_add_review(self, temp_registry):
        """Test adding a review."""
        strategy = temp_registry.register_strategy(
            name="Test",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={},
        )

        review = temp_registry.add_review(
            strategy_id=strategy.strategy_id,
            author="reviewer",
            rating=4.5,
            comment="Great strategy!",
        )

        assert review is not None
        assert review.rating == 4.5
        assert review.comment == "Great strategy!"

    def test_review_updates_average_rating(self, temp_registry):
        """Test that reviews update average rating."""
        strategy = temp_registry.register_strategy(
            name="Test",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={},
        )

        temp_registry.add_review(strategy.strategy_id, "user1", 5.0, "Great!")
        temp_registry.add_review(strategy.strategy_id, "user2", 3.0, "Okay")

        updated = temp_registry.get_strategy(strategy.strategy_id)
        assert updated.rating == 4.0  # (5 + 3) / 2
        assert updated.rating_count == 2

    def test_get_reviews(self, temp_registry):
        """Test getting reviews for a strategy."""
        strategy = temp_registry.register_strategy(
            name="Test",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={},
        )

        temp_registry.add_review(strategy.strategy_id, "user1", 5.0, "Great!")
        temp_registry.add_review(strategy.strategy_id, "user2", 4.0, "Good")

        reviews = temp_registry.get_reviews(strategy.strategy_id)
        assert len(reviews) == 2


class TestStrategyVersioning:
    """Test strategy versioning functionality."""

    def test_update_creates_version(self, temp_registry):
        """Test that update creates version history."""
        strategy = temp_registry.register_strategy(
            name="Test",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={"v1": True},
            version="1.0.0",
        )

        updated = temp_registry.update_strategy(
            strategy_id=strategy.strategy_id,
            config={"v2": True},
            version="2.0.0",
            changelog="Updated config",
        )

        assert updated is not None
        assert updated.version == "2.0.0"


class TestCategoriesAndTags:
    """Test category and tag functionality."""

    def test_get_categories(self, temp_registry):
        """Test getting categories with counts."""
        temp_registry.register_strategy(
            name="S1",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={},
            category="mean_reversion",
        )
        temp_registry.register_strategy(
            name="S2",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={},
            category="mean_reversion",
        )
        temp_registry.register_strategy(
            name="S3",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={},
            category="trend_following",
        )

        categories = temp_registry.get_categories()
        assert len(categories) == 2

        mr_cat = next(c for c in categories if c["category"] == "mean_reversion")
        assert mr_cat["count"] == 2

    def test_get_popular_tags(self, temp_registry):
        """Test getting popular tags."""
        temp_registry.register_strategy(
            name="S1",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={},
            tags=["rsi", "btc"],
        )
        temp_registry.register_strategy(
            name="S2",
            author="test",
            pnl=10.0,
            sharpe=1.0,
            summary="Test",
            config={},
            tags=["rsi", "eth"],
        )

        tags = temp_registry.get_popular_tags()
        assert len(tags) >= 1

        # RSI should be most popular (appears in 2 strategies)
        assert tags[0]["tag"] == "rsi"
        assert tags[0]["count"] == 2
