def calculate_position_size(account_balance: float, risk_percent: float, entry_price: float,
                            stop_loss_price: float = None, risk_to_reward: float = 2) -> float:
    """
    Calculate position size based on risk management rules

    Args:
        account_balance: Total account balance
        risk_percent: Percentage of account to risk per trade (e.g., 0.01 for 1%)
        entry_price: Entry price of the trade
        stop_loss_price: Optional stop loss price
        risk_to_reward: Risk to reward ratio (default 2:1)

    Returns:
        Number of shares to trade
    """
    if stop_loss_price:
        risk_per_share = abs(entry_price - stop_loss_price)
    else:
        # Default to 2% stop loss if not provided
        risk_per_share = entry_price * 0.02

    risk_amount = account_balance * risk_percent
    position_size = risk_amount / risk_per_share

    # Round down to nearest whole share
    return int(position_size)