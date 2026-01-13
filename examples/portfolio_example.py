"""
Example usage of the portfolio tracking system.

This demonstrates how to:
1. Initialize the database
2. Create a portfolio
3. Record trades
4. Update positions with current prices
5. Get portfolio summary
6. Reset a portfolio (clear all data)
"""

import asyncio
from decimal import Decimal

from polymarket_bot.portfolio import (
    MarketType,
    PortfolioService,
    PositionSide,
    TransactionType,
    init_db,
)


def example_polymarket_portfolio():
    """Example: Track Polymarket prediction market positions."""
    print("\n=== Polymarket Portfolio Example ===\n")

    # Initialize database (creates tables if they don't exist)
    init_db()

    # Use the portfolio service
    with PortfolioService() as portfolio_service:
        # Create or get portfolio
        portfolio = portfolio_service.ensure_portfolio(
            name="polymarket_main",
            market_type=MarketType.PREDICTION,
            exchange="polymarket",
            wallet_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
            currency="USDC",
        )

        print(f"Portfolio created: {portfolio.name} (ID: {portfolio.id})")

        # Add initial funds
        portfolio_service.add_funds(portfolio, Decimal("1000.0000"), notes="Initial deposit")
        print(f"Added funds. Cash balance: ${portfolio.cash_balance}")

        # Record a BUY trade (betting YES on a market)
        position1, tx1 = portfolio_service.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset_id="token_12345_yes",
            asset_name="Will Bitcoin hit $100k by EOY - YES",
            market_id="condition_12345",
            market_question="Will Bitcoin hit $100,000 by end of 2025?",
            quantity=Decimal("100"),  # 100 YES tokens
            price=Decimal("0.65"),  # $0.65 per token
            fee=Decimal("0.50"),  # $0.50 fee
            side=PositionSide.LONG,
            external_order_id="order_abc123",
        )
        print(f"\n✓ Bought {position1.quantity} YES tokens at ${position1.average_entry_price}")
        print(f"  Total cost: ${position1.total_cost}")

        # Record another BUY trade (betting NO on different market)
        position2, tx2 = portfolio_service.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset_id="token_67890_no",
            asset_name="Will inflation exceed 5% - NO",
            market_id="condition_67890",
            market_question="Will US inflation exceed 5% in Q4 2025?",
            quantity=Decimal("200"),
            price=Decimal("0.30"),
            fee=Decimal("0.40"),
            side=PositionSide.LONG,
        )
        print(f"✓ Bought {position2.quantity} NO tokens at ${position2.average_entry_price}")

        # Update prices (simulating market movement)
        print("\n--- Updating prices (market moved) ---")
        current_prices = {
            "token_12345_yes": Decimal("0.72"),  # Price went up (profitable!)
            "token_67890_no": Decimal("0.28"),  # Price went down (losing)
        }

        portfolio = portfolio_service.update_position_prices(portfolio, current_prices)

        # Get portfolio summary
        summary = portfolio_service.get_portfolio_summary(portfolio)
        print_summary(summary)

        # Sell some tokens (take profit)
        print("\n--- Selling 50 YES tokens (taking partial profit) ---")
        position1, tx3 = portfolio_service.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.SELL,
            asset_id="token_12345_yes",
            quantity=Decimal("50"),
            price=Decimal("0.72"),
            fee=Decimal("0.25"),
        )

        # Update prices again
        portfolio = portfolio_service.update_position_prices(portfolio, current_prices)
        summary = portfolio_service.get_portfolio_summary(portfolio)
        print_summary(summary)


def example_crypto_portfolio():
    """Example: Track crypto spot trading positions."""
    print("\n\n=== Crypto Portfolio Example ===\n")

    init_db()

    with PortfolioService() as portfolio_service:
        # Create crypto portfolio
        portfolio = portfolio_service.ensure_portfolio(
            name="binance_spot",
            market_type=MarketType.CRYPTO,
            exchange="binance",
            account_id="user_12345",
            currency="USDT",
        )

        print(f"Portfolio created: {portfolio.name}")

        # Add funds
        portfolio_service.add_funds(portfolio, Decimal("10000.00"), notes="Trading capital")
        print(f"Added ${portfolio.cash_balance} USDT")

        # Buy BTC
        position_btc, _ = portfolio_service.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset_id="BTC",
            asset_name="Bitcoin",
            quantity=Decimal("0.5"),
            price=Decimal("45000.00"),
            fee=Decimal("11.25"),  # 0.05% fee
            side=PositionSide.LONG,
        )
        print(f"\n✓ Bought {position_btc.quantity} BTC at ${position_btc.average_entry_price}")

        # Buy ETH
        position_eth, _ = portfolio_service.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset_id="ETH",
            asset_name="Ethereum",
            quantity=Decimal("10.0"),
            price=Decimal("2500.00"),
            fee=Decimal("12.50"),
            side=PositionSide.LONG,
        )
        print(f"✓ Bought {position_eth.quantity} ETH at ${position_eth.average_entry_price}")

        # Update with current market prices
        print("\n--- Market update (prices changed) ---")
        current_prices = {
            "BTC": Decimal("47000.00"),  # +4.44%
            "ETH": Decimal("2450.00"),   # -2%
        }

        portfolio = portfolio_service.update_position_prices(portfolio, current_prices)
        summary = portfolio_service.get_portfolio_summary(portfolio)
        print_summary(summary)


def example_multi_market():
    """Example: Track positions across multiple markets."""
    print("\n\n=== Multi-Market Portfolio Example ===\n")

    init_db()

    with PortfolioService() as portfolio_service:
        # Create multiple portfolios for different exchanges
        poly = portfolio_service.ensure_portfolio(
            name="polymarket_account",
            market_type=MarketType.PREDICTION,
            exchange="polymarket",
        )

        binance = portfolio_service.ensure_portfolio(
            name="binance_account",
            market_type=MarketType.CRYPTO,
            exchange="binance",
        )

        # Fund both accounts
        portfolio_service.add_funds(poly, Decimal("5000"))
        portfolio_service.add_funds(binance, Decimal("10000"))

        print(f"Polymarket: ${poly.cash_balance}")
        print(f"Binance: ${binance.cash_balance}")

        # Trade on both
        portfolio_service.record_trade(
            portfolio=poly,
            transaction_type=TransactionType.BUY,
            asset_id="election_yes",
            asset_name="Election Outcome - YES",
            quantity=Decimal("1000"),
            price=Decimal("0.55"),
            fee=Decimal("0.50"),
        )

        portfolio_service.record_trade(
            portfolio=binance,
            transaction_type=TransactionType.BUY,
            asset_id="BTC",
            asset_name="Bitcoin",
            quantity=Decimal("0.2"),
            price=Decimal("46000"),
            fee=Decimal("9.20"),
        )

        # Update prices
        portfolio_service.update_position_prices(poly, {"election_yes": Decimal("0.60")})
        portfolio_service.update_position_prices(binance, {"BTC": Decimal("47500")})

        print("\n--- Polymarket Summary ---")
        print_summary(portfolio_service.get_portfolio_summary(poly))

        print("\n--- Binance Summary ---")
        print_summary(portfolio_service.get_portfolio_summary(binance))


def example_reset_portfolio():
    """Example: Reset a portfolio to clear all data."""
    print("\n\n=== Reset Portfolio Example ===\n")

    init_db()

    with PortfolioService() as portfolio_service:
        # Create a test portfolio
        portfolio = portfolio_service.ensure_portfolio(
            name="test_reset_portfolio",
            market_type=MarketType.PREDICTION,
            exchange="polymarket",
        )

        print(f"Portfolio created: {portfolio.name}")

        # Add funds and make some trades
        portfolio_service.add_funds(portfolio, Decimal("1000.00"))
        print(f"Added funds: ${portfolio.cash_balance}")

        # Make some trades
        portfolio_service.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset_id="token_test_1",
            asset_name="Test Market 1 - YES",
            quantity=Decimal("100"),
            price=Decimal("0.60"),
            fee=Decimal("0.50"),
        )

        portfolio_service.record_trade(
            portfolio=portfolio,
            transaction_type=TransactionType.BUY,
            asset_id="token_test_2",
            asset_name="Test Market 2 - NO",
            quantity=Decimal("50"),
            price=Decimal("0.40"),
            fee=Decimal("0.25"),
        )

        # Show portfolio state before reset
        print("\n--- Before Reset ---")
        summary = portfolio_service.get_portfolio_summary(portfolio)
        print(f"Cash Balance: ${summary['cash_balance']:.2f}")
        print(f"Open Positions: {summary['open_positions_count']}")
        print(f"Total Transactions: {summary['total_transactions']}")

        # Reset the portfolio
        print("\n⚠️  Resetting portfolio (clearing all data)...")
        portfolio_service.reset_portfolio(portfolio)

        # Show portfolio state after reset
        print("\n--- After Reset ---")
        summary = portfolio_service.get_portfolio_summary(portfolio)
        print(f"Cash Balance: ${summary['cash_balance']:.2f}")
        print(f"Open Positions: {summary['open_positions_count']}")
        print(f"Total Transactions: {summary['total_transactions']}")
        print("\n✓ Portfolio reset complete - all data cleared!")


def print_summary(summary: dict):
    """Pretty print portfolio summary."""
    print(f"\n{'='*60}")
    print(f"Portfolio: {summary['name']} ({summary['exchange']})")
    print(f"{'='*60}")
    print(f"Cash Balance:     ${summary['cash_balance']:>12,.2f}")
    print(f"Total Value:      ${summary['total_value']:>12,.2f}")
    print(f"Unrealized P&L:   ${summary['unrealized_pnl']:>12,.2f}")
    print(f"Realized P&L:     ${summary['realized_pnl']:>12,.2f}")
    print(f"Total P&L:        ${summary['total_pnl']:>12,.2f}")
    print(f"\nOpen Positions: {summary['open_positions_count']}")

    if summary['positions']:
        print(f"\n{'Asset':<30} {'Qty':>12} {'Entry':>12} {'Current':>12} {'P&L':>12} {'%':>8}")
        print("-" * 95)
        for pos in summary['positions']:
            pnl = pos['unrealized_pnl'] or 0
            pnl_pct = pos['pnl_percent'] or 0
            current = pos['current_price'] or 0

            pnl_color = "+" if pnl >= 0 else ""
            print(
                f"{pos['asset_name'][:30]:<30} "
                f"{pos['quantity']:>12.4f} "
                f"${pos['entry_price']:>11.4f} "
                f"${current:>11.4f} "
                f"{pnl_color}${pnl:>10.2f} "
                f"{pnl_color}{pnl_pct:>7.2f}%"
            )

    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Run examples
    example_polymarket_portfolio()
    example_crypto_portfolio()
    example_multi_market()
    example_reset_portfolio()

    print("\n✅ All examples completed!")
    print(f"📊 Database saved to: ./data/portfolio.db")
    print(f"💡 You can inspect it with: sqlite3 data/portfolio.db")
