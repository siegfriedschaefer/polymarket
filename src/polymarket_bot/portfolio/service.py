"""Portfolio management service - main API for tracking positions."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from polymarket_bot.portfolio.database import get_db, init_db
from polymarket_bot.portfolio.models import (
    MarketType,
    Portfolio,
    Position,
    PositionSide,
    Transaction,
    TransactionType,
)

logger = structlog.get_logger(__name__)


class PortfolioService:
    """
    Service for managing portfolio state across different markets.

    This is market-agnostic and can be used for Polymarket, crypto, stocks, etc.
    """

    def __init__(self, db_session: Optional[Session] = None):
        """
        Initialize portfolio service.

        Args:
            db_session: Optional database session. If not provided, will use context manager.
        """
        self.db = db_session
        self._owns_session = db_session is None

    def __enter__(self):
        """Support context manager usage."""
        if self._owns_session:
            self._context = get_db()
            self.db = self._context.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up context manager."""
        if self._owns_session and hasattr(self, '_context'):
            return self._context.__exit__(exc_type, exc_val, exc_tb)

    def ensure_portfolio(
        self,
        name: str,
        market_type: MarketType,
        exchange: str,
        account_id: Optional[str] = None,
        wallet_address: Optional[str] = None,
        currency: str = "USD",
    ) -> Portfolio:
        """
        Get or create a portfolio.

        Args:
            name: Unique portfolio name
            market_type: Type of market (prediction, crypto, etc.)
            exchange: Exchange/platform name
            account_id: External account identifier
            wallet_address: Wallet address for blockchain markets
            currency: Base currency

        Returns:
            Portfolio instance
        """
        portfolio = self.db.query(Portfolio).filter(Portfolio.name == name).first()

        if not portfolio:
            portfolio = Portfolio(
                name=name,
                market_type=market_type.value,
                exchange=exchange,
                account_id=account_id,
                wallet_address=wallet_address,
                currency=currency,
            )
            self.db.add(portfolio)
            self.db.commit()
            self.db.refresh(portfolio)

            logger.info(
                "portfolio_created",
                portfolio_id=portfolio.id,
                name=name,
                market_type=market_type,
                exchange=exchange,
            )

        return portfolio

    def record_trade(
        self,
        portfolio: Portfolio,
        transaction_type: TransactionType,
        asset_id: str,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal = Decimal(0),
        asset_name: Optional[str] = None,
        market_id: Optional[str] = None,
        market_question: Optional[str] = None,
        side: Optional[PositionSide] = None,
        external_id: Optional[str] = None,
        external_order_id: Optional[str] = None,
    ) -> tuple[Position, Transaction]:
        """
        Record a trade and update positions.

        Args:
            portfolio: Portfolio to update
            transaction_type: BUY or SELL
            asset_id: Asset identifier (token ID, ticker, etc.)
            quantity: Amount traded
            price: Price per unit
            fee: Trading fee
            asset_name: Human-readable asset name
            market_id: Market/condition ID
            market_question: Market question (for prediction markets)
            side: Position side (LONG/SHORT), auto-determined if not provided
            external_id: External transaction ID
            external_order_id: External order ID

        Returns:
            (position, transaction) tuple
        """
        # Build position query filters
        filters = [
            Position.portfolio_id == portfolio.id,
            Position.asset_id == asset_id,
            Position.is_open == True,
        ]

        # For SELL without explicit side, find any open position
        # For BUY, default to LONG if side not specified
        if side is not None:
            filters.append(Position.side == side.value)
        elif transaction_type == TransactionType.BUY:
            side = PositionSide.LONG
            filters.append(Position.side == side.value)

        # Find existing position
        position = (
            self.db.query(Position)
            .filter(and_(*filters))
            .first()
        )

        # Set side from existing position if selling
        if transaction_type == TransactionType.SELL and position is not None and side is None:
            side = PositionSide(position.side)

        # Calculate amounts
        total_amount = quantity * price
        total_cost = total_amount + fee

        if transaction_type == TransactionType.BUY:
            if position is None:
                # Open new position
                position = Position(
                    portfolio_id=portfolio.id,
                    asset_id=asset_id,
                    asset_name=asset_name or asset_id,
                    market_id=market_id,
                    market_question=market_question,
                    side=side.value,
                    quantity=quantity,
                    average_entry_price=price,
                    total_cost=total_cost,
                    is_open=True,
                )
                self.db.add(position)
            else:
                # Add to existing position
                old_total_cost = position.total_cost
                new_total_cost = old_total_cost + total_cost

                old_quantity = position.quantity
                new_quantity = old_quantity + quantity

                # Update average entry price
                position.average_entry_price = new_total_cost / new_quantity
                position.quantity = new_quantity
                position.total_cost = new_total_cost

        elif transaction_type == TransactionType.SELL:
            if position is None:
                raise ValueError(f"Cannot sell - no open position for asset {asset_id}")

            if quantity > position.quantity:
                raise ValueError(
                    f"Cannot sell {quantity} - only {position.quantity} available"
                )

            # Reduce position
            position.quantity -= quantity

            # If position fully closed
            if position.quantity == 0:
                position.is_open = False
                position.closed_at = datetime.utcnow()

                # Calculate realized P&L
                realized_pnl = total_amount - (position.average_entry_price * quantity) - fee
                portfolio.realized_pnl += realized_pnl

                logger.info(
                    "position_closed",
                    position_id=position.id,
                    asset_id=asset_id,
                    realized_pnl=float(realized_pnl),
                )
            else:
                # Partial close - adjust cost basis proportionally
                remaining_ratio = position.quantity / (position.quantity + quantity)
                position.total_cost *= remaining_ratio

        # Record transaction
        transaction = Transaction(
            portfolio_id=portfolio.id,
            position_id=position.id,
            transaction_type=transaction_type.value,
            asset_id=asset_id,
            quantity=quantity,
            price=price,
            amount=total_amount,
            fee=fee,
            external_id=external_id,
            external_order_id=external_order_id,
        )
        self.db.add(transaction)

        # Update portfolio cash (assuming cash-based trades)
        if transaction_type == TransactionType.BUY:
            portfolio.cash_balance -= total_cost
        elif transaction_type == TransactionType.SELL:
            portfolio.cash_balance += total_amount - fee

        portfolio.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(position)
        self.db.refresh(transaction)

        logger.info(
            "trade_recorded",
            portfolio_id=portfolio.id,
            position_id=position.id,
            transaction_id=transaction.id,
            type=transaction_type.value,
            asset_id=asset_id,
            quantity=float(quantity),
            price=float(price),
        )

        return position, transaction

    def update_position_prices(self, portfolio: Portfolio, prices: dict[str, Decimal]) -> Portfolio:
        """
        Update current prices for all positions and recalculate P&L.

        Args:
            portfolio: Portfolio to update
            prices: Dict mapping asset_id to current price

        Returns:
            Updated portfolio with recalculated values
        """
        total_value = portfolio.cash_balance
        total_unrealized_pnl = Decimal(0)

        open_positions = (
            self.db.query(Position)
            .filter(and_(Position.portfolio_id == portfolio.id, Position.is_open == True))
            .all()
        )

        for position in open_positions:
            if position.asset_id in prices:
                current_price = prices[position.asset_id]
                unrealized_pnl, pnl_percent = position.calculate_pnl(current_price)

                total_value += position.current_value
                total_unrealized_pnl += unrealized_pnl

                logger.debug(
                    "position_updated",
                    position_id=position.id,
                    asset_id=position.asset_id,
                    current_price=float(current_price),
                    unrealized_pnl=float(unrealized_pnl),
                )

        # Update portfolio totals
        portfolio.total_value = total_value
        portfolio.unrealized_pnl = total_unrealized_pnl
        portfolio.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(portfolio)

        logger.info(
            "portfolio_updated",
            portfolio_id=portfolio.id,
            total_value=float(portfolio.total_value),
            unrealized_pnl=float(portfolio.unrealized_pnl),
            realized_pnl=float(portfolio.realized_pnl),
        )

        return portfolio

    def get_portfolio_summary(self, portfolio: Portfolio) -> dict:
        """
        Get comprehensive portfolio summary.

        Args:
            portfolio: Portfolio to summarize

        Returns:
            Dictionary with portfolio stats
        """
        open_positions = (
            self.db.query(Position)
            .filter(and_(Position.portfolio_id == portfolio.id, Position.is_open == True))
            .all()
        )

        total_transactions = (
            self.db.query(func.count(Transaction.id))
            .filter(Transaction.portfolio_id == portfolio.id)
            .scalar()
        )

        return {
            "portfolio_id": portfolio.id,
            "name": portfolio.name,
            "exchange": portfolio.exchange,
            "market_type": portfolio.market_type,
            "cash_balance": float(portfolio.cash_balance),
            "total_value": float(portfolio.total_value),
            "unrealized_pnl": float(portfolio.unrealized_pnl),
            "realized_pnl": float(portfolio.realized_pnl),
            "total_pnl": float(portfolio.unrealized_pnl + portfolio.realized_pnl),
            "open_positions_count": len(open_positions),
            "total_transactions": total_transactions,
            "positions": [
                {
                    "asset_id": pos.asset_id,
                    "asset_name": pos.asset_name,
                    "side": pos.side,
                    "quantity": float(pos.quantity),
                    "entry_price": float(pos.average_entry_price),
                    "current_price": float(pos.current_price) if pos.current_price else None,
                    "current_value": float(pos.current_value) if pos.current_value else None,
                    "unrealized_pnl": float(pos.unrealized_pnl) if pos.unrealized_pnl else None,
                    "pnl_percent": float(pos.unrealized_pnl_percent) if pos.unrealized_pnl_percent else None,
                }
                for pos in open_positions
            ],
            "updated_at": portfolio.updated_at.isoformat(),
        }

    def add_funds(self, portfolio: Portfolio, amount: Decimal, notes: Optional[str] = None) -> Transaction:
        """
        Add funds to portfolio (deposit).

        Args:
            portfolio: Portfolio to deposit to
            amount: Amount to deposit
            notes: Optional notes

        Returns:
            Transaction record
        """
        portfolio.cash_balance += amount

        transaction = Transaction(
            portfolio_id=portfolio.id,
            transaction_type=TransactionType.DEPOSIT.value,
            asset_id="CASH",
            quantity=amount,
            price=Decimal(1),
            amount=amount,
            notes=notes,
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        logger.info("funds_added", portfolio_id=portfolio.id, amount=float(amount))

        return transaction

    def withdraw_funds(self, portfolio: Portfolio, amount: Decimal, notes: Optional[str] = None) -> Transaction:
        """
        Withdraw funds from portfolio.

        Args:
            portfolio: Portfolio to withdraw from
            amount: Amount to withdraw
            notes: Optional notes

        Returns:
            Transaction record
        """
        if amount > portfolio.cash_balance:
            raise ValueError(f"Insufficient funds: {portfolio.cash_balance} available, {amount} requested")

        portfolio.cash_balance -= amount

        transaction = Transaction(
            portfolio_id=portfolio.id,
            transaction_type=TransactionType.WITHDRAWAL.value,
            asset_id="CASH",
            quantity=amount,
            price=Decimal(1),
            amount=amount,
            notes=notes,
        )
        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        logger.info("funds_withdrawn", portfolio_id=portfolio.id, amount=float(amount))

        return transaction

    def reset_portfolio(self, portfolio: Portfolio) -> None:
        """
        Reset portfolio to initial state by clearing all positions, transactions, and funds.

        Args:
            portfolio: Portfolio to reset

        Warning:
            This operation cannot be undone. All trading history will be permanently deleted.
        """
        # Delete all transactions
        self.db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio.id
        ).delete()

        # Delete all positions
        self.db.query(Position).filter(
            Position.portfolio_id == portfolio.id
        ).delete()

        # Reset portfolio balances
        portfolio.cash_balance = Decimal(0)
        portfolio.total_value = Decimal(0)
        portfolio.unrealized_pnl = Decimal(0)
        portfolio.realized_pnl = Decimal(0)
        portfolio.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(portfolio)

        logger.info(
            "portfolio_reset",
            portfolio_id=portfolio.id,
            name=portfolio.name
        )
