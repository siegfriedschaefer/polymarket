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

        summary = portfolio_service.get_portfolio_summary(portfolio)
        print_summary(summary)

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

        # Reset the portfolio
        print("\n⚠️  Resetting portfolio (clearing all data)...")
        portfolio_service.reset_portfolio(portfolio)
        summary = portfolio_service.get_portfolio_summary(portfolio)
        print_summary(summary)



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

    print("\n✅ All examples completed!")
    print(f"📊 Database saved to: ./data/portfolio.db")
    print(f"💡 You can inspect it with: sqlite3 data/portfolio.db")
