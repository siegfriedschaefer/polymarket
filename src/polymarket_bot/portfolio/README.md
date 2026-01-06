# Portfolio Tracking System

Market-agnostic portfolio tracking system for managing positions across different asset types and exchanges.

## Features

- **Market Agnostic**: Works with prediction markets (Polymarket), crypto, forex, stocks
- **Persistent State**: SQLAlchemy-based storage survives restarts
- **Complete Audit Trail**: All transactions recorded with timestamps
- **Real-time P&L**: Track unrealized and realized profits/losses
- **Multi-Portfolio**: Manage multiple accounts/exchanges separately
- **Flexible**: Extensible for any asset type

## Quick Start

### Installation

```bash
pip install sqlalchemy>=2.0.0
```

### Initialize Database

```python
from polymarket_bot.portfolio import init_db

# Creates tables if they don't exist
init_db()
```

### Basic Usage

```python
from decimal import Decimal
from polymarket_bot.portfolio import (
    PortfolioService,
    MarketType,
    TransactionType,
    PositionSide
)

# Use context manager for automatic session handling
with PortfolioService() as ps:
    # Create portfolio
    portfolio = ps.ensure_portfolio(
        name="my_polymarket",
        market_type=MarketType.PREDICTION,
        exchange="polymarket",
        wallet_address="0x...",
    )

    # Add funds
    ps.add_funds(portfolio, Decimal("1000.00"))

    # Record a trade
    position, tx = ps.record_trade(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset_id="token_yes_123",
        asset_name="Will BTC hit $100k - YES",
        quantity=Decimal("100"),
        price=Decimal("0.65"),
        fee=Decimal("0.50"),
    )

    # Update with current prices
    prices = {"token_yes_123": Decimal("0.72")}
    portfolio = ps.update_position_prices(portfolio, prices)

    # Get summary
    summary = ps.get_portfolio_summary(portfolio)
    print(f"Total Value: ${summary['total_value']}")
    print(f"Unrealized P&L: ${summary['unrealized_pnl']}")
```

## Data Model

### Portfolio
Main account container holding cash and positions.

```python
- id: Primary key
- name: Unique portfolio name
- market_type: prediction/crypto/forex/stock
- exchange: Exchange/platform name
- cash_balance: Available cash
- total_value: Cash + position values
- unrealized_pnl: Open position P&L
- realized_pnl: Closed position P&L
```

### Position
Individual holdings in assets/markets.

```python
- id: Primary key
- portfolio_id: Parent portfolio
- asset_id: Asset identifier (token ID, ticker)
- asset_name: Human-readable name
- market_id: External market ID
- side: LONG or SHORT
- quantity: Amount held
- average_entry_price: Cost basis
- current_price: Latest price
- unrealized_pnl: Current P&L
- is_open: Position status
```

### Transaction
Audit trail of all activities.

```python
- id: Primary key
- portfolio_id: Parent portfolio
- position_id: Related position (nullable)
- transaction_type: buy/sell/deposit/withdrawal/fee/settlement
- asset_id: Asset identifier
- quantity: Amount
- price: Price per unit
- amount: Total value
- fee: Transaction fee
- external_id: Exchange order ID
```

## API Reference

### PortfolioService

#### `ensure_portfolio(name, market_type, exchange, **kwargs) -> Portfolio`
Get or create a portfolio.

#### `record_trade(portfolio, transaction_type, asset_id, quantity, price, **kwargs) -> (Position, Transaction)`
Record a buy or sell trade.

#### `update_position_prices(portfolio, prices: dict) -> Portfolio`
Update current prices and recalculate P&L.

#### `get_portfolio_summary(portfolio) -> dict`
Get complete portfolio statistics.

#### `add_funds(portfolio, amount) -> Transaction`
Deposit cash to portfolio.

#### `withdraw_funds(portfolio, amount) -> Transaction`
Withdraw cash from portfolio.

## Integration with Polymarket Client

The `PolymarketClient` automatically initializes portfolio tracking:

```python
from polymarket_bot.api.client import get_client

# Get client (portfolio tracking enabled by default)
client = get_client()

# Get positions from local database
positions = await client.get_positions()
print(positions)
```

Disable portfolio tracking:

```python
client = PolymarketClient(enable_portfolio_tracking=False)
```

## Examples

See `examples/portfolio_example.py` for complete examples:

```bash
cd /Users/siggis/projects/claude/polymarket
PYTHONPATH=src python3 examples/portfolio_example.py
```

This demonstrates:
- Polymarket prediction market positions
- Crypto spot trading positions
- Multi-market portfolio management
- P&L calculations
- Position lifecycle (open, update, close)

## Database Location

By default, SQLite database is stored at:
```
./data/portfolio.db
```

Change this by setting `DATABASE_URL` environment variable:
```bash
export DATABASE_URL="postgresql://user:pass@localhost/portfolio"
# or
export DATABASE_URL="sqlite:///path/to/custom.db"
```

## Extending for Other Markets

The system is designed to work with any market type:

### Crypto Example
```python
portfolio = ps.ensure_portfolio(
    name="binance_spot",
    market_type=MarketType.CRYPTO,
    exchange="binance",
)

ps.record_trade(
    portfolio=portfolio,
    transaction_type=TransactionType.BUY,
    asset_id="BTC",
    asset_name="Bitcoin",
    quantity=Decimal("0.5"),
    price=Decimal("45000"),
    fee=Decimal("11.25"),
)
```

### Forex Example
```python
portfolio = ps.ensure_portfolio(
    name="oanda_account",
    market_type=MarketType.FOREX,
    exchange="oanda",
)

ps.record_trade(
    portfolio=portfolio,
    transaction_type=TransactionType.BUY,
    asset_id="EURUSD",
    quantity=Decimal("10000"),  # 1 mini lot
    price=Decimal("1.0850"),
    side=PositionSide.LONG,
)
```

## Best Practices

1. **Use context managers**: Always use `with PortfolioService()` for automatic session management
2. **Record all trades**: Call `record_trade()` whenever placing orders
3. **Update prices regularly**: Schedule `update_position_prices()` to track real-time P&L
4. **One portfolio per exchange**: Keep different exchanges in separate portfolios
5. **Decimal for precision**: Always use `Decimal` for monetary values, never float

## Testing

```bash
# Run tests
pytest tests/test_portfolio.py

# With coverage
pytest tests/test_portfolio.py --cov=polymarket_bot.portfolio
```

## Troubleshooting

### ImportError: No module named 'sqlalchemy'
```bash
pip install sqlalchemy>=2.0.0
```

### Database locked errors
SQLite has limited concurrency. For production, use PostgreSQL:
```bash
export DATABASE_URL="postgresql://user:pass@localhost/portfolio"
```

### Portfolio not found
Ensure `init_db()` was called before using the service.

## Architecture

```
portfolio/
├── models.py       # SQLAlchemy models (Portfolio, Position, Transaction)
├── database.py     # Database setup and session management
├── service.py      # Main API (PortfolioService)
└── __init__.py     # Public exports
```

## Future Enhancements

- [ ] Position history snapshots
- [ ] Performance metrics (Sharpe ratio, max drawdown)
- [ ] Trade analytics (win rate, avg profit)
- [ ] Multi-currency support
- [ ] Portfolio rebalancing tools
- [ ] Risk management alerts
- [ ] Export to CSV/JSON
- [ ] Alembic migrations for schema changes
