from datetime import datetime
from logs.database.db_models import Trade

def log_trade(session, symbol, entry_price, quantity, strategy):
    trade = Trade(
        symbol=symbol,
        entry_price=entry_price,
        quantity=quantity,
        entry_time=datetime.now(),
        strategy=strategy,
        status='open'
    )
    session.add(trade)
    session.commit()
    return trade.id

def update_trade(session, trade_id, exit_price, pnl):
    trade = session.query(Trade).filter(Trade.id == trade_id).first()
    if trade:
        trade.exit_price = exit_price
        trade.exit_time = datetime.now()
        trade.pnl = pnl
        trade.status = 'closed'
        session.commit()

def get_open_trades(session):
    return session.query(Trade).filter(Trade.status == 'open').all()

def get_trading_history(session, days=30):
    cutoff = datetime.now() - timedelta(days=days)
    return session.query(Trade).filter(Trade.exit_time >= cutoff).all()