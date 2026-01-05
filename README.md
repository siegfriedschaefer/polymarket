# Polymarket Trading Bot

An automated trading bot for Polymarket built with Python, featuring background task processing with Celery and designed for easy containerization with Docker.

## Architecture Overview

```
polymarket/
├── src/polymarket_bot/
│   ├── api/              # Polymarket API client wrapper
│   ├── strategies/       # Trading strategy implementations
│   ├── tasks/            # Celery background tasks
│   ├── utils/            # Utility functions and logging
│   ├── config.py         # Configuration management
│   └── main.py           # Main application entry point
├── tests/                # Test suite
├── config/               # Configuration files
├── logs/                 # Application logs
├── data/                 # Data storage
├── docker-compose.yml    # Docker orchestration
├── Dockerfile            # Container definition
└── requirements.txt      # Python dependencies
```

## Features

- **Polymarket API Integration**: Full wrapper around py-clob-client
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
- `LOG_LEVEL`: Logging level (default: `INFO`)

See `.env.example` for all available options.

## Development

### Project Structure

**src/polymarket_bot/api/**: API client wrapper
- `client.py`: Polymarket CLOB client wrapper with enhanced functionality

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
- **update_positions**: Updates position information every minute

You can trigger tasks manually:

```python
from polymarket_bot.tasks.trading_tasks import run_strategy
result = run_strategy.delay()
```

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
