"""Portfolio tracking models - market-agnostic design."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import (
    DECIMAL,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class MarketType(str, Enum):
    """Types of markets supported."""

    PREDICTION = "prediction"  # Polymarket, Kalshi, etc.
    CRYPTO = "crypto"  # Spot/futures crypto
    FOREX = "forex"  # Foreign exchange
    STOCK = "stock"  # Stock markets
    OTHER = "other"


class PositionSide(str, Enum):
    """Side of a position."""

    LONG = "long"  # Betting YES / buying
    SHORT = "short"  # Betting NO / selling


class TransactionType(str, Enum):
    """Types of transactions."""

    BUY = "buy"
    SELL = "sell"
    DEPOSIT = "deposit"  # Adding funds
    WITHDRAWAL = "withdrawal"  # Removing funds
    FEE = "fee"  # Trading fees
    SETTLEMENT = "settlement"  # Position settlement/payout


class Portfolio(Base):
    """
    Portfolio represents the overall account state.

    One portfolio per market/exchange to keep things separated.
    """

    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    market_type = Column(String(20), nullable=False)  # MarketType enum
    exchange = Column(String(50), nullable=False)  # e.g., "polymarket", "binance"

    # Account identifiers
    account_id = Column(String(100))  # External account ID
    wallet_address = Column(String(100))  # For blockchain-based markets

    # Portfolio state
    cash_balance = Column(DECIMAL(20, 8), nullable=False, default=0)
    total_value = Column(DECIMAL(20, 8), nullable=False, default=0)
    unrealized_pnl = Column(DECIMAL(20, 8), nullable=False, default=0)
    realized_pnl = Column(DECIMAL(20, 8), nullable=False, default=0)

    # Metadata
    currency = Column(String(10), nullable=False, default="USD")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    positions = relationship("Position", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Portfolio(name='{self.name}', exchange='{self.exchange}', value={self.total_value})>"


class Position(Base):
    """
    Position represents an open holding in a specific asset/market.

    Market-agnostic design works for:
    - Polymarket outcome tokens (YES/NO)
    - Crypto spot holdings (BTC, ETH)
    - Crypto futures positions
    - Stock positions
    """

    __tablename__ = "positions"
    __table_args__ = (
        Index('idx_portfolio_asset', 'portfolio_id', 'asset_id'),
        Index('idx_portfolio_open', 'portfolio_id', 'is_open'),
    )

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)

    # Asset identification (flexible for different markets)
    asset_id = Column(String(100), nullable=False)  # Token ID, ticker symbol, contract address
    asset_name = Column(String(200))  # Human-readable name
    market_id = Column(String(100))  # External market/condition ID
    market_question = Column(Text)  # For prediction markets

    # Position details
    side = Column(String(10), nullable=False)  # PositionSide enum
    quantity = Column(DECIMAL(20, 8), nullable=False, default=0)

    # Cost basis tracking
    average_entry_price = Column(DECIMAL(20, 8), nullable=False)
    total_cost = Column(DECIMAL(20, 8), nullable=False)  # Including fees

    # Current state
    current_price = Column(DECIMAL(20, 8))
    current_value = Column(DECIMAL(20, 8))
    unrealized_pnl = Column(DECIMAL(20, 8))
    unrealized_pnl_percent = Column(DECIMAL(10, 4))

    # Status
    is_open = Column(Boolean, default=True)
    opened_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    closed_at = Column(DateTime)
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Additional metadata (JSON-serializable data)
    extra_data = Column(Text)  # Store JSON for market-specific data

    # Relationships
    portfolio = relationship("Portfolio", back_populates="positions")
    transactions = relationship("Transaction", back_populates="position")

    def __repr__(self):
        return f"<Position(asset='{self.asset_name}', qty={self.quantity}, pnl={self.unrealized_pnl})>"

    def calculate_pnl(self, current_price: Decimal) -> tuple[Decimal, Decimal]:
        """
        Calculate unrealized P&L for this position.

        Returns:
            (absolute_pnl, percentage_pnl)
        """
        self.current_price = current_price
        self.current_value = current_price * self.quantity

        if self.side == PositionSide.LONG:
            self.unrealized_pnl = self.current_value - self.total_cost
        else:  # SHORT
            self.unrealized_pnl = self.total_cost - self.current_value

        self.unrealized_pnl_percent = (self.unrealized_pnl / self.total_cost * 100) if self.total_cost > 0 else Decimal(0)

        return self.unrealized_pnl, self.unrealized_pnl_percent


class Transaction(Base):
    """
    Transaction records all activities that affect portfolio/positions.

    This creates an audit trail for all trades, deposits, withdrawals, etc.
    """

    __tablename__ = "transactions"
    __table_args__ = (
        Index('idx_portfolio_created', 'portfolio_id', 'created_at'),
        Index('idx_position_created', 'position_id', 'created_at'),
    )

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("positions.id"))  # Nullable for non-position txns

    # Transaction details
    transaction_type = Column(String(20), nullable=False)  # TransactionType enum
    asset_id = Column(String(100), nullable=False)
    quantity = Column(DECIMAL(20, 8), nullable=False)
    price = Column(DECIMAL(20, 8))
    amount = Column(DECIMAL(20, 8), nullable=False)  # Total amount (qty * price)
    fee = Column(DECIMAL(20, 8), default=0)

    # External references
    external_id = Column(String(100))  # Order ID from exchange
    external_order_id = Column(String(100))  # Original order that created this fill

    # Metadata
    notes = Column(Text)
    extra_data = Column(Text)  # JSON for additional data
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    portfolio = relationship("Portfolio", back_populates="transactions")
    position = relationship("Position", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction(type='{self.transaction_type}', asset='{self.asset_id}', qty={self.quantity})>"
