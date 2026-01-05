# Polymarket Bot - Architecture & Execution Diagrams

## 1. System Architecture Overview

```mermaid
graph TB
    subgraph "User Layer"
        USER[User/Developer]
    end

    subgraph "Application Layer"
        MAIN[Main Application<br/>main.py]
        CONFIG[Configuration<br/>config.py]
        LOGGING[Logging<br/>utils/logging.py]
    end

    subgraph "Business Logic Layer"
        API[API Client<br/>api/client.py]
        STRATEGY[Strategy Engine<br/>strategies/]
        BASE[Base Strategy]
        EXAMPLE[Example Strategy]
        CUSTOM[Your Custom Strategy]
    end

    subgraph "Task Queue Layer"
        CELERY[Celery App<br/>celery_app.py]
        WORKER[Celery Worker]
        BEAT[Celery Beat Scheduler]
        TASKS[Trading Tasks<br/>trading_tasks.py]
    end

    subgraph "Infrastructure Layer"
        REDIS[(Redis<br/>Message Broker)]
        FLOWER[Flower<br/>Monitoring UI]
    end

    subgraph "External Services"
        POLYMARKET[Polymarket API<br/>clob.polymarket.com]
    end

    USER --> MAIN
    USER --> CELERY
    MAIN --> CONFIG
    MAIN --> LOGGING
    MAIN --> STRATEGY
    STRATEGY --> BASE
    BASE --> EXAMPLE
    BASE --> CUSTOM
    STRATEGY --> API
    API --> POLYMARKET

    CELERY --> WORKER
    CELERY --> BEAT
    CELERY --> REDIS
    WORKER --> TASKS
    BEAT --> TASKS
    TASKS --> API
    REDIS --> FLOWER

    CONFIG -.env vars.-> MAIN
    CONFIG -.env vars.-> CELERY

    style USER fill:#e1f5ff
    style POLYMARKET fill:#ffe1e1
    style REDIS fill:#ffe1f5
    style MAIN fill:#c8e6c9
    style CELERY fill:#c8e6c9
```

## 2. Main Application Execution Flow

```mermaid
sequenceDiagram
    participant User
    participant Main as main.py
    participant Config as config.py
    participant Logger as logging.py
    participant Client as API Client
    participant Strategy
    participant Polymarket as Polymarket API

    User->>Main: python -m polymarket_bot.main
    activate Main

    Main->>Logger: setup_logging()
    Logger-->>Main: Logger configured

    Main->>Config: Load settings from .env
    Config-->>Main: Settings object

    Main->>Main: Initialize Application()

    Main->>Client: get_client()
    activate Client
    Client->>Config: Get API credentials
    Config-->>Client: API key, secret
    Client->>Client: Initialize ClobClient
    Client-->>Main: Client instance
    deactivate Client

    Main->>Strategy: Initialize ExampleStrategy(client)
    Strategy-->>Main: Strategy instance

    Main->>Main: Register signal handlers

    Main->>Strategy: strategy.run()
    activate Strategy

    Strategy->>Strategy: analyze()
    Strategy->>Client: get_markets()
    Client->>Polymarket: GET /markets
    Polymarket-->>Client: Market data
    Client-->>Strategy: Markets list

    Strategy->>Strategy: Process analysis
    Strategy->>Strategy: execute(signals)

    alt Trading Enabled
        Strategy->>Client: place_order(params)
        Client->>Config: Check ENABLE_TRADING
        Config-->>Client: True
        Client->>Polymarket: POST /order
        Polymarket-->>Client: Order result
        Client-->>Strategy: Order placed
    else Trading Disabled
        Strategy->>Client: place_order(params)
        Client->>Config: Check ENABLE_TRADING
        Config-->>Client: False
        Client-->>Strategy: Trading disabled
    end

    Strategy-->>Main: Execution result
    deactivate Strategy

    Main->>Main: shutdown()
    Main-->>User: Exit
    deactivate Main
```

## 3. Celery Background Task Execution

```mermaid
sequenceDiagram
    participant Beat as Celery Beat
    participant Broker as Redis Broker
    participant Worker as Celery Worker
    participant Task as Trading Task
    participant Client as API Client
    participant Strategy
    participant Polymarket as Polymarket API

    Note over Beat: Every 5 minutes
    Beat->>Broker: Publish 'run_strategy' task

    Broker->>Worker: Deliver task
    activate Worker

    Worker->>Task: Execute run_strategy()
    activate Task

    Task->>Client: get_client()
    Client-->>Task: Client instance

    Task->>Strategy: Initialize ExampleStrategy
    Strategy-->>Task: Strategy instance

    Task->>Strategy: asyncio.run(strategy.run())
    activate Strategy

    Strategy->>Strategy: analyze()
    Strategy->>Client: get_markets()
    Client->>Polymarket: GET /markets
    Polymarket-->>Client: Market data
    Client-->>Strategy: Markets

    Strategy->>Strategy: execute(signals)
    Strategy->>Client: place_order() if needed
    Client->>Polymarket: POST /order
    Polymarket-->>Client: Order result
    Client-->>Strategy: Result

    Strategy-->>Task: Execution result
    deactivate Strategy

    Task->>Broker: Store result
    Task-->>Worker: Task complete
    deactivate Task

    Worker-->>Broker: Acknowledge
    deactivate Worker

    Note over Beat: Every 1 minute
    Beat->>Broker: Publish 'update_positions' task

    Broker->>Worker: Deliver task
    activate Worker
    Worker->>Task: Execute update_positions()
    activate Task

    Task->>Client: get_client()
    Client-->>Task: Client instance

    Task->>Client: asyncio.run(client.get_positions())
    Client->>Polymarket: GET /positions
    Polymarket-->>Client: Positions data
    Client-->>Task: Positions

    Task->>Broker: Store result
    Task-->>Worker: Task complete
    deactivate Task
    Worker-->>Broker: Acknowledge
    deactivate Worker
```

## 4. Strategy Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Initialization

    Initialization --> Analysis: strategy.run()

    state Analysis {
        [*] --> FetchMarkets
        FetchMarkets --> ProcessData
        ProcessData --> GenerateSignals
        GenerateSignals --> [*]
    }

    Analysis --> Execution: signals generated

    state Execution {
        [*] --> CheckSignals
        CheckSignals --> NoAction: no signals
        CheckSignals --> ValidateRules: has signals
        ValidateRules --> CheckTradingEnabled
        CheckTradingEnabled --> PlaceOrder: enabled=true
        CheckTradingEnabled --> LogOnly: enabled=false
        PlaceOrder --> VerifyOrder
        VerifyOrder --> [*]
        LogOnly --> [*]
        NoAction --> [*]
    }

    Execution --> Complete
    Complete --> [*]
```

## 5. Trading Flow Decision Tree

```mermaid
flowchart TD
    Start([Strategy Run Triggered]) --> Init[Initialize Client & Strategy]
    Init --> Analyze[Run Analysis]

    Analyze --> GetMarkets[Fetch Markets from API]
    GetMarkets --> ProcessMarkets{Markets<br/>Available?}

    ProcessMarkets -->|No| NoMarkets[Log: No markets]
    ProcessMarkets -->|Yes| AnalyzeData[Analyze Market Data]

    AnalyzeData --> GenSignals[Generate Trading Signals]
    GenSignals --> HasSignals{Signals<br/>Generated?}

    HasSignals -->|No| NoAction[Log: No Action Required]
    HasSignals -->|Yes| ValidateSignals[Validate Signals]

    ValidateSignals --> CheckSize{Position Size<br/>Within Limit?}
    CheckSize -->|No| RejectSize[Reject: Size Too Large]
    CheckSize -->|Yes| CheckSlippage{Slippage<br/>Acceptable?}

    CheckSlippage -->|No| RejectSlip[Reject: Slippage Too High]
    CheckSlippage -->|Yes| CheckEnabled{ENABLE_TRADING<br/>= true?}

    CheckEnabled -->|No| LogOrder[Log Order - Not Executed]
    CheckEnabled -->|Yes| PlaceOrder[Place Order via API]

    PlaceOrder --> OrderSuccess{Order<br/>Success?}
    OrderSuccess -->|Yes| LogSuccess[Log: Order Placed]
    OrderSuccess -->|No| LogError[Log: Order Failed]

    NoMarkets --> End([Return Result])
    NoAction --> End
    RejectSize --> End
    RejectSlip --> End
    LogOrder --> End
    LogSuccess --> End
    LogError --> End

    style Start fill:#c8e6c9
    style End fill:#c8e6c9
    style CheckEnabled fill:#fff9c4
    style PlaceOrder fill:#ffccbc
    style OrderSuccess fill:#fff9c4
```

## 6. Docker Container Orchestration

```mermaid
graph TB
    subgraph "Docker Compose Environment"
        subgraph "Application Containers"
            BOT[Bot Container<br/>Main Application]
            WORKER[Worker Container<br/>Celery Worker]
            BEAT[Beat Container<br/>Celery Beat]
            FLOWER[Flower Container<br/>Monitoring UI:5555]
        end

        subgraph "Infrastructure"
            REDIS[Redis Container<br/>:6379]
        end

        subgraph "Shared Volumes"
            LOGS[./logs:/app/logs]
            DATA[./data:/app/data]
            SRC[./src:/app/src]
        end
    end

    subgraph "External"
        POLY[Polymarket API]
        USER[User Browser]
    end

    BOT --> REDIS
    WORKER --> REDIS
    BEAT --> REDIS
    FLOWER --> REDIS

    BOT --> LOGS
    WORKER --> LOGS
    BEAT --> LOGS

    BOT --> DATA
    WORKER --> DATA

    BOT --> SRC
    WORKER --> SRC
    BEAT --> SRC

    BOT --> POLY
    WORKER --> POLY

    USER --> FLOWER

    style REDIS fill:#ffe1f5
    style POLY fill:#ffe1e1
    style FLOWER fill:#e1f5ff
```

## 7. Configuration Flow

```mermaid
flowchart LR
    ENV[.env File] --> LOAD[Load Environment Variables]
    LOAD --> PYDANTIC[Pydantic Settings]

    PYDANTIC --> VALIDATE{Validation}
    VALIDATE -->|Invalid| ERROR[Raise ValidationError]
    VALIDATE -->|Valid| SETTINGS[Settings Object]

    SETTINGS --> MAIN[Main Application]
    SETTINGS --> CELERY[Celery App]
    SETTINGS --> API[API Client]
    SETTINGS --> LOGGER[Logger]

    MAIN --> RUN[Application Runtime]
    CELERY --> TASKS[Background Tasks]

    style ENV fill:#fff9c4
    style SETTINGS fill:#c8e6c9
    style ERROR fill:#ffccbc
```

## 8. Data Flow Diagram

```mermaid
flowchart TD
    subgraph "Data Sources"
        PM[Polymarket API]
        ENV[Environment Config]
    end

    subgraph "Application"
        CLIENT[API Client]
        STRATEGY[Strategy Engine]
        CACHE[Redis Cache]
    end

    subgraph "Storage"
        LOGS[Log Files]
        DATA[Data Directory]
        REDIS_DB[(Redis DB)]
    end

    subgraph "Outputs"
        ORDERS[Order Execution]
        METRICS[Metrics/Monitoring]
        ALERTS[Alerts/Notifications]
    end

    PM -->|Market Data| CLIENT
    PM -->|Positions| CLIENT
    CLIENT -->|Parsed Data| STRATEGY

    ENV -->|Configuration| STRATEGY
    ENV -->|Configuration| CLIENT

    STRATEGY -->|Analysis Results| CACHE
    CACHE -->|Cached Data| STRATEGY
    CACHE --> REDIS_DB

    STRATEGY -->|Trading Signals| ORDERS
    ORDERS -->|Order Data| PM

    CLIENT -->|Structured Logs| LOGS
    STRATEGY -->|Structured Logs| LOGS
    ORDERS -->|Structured Logs| LOGS

    STRATEGY -->|Positions| DATA
    STRATEGY -->|Historical Data| DATA

    ORDERS -->|Metrics| METRICS
    STRATEGY -->|Alerts| ALERTS

    style PM fill:#ffe1e1
    style ORDERS fill:#ffccbc
    style LOGS fill:#e1f5ff
    style DATA fill:#e1f5ff
```

## 9. Error Handling Flow

```mermaid
flowchart TD
    START[Operation Start] --> TRY[Try Execute]

    TRY --> SUCCESS{Success?}

    SUCCESS -->|Yes| LOG_SUCCESS[Log Success]
    SUCCESS -->|No| CATCH[Catch Exception]

    CATCH --> LOG_ERROR[Log Error with Context]
    LOG_ERROR --> CHECK_TYPE{Error Type?}

    CHECK_TYPE -->|API Error| RETRY{Retryable?}
    CHECK_TYPE -->|Config Error| FATAL[Fatal Error]
    CHECK_TYPE -->|Network Error| RETRY
    CHECK_TYPE -->|Other| LOG_UNKNOWN[Log Unknown Error]

    RETRY -->|Yes| BACKOFF[Exponential Backoff]
    RETRY -->|No| REPORT[Report Failure]

    BACKOFF --> TRY

    FATAL --> SHUTDOWN[Shutdown Application]
    REPORT --> CONTINUE[Continue Execution]
    LOG_UNKNOWN --> CONTINUE
    LOG_SUCCESS --> RETURN[Return Result]
    CONTINUE --> RETURN

    style FATAL fill:#ffccbc
    style SUCCESS fill:#c8e6c9
    style SHUTDOWN fill:#ff8a80
```

## 10. Deployment Transition

```mermaid
graph LR
    subgraph "Development"
        DEV_LOCAL[Local Python<br/>venv]
        DEV_REDIS[Local Redis<br/>localhost:6379]
        DEV_ENV[.env file<br/>ENABLE_TRADING=false]
    end

    subgraph "Docker Development"
        DOCKER_DEV[Docker Compose<br/>development target]
        DOCKER_REDIS[Redis Container]
        DOCKER_VOL[Mounted Volumes<br/>Hot Reload]
    end

    subgraph "Production"
        DOCKER_PROD[Docker Compose<br/>production target]
        PROD_REDIS[Redis Container<br/>Persistent Volume]
        PROD_ENV[Secrets Management<br/>ENABLE_TRADING=true]
        PROD_MON[Monitoring<br/>Prometheus/Grafana]
    end

    DEV_LOCAL -->|docker-compose up| DOCKER_DEV
    DOCKER_DEV -->|Build prod image| DOCKER_PROD
    DOCKER_PROD --> PROD_MON

    DEV_ENV -.copy.-> DOCKER_DEV
    DOCKER_DEV -.configure.-> PROD_ENV

    style DEV_LOCAL fill:#e1f5ff
    style DOCKER_DEV fill:#fff9c4
    style DOCKER_PROD fill:#c8e6c9
```

## Execution Modes

### Mode 1: One-Time Execution
```bash
python -m polymarket_bot.main
```
- Runs strategy once
- Logs results
- Exits

### Mode 2: Scheduled Execution (Celery)
```bash
# Terminal 1
celery -A polymarket_bot.tasks.celery_app worker

# Terminal 2
celery -A polymarket_bot.tasks.celery_app beat
```
- Runs strategy every 5 minutes
- Updates positions every minute
- Runs continuously

### Mode 3: Docker Orchestration
```bash
docker-compose up
```
- All services start together
- Auto-restart on failure
- Shared networking
- Persistent storage

## Key Integration Points

1. **Configuration**: All components read from `config.py` → `.env`
2. **Logging**: All components use `structlog` → `logs/bot.log`
3. **API Client**: Singleton pattern ensures single instance
4. **Task Queue**: Redis coordinates between Celery components
5. **Monitoring**: Flower provides visibility into task execution
6. **Docker**: Containers share network and volumes

## Critical Paths

### Trading Path
`.env` → `config.py` → `API Client` → `Strategy` → `Polymarket API`

### Monitoring Path
`Task Execution` → `Redis` → `Flower UI` → `User`

### Logging Path
`All Components` → `structlog` → `logs/bot.log` → `Analysis`
