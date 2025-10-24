"""
REST API routes for Sentiment Arena
All endpoints for models, portfolios, positions, trades, and scheduler
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal

from backend.database.base import SessionLocal
from backend.models.model import Model
from backend.models.portfolio import Portfolio
from backend.models.position import Position
from backend.models.trade import Trade, TradeSide, TradeStatus
from backend.models.reasoning import Reasoning
from backend.services.market_data import MarketDataService
from backend.services.trading_engine import TradingEngine
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["API"])


# Dependency to get database session
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Helper function to convert Decimal to float
def decimal_to_float(value):
    """Convert Decimal to float for JSON serialization"""
    if isinstance(value, Decimal):
        return float(value)
    return value


@router.get("/models", response_model=List[Dict[str, Any]])
async def get_models(db: Session = Depends(get_db)):
    """
    Get all competing models with basic stats

    Returns:
        List of models with portfolio information
    """
    models = db.query(Model).all()

    result = []
    for model in models:
        portfolio = db.query(Portfolio).filter(Portfolio.model_id == model.id).first()

        # Count positions and trades
        num_positions = db.query(Position).filter(Position.model_id == model.id).count()
        num_trades = db.query(Trade).filter(Trade.model_id == model.id).count()

        result.append({
            "id": model.id,
            "name": model.name,
            "api_identifier": model.api_identifier,
            "starting_balance": decimal_to_float(model.starting_balance),
            "current_balance": decimal_to_float(portfolio.current_balance) if portfolio else 0.0,
            "total_value": decimal_to_float(portfolio.total_value) if portfolio else 0.0,
            "total_pl": decimal_to_float(portfolio.total_pl) if portfolio else 0.0,
            "num_positions": num_positions,
            "num_trades": num_trades,
            "created_at": model.created_at.isoformat() if model.created_at else None
        })

    return result


@router.get("/models/{model_id}/portfolio", response_model=Dict[str, Any])
async def get_portfolio(model_id: int, db: Session = Depends(get_db)):
    """
    Get current portfolio for a model

    Args:
        model_id: Model ID

    Returns:
        Portfolio with balance, positions, and total value
    """
    # Get model
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Get portfolio
    portfolio = db.query(Portfolio).filter(Portfolio.model_id == model_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Get positions
    positions = db.query(Position).filter(Position.model_id == model_id).all()

    positions_data = []
    for position in positions:
        positions_data.append({
            "id": position.id,
            "symbol": position.symbol,
            "quantity": position.quantity,
            "avg_price": decimal_to_float(position.avg_price),
            "current_price": decimal_to_float(position.current_price),
            "unrealized_pl": decimal_to_float(position.unrealized_pl),
            "unrealized_pl_pct": decimal_to_float(position.unrealized_pl_pct),
            "position_value": decimal_to_float(position.position_value),
            "opened_at": position.opened_at.isoformat() if position.opened_at else None
        })

    return {
        "model_id": model_id,
        "model_name": model.name,
        "current_balance": decimal_to_float(portfolio.current_balance),
        "total_value": decimal_to_float(portfolio.total_value),
        "total_pl": decimal_to_float(portfolio.total_pl),
        "total_pl_pct": decimal_to_float(portfolio.total_pl_pct),
        "realized_pl": decimal_to_float(portfolio.realized_pl),
        "num_positions": len(positions),
        "positions": positions_data
    }


@router.get("/models/{model_id}/positions", response_model=List[Dict[str, Any]])
async def get_positions(model_id: int, db: Session = Depends(get_db)):
    """
    Get current open positions for a model

    Args:
        model_id: Model ID

    Returns:
        List of open positions
    """
    # Verify model exists
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    positions = db.query(Position).filter(Position.model_id == model_id).all()

    result = []
    for position in positions:
        result.append({
            "id": position.id,
            "symbol": position.symbol,
            "quantity": position.quantity,
            "avg_price": decimal_to_float(position.avg_price),
            "current_price": decimal_to_float(position.current_price),
            "unrealized_pl": decimal_to_float(position.unrealized_pl),
            "unrealized_pl_pct": decimal_to_float(position.unrealized_pl_pct),
            "position_value": decimal_to_float(position.position_value),
            "opened_at": position.opened_at.isoformat() if position.opened_at else None,
            "updated_at": position.updated_at.isoformat() if position.updated_at else None
        })

    return result


@router.get("/models/{model_id}/trades", response_model=Dict[str, Any])
async def get_trades(
    model_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get trade history for a model with pagination

    Args:
        model_id: Model ID
        skip: Number of trades to skip (default: 0)
        limit: Number of trades to return (default: 50, max: 100)

    Returns:
        Paginated trade history
    """
    # Verify model exists
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Get total count
    total = db.query(Trade).filter(Trade.model_id == model_id).count()

    # Get trades with pagination
    trades = (
        db.query(Trade)
        .filter(Trade.model_id == model_id)
        .order_by(desc(Trade.timestamp))
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for trade in trades:
        result.append({
            "id": trade.id,
            "symbol": trade.symbol,
            "side": trade.side.value if trade.side else None,
            "quantity": trade.quantity,
            "price": decimal_to_float(trade.price),
            "fee": decimal_to_float(trade.fee),
            "total": decimal_to_float(trade.total),
            "status": trade.status.value if trade.status else None,
            "timestamp": trade.timestamp.isoformat() if trade.timestamp else None
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "trades": result
    }


@router.get("/models/{model_id}/performance", response_model=Dict[str, Any])
async def get_performance(model_id: int, db: Session = Depends(get_db)):
    """
    Get performance metrics for a model

    Args:
        model_id: Model ID

    Returns:
        Performance metrics (P&L, win rate, ROI, etc.)
    """
    # Verify model exists
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Get portfolio
    portfolio = db.query(Portfolio).filter(Portfolio.model_id == model_id).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # Get trading engine for metrics
    trading_engine = TradingEngine(db)

    # Get performance metrics
    try:
        metrics = trading_engine.get_portfolio_metrics(model_id)

        return {
            "model_id": model_id,
            "model_name": model.name,
            "starting_balance": decimal_to_float(model.starting_balance),
            "current_balance": decimal_to_float(portfolio.current_balance),
            "total_value": decimal_to_float(portfolio.total_value),
            "total_pl": decimal_to_float(portfolio.total_pl),
            "total_pl_pct": decimal_to_float(portfolio.total_pl_pct),
            "realized_pl": decimal_to_float(portfolio.realized_pl),
            "unrealized_pl": decimal_to_float(metrics.get("unrealized_pl", 0)),
            "total_trades": metrics.get("total_trades", 0),
            "winning_trades": metrics.get("winning_trades", 0),
            "losing_trades": metrics.get("losing_trades", 0),
            "win_rate": metrics.get("win_rate", 0.0),
            "total_fees_paid": decimal_to_float(metrics.get("total_fees_paid", 0)),
            "num_positions": metrics.get("num_positions", 0),
            "roi": decimal_to_float(portfolio.total_pl_pct)
        }
    except Exception as e:
        logger.error(f"Error calculating performance: {e}")
        # Return basic metrics if calculation fails
        return {
            "model_id": model_id,
            "model_name": model.name,
            "starting_balance": decimal_to_float(model.starting_balance),
            "current_balance": decimal_to_float(portfolio.current_balance),
            "total_value": decimal_to_float(portfolio.total_value),
            "total_pl": decimal_to_float(portfolio.total_pl),
            "total_pl_pct": decimal_to_float(portfolio.total_pl_pct),
            "realized_pl": decimal_to_float(portfolio.realized_pl),
            "error": str(e)
        }


@router.get("/models/{model_id}/reasoning", response_model=List[Dict[str, Any]])
async def get_reasoning(
    model_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Get latest reasoning/decisions for a model

    Args:
        model_id: Model ID
        limit: Number of reasoning entries to return (default: 10, max: 50)

    Returns:
        Latest reasoning entries
    """
    # Verify model exists
    model = db.query(Model).filter(Model.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Get reasoning entries
    reasoning_entries = (
        db.query(Reasoning)
        .filter(Reasoning.model_id == model_id)
        .order_by(desc(Reasoning.timestamp))
        .limit(limit)
        .all()
    )

    result = []
    for entry in reasoning_entries:
        result.append({
            "id": entry.id,
            "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
            "decision": entry.decision,
            "reasoning_text": entry.reasoning_text,
            "research_content": entry.research_content,
            "confidence": entry.confidence,
            "raw_response": entry.raw_response
        })

    return result


@router.get("/leaderboard", response_model=List[Dict[str, Any]])
async def get_leaderboard(db: Session = Depends(get_db)):
    """
    Get leaderboard of all models ranked by performance

    Returns:
        Models ranked by total P&L
    """
    # Get all models with portfolios
    models = (
        db.query(Model, Portfolio)
        .join(Portfolio, Model.id == Portfolio.model_id)
        .order_by(desc(Portfolio.total_pl))
        .all()
    )

    result = []
    rank = 1
    for model, portfolio in models:
        # Count positions and trades
        num_positions = db.query(Position).filter(Position.model_id == model.id).count()
        num_trades = db.query(Trade).filter(Trade.model_id == model.id).count()

        result.append({
            "rank": rank,
            "model_id": model.id,
            "model_name": model.name,
            "api_identifier": model.api_identifier,
            "total_value": decimal_to_float(portfolio.total_value),
            "total_pl": decimal_to_float(portfolio.total_pl),
            "total_pl_pct": decimal_to_float(portfolio.total_pl_pct),
            "realized_pl": decimal_to_float(portfolio.realized_pl),
            "current_balance": decimal_to_float(portfolio.current_balance),
            "num_positions": num_positions,
            "num_trades": num_trades
        })
        rank += 1

    return result


@router.get("/market/status", response_model=Dict[str, Any])
async def get_market_status():
    """
    Get current market status

    Returns:
        Market open/closed status and next market event
    """
    market_data = MarketDataService()

    try:
        is_open = market_data.is_market_open()
        is_trading_day = market_data.is_trading_day()

        # Get current time in CET
        from datetime import datetime
        import pytz
        cet = pytz.timezone("Europe/Berlin")
        current_time = datetime.now(cet)

        return {
            "is_open": is_open,
            "is_trading_day": is_trading_day,
            "current_time_cet": current_time.isoformat(),
            "market_hours": {
                "open": "09:00 CET",
                "close": "17:30 CET"
            },
            "trading_days": "Monday - Friday (excluding holidays)"
        }
    except Exception as e:
        logger.error(f"Error getting market status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler/status", response_model=Dict[str, Any])
async def get_scheduler_status():
    """
    Get scheduler status and upcoming jobs

    Returns:
        Scheduler status and job information
    """
    from backend.main import get_scheduler

    scheduler = get_scheduler()
    if not scheduler:
        return {
            "status": "not_running",
            "message": "Scheduler is not initialized"
        }

    try:
        status = scheduler.get_job_status()
        return status
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/trigger-research", response_model=Dict[str, Any])
async def trigger_research(
    job_name: Optional[str] = Query(None, description="Job name to trigger (pre_market_research or afternoon_research)")
):
    """
    Manually trigger a research job

    Args:
        job_name: Name of job to trigger (optional)

    Returns:
        Trigger confirmation
    """
    from backend.main import get_scheduler

    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(status_code=503, detail="Scheduler is not running")

    try:
        # Determine which job to trigger
        if job_name:
            if job_name not in ["pre_market_research", "afternoon_research"]:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid job name. Use 'pre_market_research' or 'afternoon_research'"
                )
            scheduler.trigger_job_now(job_name)
            message = f"Triggered {job_name}"
        else:
            # Trigger pre-market by default
            scheduler.trigger_job_now("pre_market_research")
            message = "Triggered pre_market_research"

        return {
            "success": True,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error triggering research: {e}")
        raise HTTPException(status_code=500, detail=str(e))
