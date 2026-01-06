# Polymarket Trading Bot

An automated trading bot for Polymarket built with Claude, written in Python.
I want to find out how sophisticated and useful AI could be by implementing such a system.
I don't want to code anything on my side here, I help just with hints and bug fixing issues.
If you are interested in the problems which arose during implementation, than have a look at the journal.

|                  | AI    | Me          |
|------------------|-------|-------------|
| Domain Knowledge | ?     | 25%         |
| Research         | 80%   | 20%         |
| Specification    | 95%   | 5% (Idea)   |
| Code             | 100%  | 0%          |
| Test             | 100%  | 0%          |
| Debugging        | 90%   | 10%         |
| Integration      | 100%  | 0%          |
| Documentation    | 90%   | 10%         |

## Time / Costs

| Date      | Time | Tokens             |
|-----------|------|--------------------|
| 20260106  |  3h  | 70000              |
| 20260105  |  2h  | 137000             |

This bot (service? )features background task processing with Celery and it is designed for easy containerization with Docker.

## Architecture Overview

```
polymarket/
├── src/polymarket_bot/
│   ├── api/              # Polymarket API client wrapper
│   ├── portfolio/        # Portfolio tracking system (market-agnostic)
│   ├── strategies/       # Trading strategy implementations
│   ├── tasks/            # Celery background tasks
│   ├── utils/            # Utility functions and logging
│   ├── config.py         # Configuration management
│   └── main.py           # Main application entry point
├── tests/                # Test suite
├── examples/             # Example scripts and usage
├── config/               # Configuration files
├── logs/                 # Application logs
├── data/                 # Data storage (portfolio.db)
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # Container definition
└── requirements.txt      # Python dependencies
```

## Features

- **Polymarket API Integration**: Full wrapper around py-clob-client
- **Portfolio Tracking**: Market-agnostic position and P&L tracking with persistent database
- **Background Tasks**: Celery-based task queue for scheduled trading
- **Structured Logging**: JSON logging with structlog
- **Configuration Management**: Environment-based config with Pydantic
- **Docker Support**: Full containerization with docker-compose
- **Safety Features**: Trading disabled by default with explicit enable flag
- **Monitoring**: Flower UI for Celery task monitoring
- **Extensible Strategy System**: Base class for implementing custom strategies

## Prerequisites

### Local Development
- Python 3.10+
- Redis (for Celery)
- Polymarket API credentials

### Docker Deployment
- Docker
- Docker Compose

## Installation

### Local Development Setup

1. Clone the repository and navigate to the project:
```bash
cd /Users/siggis/projects/claude/polymarket
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
make install  # Production dependencies
# or
make dev-install  # Development dependencies
```

4. Copy the environment template and configure:
```bash
cp .env.example .env
```

5. Edit `.env` with your credentials:
```bash
POLYMARKET_API_KEY=your_api_key_here
POLYMARKET_SECRET=your_secret_key_here
ENABLE_TRADING=false  # Keep false until ready to trade live
```

6. Ensure Redis is running locally:
```bash
redis-server
```

### Docker Deployment

1. Copy the environment template:
```bash
cp .env.example .env
```

2. Configure your `.env` file with credentials

3. Build and start services:
```bash
make docker-build
make docker-up
```

This starts:
- **bot**: Main application
- **celery-worker**: Background task worker
- **celery-beat**: Task scheduler
- **flower**: Task monitoring UI (http://localhost:5555)
- **redis**: Message broker and result backend

## Usage

### Running Locally

Run the bot once:
```bash
make run
```

Start Celery worker:
```bash
make celery-worker
```

Start Celery beat scheduler:
```bash
make celery-beat
```

Start Flower monitoring:
```bash
make flower
```

### Running with Docker

Start all services:
```bash
make docker-up
```

View logs:
```bash
make docker-logs
```

Stop services:
```bash
make docker-down
```

## Configuration

All configuration is managed through environment variables in `.env`:

### Required Settings
- `POLYMARKET_API_KEY`: Your Polymarket API key
- `POLYMARKET_SECRET`: Your Polymarket secret key

### Trading Settings
- `ENABLE_TRADING`: Must be `true` to execute live trades (default: `false`)
- `MAX_POSITION_SIZE`: Maximum position size in USD (default: `100.0`)
- `MAX_SLIPPAGE`: Maximum acceptable slippage (default: `0.01`)

### Infrastructure
- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379/0`)
- `DATABASE_URL`: Portfolio database URL (default: `sqlite:///./data/portfolio.db`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

See `.env.example` for all available options.

**Note**: For production, consider using PostgreSQL for the portfolio database:
```bash
DATABASE_URL=postgresql://user:pass@localhost/polymarket_portfolio
```

## Development

### Project Structure

**src/polymarket_bot/api/**: API client wrapper
- `client.py`: Polymarket CLOB client wrapper with enhanced functionality

**src/polymarket_bot/portfolio/**: Portfolio tracking system
- `models.py`: SQLAlchemy models (Portfolio, Position, Transaction)
- `service.py`: Portfolio management service (PortfolioService)
- `database.py`: Database session management
- `README.md`: Complete portfolio tracking documentation

**src/polymarket_bot/strategies/**: Trading strategies
- `base.py`: Base strategy class to inherit from
- `example.py`: Example strategy implementation

**src/polymarket_bot/tasks/**: Background tasks
- `celery_app.py`: Celery configuration
- `trading_tasks.py`: Scheduled trading tasks

### Implementing a Custom Strategy

1. Create a new strategy file in `src/polymarket_bot/strategies/`:

```python
from polymarket_bot.strategies.base import BaseStrategy
from polymarket_bot.api.client import PolymarketClient

class MyStrategy(BaseStrategy):
    def __init__(self, client: PolymarketClient):
        super().__init__(client, name="MyStrategy")

    async def analyze(self) -> dict:
        # Implement your market analysis logic
        markets = await self.client.get_markets()
        # Your analysis here
        return {"action": "buy", "market": "..."}

    async def execute(self, signals: dict) -> list:
        # Implement your execution logic
        if signals.get("action") == "buy":
            order = await self.client.place_order({...})
            return [order]
        return []
```

2. Update `main.py` to use your strategy:

```python
from polymarket_bot.strategies.my_strategy import MyStrategy
# ...
self.strategy = MyStrategy(self.client)
```

### Portfolio Tracking

The bot includes a market-agnostic portfolio tracking system that works with Polymarket, crypto exchanges, and other asset types.

**Quick Start:**

```python
from polymarket_bot.portfolio import PortfolioService, MarketType, TransactionType
from decimal import Decimal

with PortfolioService() as ps:
    # Create portfolio
    portfolio = ps.ensure_portfolio(
        name="my_polymarket",
        market_type=MarketType.PREDICTION,
        exchange="polymarket"
    )

    # Add funds
    ps.add_funds(portfolio, Decimal("1000.00"))

    # Record a trade
    position, tx = ps.record_trade(
        portfolio=portfolio,
        transaction_type=TransactionType.BUY,
        asset_id="token_yes_123",
        quantity=Decimal("100"),
        price=Decimal("0.65"),
        fee=Decimal("0.50")
    )

    # Get portfolio summary
    summary = ps.get_portfolio_summary(portfolio)
    print(f"Total P&L: ${summary['total_pnl']}")
```

**Features:**
- Persistent state across restarts (SQLite/PostgreSQL)
- Real-time P&L tracking (unrealized and realized)
- Complete transaction audit trail
- Multi-portfolio support (track multiple exchanges)
- Works with any market type (prediction, crypto, stocks, forex)

**Run the example:**
```bash
PYTHONPATH=src python3 examples/portfolio_example.py
```

**View the database:**
```bash
sqlite3 data/portfolio.db
# or
cat src/polymarket_bot/portfolio/README.md  # Full documentation
```

### Running Tests

```bash
make test          # Run tests
make test-cov      # Run tests with coverage
```

### Code Quality

```bash
make format        # Format code with black and ruff
make lint          # Run linting checks
```

## Celery Tasks

The bot includes scheduled tasks configured in `tasks/celery_app.py`:

- **run_strategy**: Executes trading strategy every 5 minutes
- **update_positions**: Queries local portfolio database every minute for position tracking

You can trigger tasks manually:

```python
from polymarket_bot.tasks.trading_tasks import run_strategy
result = run_strategy.delay()
```

Note: The `update_positions` task queries the local portfolio database, not the Polymarket API. This provides persistent position tracking across restarts.

## Safety Features

1. **Trading Disabled by Default**: `ENABLE_TRADING=false` prevents accidental live trading
2. **Explicit Trade Confirmation**: All orders require `ENABLE_TRADING=true`
3. **Position Limits**: `MAX_POSITION_SIZE` caps position sizes
4. **Structured Logging**: All actions are logged for audit trails
5. **Test Environment**: Separate configuration for testing

## Monitoring

Access Flower UI for task monitoring:
- Local: http://localhost:5555
- Docker: http://localhost:5555

Monitor logs:
```bash
tail -f logs/bot.log                    # Local
docker-compose logs -f bot              # Docker
```

## Transitioning to Production

1. Set up a production environment:
```bash
ENVIRONMENT=production
DEBUG=false
ENABLE_TRADING=true  # Only when ready
```

2. Use the production Docker target:
```dockerfile
docker build --target production -t polymarket-bot:prod .
```

3. Configure monitoring and alerting
4. Set up proper secret management (not .env files)
5. Implement backup and disaster recovery
6. Enable metrics collection

## Troubleshooting

### Redis Connection Issues
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG
```

### API Authentication Errors
- Verify your API credentials in `.env`
- Check that credentials have proper permissions
- Ensure `POLYMARKET_CHAIN_ID` is correct (137 for mainnet)

### Celery Tasks Not Running
```bash
# Check Celery worker is running
celery -A polymarket_bot.tasks.celery_app inspect active

# Check Celery beat scheduler
celery -A polymarket_bot.tasks.celery_app inspect scheduled
```

## License

This is a template project. Add your license here.

## Disclaimer

This bot is for educational purposes. Trading cryptocurrencies and prediction markets carries significant risk. Never trade with funds you cannot afford to lose. Always test thoroughly in a development environment before enabling live trading.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Implement your changes with tests
4. Run linting and tests: `make lint && make test`
5. Submit a pull request

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review logs in `logs/bot.log`
