"""Tests for portfolio tracking system."""

from decimal import Decimal

import pytest

from polymarket_bot.portfolio import (
    MarketType,
    Portfolio,
    PortfolioService,
    PositionSide,
    TransactionType,
    init_db,
)
from polymarket_bot.portfolio.database import drop_db


@pytest.fixture
def clean_db():
    """Provide a clean test database."""
    # Use in-memory SQLite for tests
    import os
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

    init_db()
    yield
    drop_db()


def test_create_portfolio(clean_db):
    """Test portfolio creation."""
    with PortfolioService() as ps:
        portfolio = ps.ensure_portfolio(
            name="test_portfolio",
            market_type=MarketType.PREDICTION,
            exchange="polymarket",
        )

        assert portfolio.id is not None
        assert portfolio.name == "test_portfolio"
        assert portfolio.market_type == MarketType.PREDICTION.value
        assert portfolio.cash_balance == Decimal(0)


def test_add_funds(clean_db):
    """Test adding funds to portfolio."""
    with PortfolioService() as ps:
        portfolio = ps.ensure_portfolio(
            name="test_portfolio",
            market_type=MarketType.CRYPTO,
            exchange="binance",
        )

        ps.add_funds(portfolio, Decimal("1000.00"))

        assert portfolio.cash_balance == Decimal("1000.00")


def test_record_buy_trade(clean_db):
    """Test recording a buy trade."""
    with PortfolioService() as ps:
        portfolio = ps.ensure_portfolio(
            name="test_portfolio",
            market_type=MarketType.PREDICTION,
            exchange="polymarket",
        )

        ps.add_funds(portfolio, Decimal("1000.00"))

        position, transaction = ps.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset_id="token_yes_123",
            asset_name="Test Market - YES",
            quantity=Decimal("100"),
            price=Decimal("0.65"),
            fee=Decimal("0.50"),
        )

        # Check position
        assert position.asset_id == "token_yes_123"
        assert position.quantity == Decimal("100")
        assert position.average_entry_price == Decimal("0.65")
        assert position.total_cost == Decimal("65.50")  # 100 * 0.65 + 0.50
        assert position.is_open is True

        # Check transaction
        assert transaction.transaction_type == TransactionType.BUY.value
        assert transaction.quantity == Decimal("100")
        assert transaction.price == Decimal("0.65")
        assert transaction.fee == Decimal("0.50")

        # Check portfolio cash
        assert portfolio.cash_balance == Decimal("934.50")  # 1000 - 65.50


def test_update_position_prices(clean_db):
    """Test updating position prices and calculating P&L."""
    with PortfolioService() as ps:
        portfolio = ps.ensure_portfolio(
            name="test_portfolio",
            market_type=MarketType.CRYPTO,
            exchange="binance",
        )

        ps.add_funds(portfolio, Decimal("10000.00"))

        # Buy BTC
        position, _ = ps.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset_id="BTC",
            quantity=Decimal("0.5"),
            price=Decimal("45000.00"),
            fee=Decimal("11.25"),
        )

        # Update price (profit)
        prices = {"BTC": Decimal("47000.00")}
        portfolio = ps.update_position_prices(portfolio, prices)

        # Refresh position from DB
        ps.db.refresh(position)

        # Check P&L calculation
        assert position.current_price == Decimal("47000.00")
        assert position.current_value == Decimal("23500.00")  # 0.5 * 47000
        # Total cost was 22511.25 (0.5 * 45000 + 11.25)
        # Unrealized P&L = 23500 - 22511.25 = 988.75
        assert position.unrealized_pnl == Decimal("988.75")


def test_sell_trade_partial(clean_db):
    """Test selling part of a position."""
    with PortfolioService() as ps:
        portfolio = ps.ensure_portfolio(
            name="test_portfolio",
            market_type=MarketType.PREDICTION,
            exchange="polymarket",
        )

        ps.add_funds(portfolio, Decimal("1000.00"))

        # Buy 100 tokens
        position, _ = ps.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset_id="token_yes",
            quantity=Decimal("100"),
            price=Decimal("0.60"),
            fee=Decimal("0.50"),
        )

        # Sell 50 tokens
        position, _ = ps.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.SELL,
            asset_id="token_yes",
            quantity=Decimal("50"),
            price=Decimal("0.70"),
            fee=Decimal("0.25"),
        )

        # Position should still be open with 50 tokens
        assert position.is_open is True
        assert position.quantity == Decimal("50")


def test_sell_trade_full_close(clean_db):
    """Test selling entire position (closing)."""
    with PortfolioService() as ps:
        portfolio = ps.ensure_portfolio(
            name="test_portfolio",
            market_type=MarketType.PREDICTION,
            exchange="polymarket",
        )

        ps.add_funds(portfolio, Decimal("1000.00"))

        # Buy 100 tokens at $0.60
        position, _ = ps.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset_id="token_yes",
            quantity=Decimal("100"),
            price=Decimal("0.60"),
            fee=Decimal("0.50"),
        )

        initial_cash = portfolio.cash_balance

        # Sell all 100 tokens at $0.70 (profit)
        position, _ = ps.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.SELL,
            asset_id="token_yes",
            quantity=Decimal("100"),
            price=Decimal("0.70"),
            fee=Decimal("0.25"),
        )

        # Position should be closed
        assert position.is_open is False
        assert position.closed_at is not None
        assert position.quantity == Decimal("0")

        # Check realized P&L
        # Sold for: 100 * 0.70 = 70, minus fee 0.25 = 69.75
        # Cost: 100 * 0.60 = 60 (entry) + 0.50 (buy fee) = 60.50
        # Realized P&L: 70 - 60 - 0.25 (sell fee) = 9.75
        assert portfolio.realized_pnl == Decimal("9.75")


def test_portfolio_summary(clean_db):
    """Test portfolio summary generation."""
    with PortfolioService() as ps:
        portfolio = ps.ensure_portfolio(
            name="test_portfolio",
            market_type=MarketType.CRYPTO,
            exchange="binance",
        )

        ps.add_funds(portfolio, Decimal("10000.00"))

        # Open two positions
        ps.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset_id="BTC",
            asset_name="Bitcoin",
            quantity=Decimal("0.5"),
            price=Decimal("45000.00"),
            fee=Decimal("11.25"),
        )

        ps.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset_id="ETH",
            asset_name="Ethereum",
            quantity=Decimal("10"),
            price=Decimal("2500.00"),
            fee=Decimal("12.50"),
        )

        # Update prices
        prices = {
            "BTC": Decimal("47000.00"),
            "ETH": Decimal("2450.00"),
        }
        portfolio = ps.update_position_prices(portfolio, prices)

        # Get summary
        summary = ps.get_portfolio_summary(portfolio)

        assert summary["name"] == "test_portfolio"
        assert summary["open_positions_count"] == 2
        assert len(summary["positions"]) == 2
        assert summary["total_transactions"] == 3  # 1 deposit + 2 buys


def test_multiple_portfolios(clean_db):
    """Test managing multiple portfolios."""
    with PortfolioService() as ps:
        poly = ps.ensure_portfolio(
            name="polymarket",
            market_type=MarketType.PREDICTION,
            exchange="polymarket",
        )

        binance = ps.ensure_portfolio(
            name="binance",
            market_type=MarketType.CRYPTO,
            exchange="binance",
        )

        assert poly.id != binance.id
        assert poly.market_type != binance.market_type


def test_insufficient_funds(clean_db):
    """Test withdrawal with insufficient funds."""
    with PortfolioService() as ps:
        portfolio = ps.ensure_portfolio(
            name="test_portfolio",
            market_type=MarketType.PREDICTION,
            exchange="polymarket",
        )

        ps.add_funds(portfolio, Decimal("100.00"))

        with pytest.raises(ValueError, match="Insufficient funds"):
            ps.withdraw_funds(portfolio, Decimal("200.00"))


def test_sell_without_position(clean_db):
    """Test selling without an open position."""
    with PortfolioService() as ps:
        portfolio = ps.ensure_portfolio(
            name="test_portfolio",
            market_type=MarketType.PREDICTION,
            exchange="polymarket",
        )

        ps.add_funds(portfolio, Decimal("1000.00"))

        with pytest.raises(ValueError, match="no open position"):
            ps.record_trade(
                portfolio=portfolio,
                transaction_type=TransactionType.SELL,
                asset_id="token_nonexistent",
                quantity=Decimal("100"),
                price=Decimal("0.60"),
            )


def test_reset_portfolio(clean_db):
    """Test resetting portfolio to initial state."""
    with PortfolioService() as ps:
        portfolio = ps.ensure_portfolio(
            name="test_portfolio",
            market_type=MarketType.PREDICTION,
            exchange="polymarket",
        )

        # Add funds and create positions
        ps.add_funds(portfolio, Decimal("1000.00"))

        # Buy some tokens
        ps.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset_id="token_yes",
            asset_name="Market YES",
            quantity=Decimal("100"),
            price=Decimal("0.60"),
            fee=Decimal("0.50"),
        )

        ps.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset_id="token_no",
            asset_name="Market NO",
            quantity=Decimal("50"),
            price=Decimal("0.40"),
            fee=Decimal("0.25"),
        )

        # Verify portfolio has data
        summary = ps.get_portfolio_summary(portfolio)
        assert summary["open_positions_count"] == 2
        assert summary["total_transactions"] == 3  # 1 deposit + 2 buys
        assert portfolio.cash_balance > Decimal("0")

        # Reset portfolio
        ps.reset_portfolio(portfolio)

        # Verify everything is cleared
        assert portfolio.cash_balance == Decimal("0")
        assert portfolio.total_value == Decimal("0")
        assert portfolio.unrealized_pnl == Decimal("0")
        assert portfolio.realized_pnl == Decimal("0")

        # Verify no positions remain
        summary = ps.get_portfolio_summary(portfolio)
        assert summary["open_positions_count"] == 0
        assert summary["total_transactions"] == 0
        assert len(summary["positions"]) == 0
