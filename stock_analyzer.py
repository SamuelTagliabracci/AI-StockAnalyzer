"""
Stock Analyzer for TSX Stock Analyzer
Handles comprehensive stock analysis and scoring
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class StockAnalyzer:
    """Comprehensive stock analysis and scoring system"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate technical indicators from price data"""
        if df is None or len(df) < 10:
            return self._get_default_technical_indicators(df)
        
        try:
            # Ensure data is sorted by date
            df = df.sort_values('date').copy()
            
            # Moving averages
            df['sma_20'] = df['close'].rolling(window=min(20, len(df))).mean()
            df['sma_50'] = df['close'].rolling(window=min(50, len(df))).mean()
            df['sma_200'] = df['close'].rolling(window=min(200, len(df))).mean() if len(df) >= 200 else None
            
            # RSI calculation
            delta = df['close'].diff()
            window = min(14, len(df) // 3)
            if window >= 2:
                gain = delta.where(delta > 0, 0).rolling(window=window).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                rs = gain / loss
                df['rsi'] = 100 - (100 / (1 + rs))
            else:
                df['rsi'] = 50
            
            # Bollinger Bands
            bb_window = min(20, len(df) // 2)
            if bb_window >= 5:
                df['bb_middle'] = df['close'].rolling(bb_window).mean()
                bb_std = df['close'].rolling(bb_window).std()
                df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
                df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            else:
                df['bb_middle'] = df['close'].mean()
                bb_std = df['close'].std()
                df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
                df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
            # MACD
            if len(df) >= 26:
                exp1 = df['close'].ewm(span=12).mean()
                exp2 = df['close'].ewm(span=26).mean()
                df['macd'] = exp1 - exp2
                df['macd_signal'] = df['macd'].ewm(span=9).mean()
                df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(window=min(20, len(df))).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Price ranges
            df['true_range'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            df['atr'] = df['true_range'].rolling(window=min(14, len(df))).mean()
            
            # Get latest values
            latest = df.iloc[-1]
            
            # 52-week high/low
            week_52_period = min(252, len(df))
            week_52_high = df['high'].tail(week_52_period).max()
            week_52_low = df['low'].tail(week_52_period).min()
            
            # Calculate positions and ratios
            current_price = latest['close']
            bb_range = latest['bb_upper'] - latest['bb_lower']
            bb_position = (current_price - latest['bb_lower']) / bb_range if bb_range > 0 else 0.5
            
            # Price trend analysis
            trend_strength = self._calculate_trend_strength(df)
            support_resistance = self._calculate_support_resistance(df)
            
            return {
                'current_price': current_price,
                'sma_20': latest['sma_20'] if pd.notna(latest['sma_20']) else current_price,
                'sma_50': latest['sma_50'] if pd.notna(latest['sma_50']) else current_price,
                'sma_200': latest['sma_200'] if 'sma_200' in df.columns and pd.notna(latest.get('sma_200')) else None,
                'rsi': latest['rsi'] if pd.notna(latest['rsi']) else 50,
                'bb_position': bb_position,
                'bb_upper': latest['bb_upper'],
                'bb_lower': latest['bb_lower'],
                'macd': latest.get('macd', 0),
                'macd_signal': latest.get('macd_signal', 0),
                'macd_histogram': latest.get('macd_histogram', 0),
                'volume_ratio': latest['volume_ratio'] if pd.notna(latest['volume_ratio']) else 1,
                'atr': latest['atr'] if pd.notna(latest['atr']) else 0,
                '52_week_high': week_52_high,
                '52_week_low': week_52_low,
                '52_week_position': (current_price - week_52_low) / (week_52_high - week_52_low) if week_52_high != week_52_low else 0.5,
                'trend_strength': trend_strength,
                'support_level': support_resistance['support'],
                'resistance_level': support_resistance['resistance'],
                'volatility': df['close'].pct_change().std() * np.sqrt(252) if len(df) > 10 else 0.3
            }
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return self._get_default_technical_indicators(df)
    
    def _get_default_technical_indicators(self, df: pd.DataFrame) -> Dict:
        """Return default technical indicators when calculation fails"""
        current_price = df['close'].iloc[-1] if df is not None and len(df) > 0 else 100
        return {
            'current_price': current_price,
            'sma_20': current_price,
            'sma_50': current_price,
            'sma_200': None,
            'rsi': 50,
            'bb_position': 0.5,
            'bb_upper': current_price * 1.1,
            'bb_lower': current_price * 0.9,
            'macd': 0,
            'macd_signal': 0,
            'macd_histogram': 0,
            'volume_ratio': 1,
            'atr': current_price * 0.02,
            '52_week_high': current_price,
            '52_week_low': current_price,
            '52_week_position': 0.5,
            'trend_strength': 0,
            'support_level': current_price * 0.95,
            'resistance_level': current_price * 1.05,
            'volatility': 0.3
        }
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Calculate trend strength (-1 to 1, negative = downtrend, positive = uptrend)"""
        if len(df) < 20:
            return 0
        
        # Use linear regression on recent prices
        recent_data = df.tail(20).copy()
        recent_data['price_index'] = range(len(recent_data))
        
        # Calculate slope of price trend
        x = recent_data['price_index'].values
        y = recent_data['close'].values
        
        if len(x) < 2:
            return 0
        
        slope = np.polyfit(x, y, 1)[0]
        price_range = y.max() - y.min()
        
        # Normalize slope by price range and time period
        if price_range > 0:
            trend_strength = (slope * len(x)) / price_range
            return max(-1, min(1, trend_strength))  # Clamp to [-1, 1]
        
        return 0
    
    def _calculate_support_resistance(self, df: pd.DataFrame) -> Dict:
        """Calculate support and resistance levels"""
        if len(df) < 20:
            current = df['close'].iloc[-1]
            return {'support': current * 0.95, 'resistance': current * 1.05}
        
        # Use recent highs and lows
        period = min(50, len(df))
        recent_data = df.tail(period)
        
        # Find local maxima and minima
        highs = recent_data['high'].rolling(window=5, center=True).max()
        lows = recent_data['low'].rolling(window=5, center=True).min()
        
        resistance_levels = highs[highs == recent_data['high']].dropna().values
        support_levels = lows[lows == recent_data['low']].dropna().values
        
        current_price = df['close'].iloc[-1]
        
        # Find nearest resistance above current price
        resistance = current_price * 1.05  # Default 5% above
        if len(resistance_levels) > 0:
            above_current = resistance_levels[resistance_levels > current_price]
            if len(above_current) > 0:
                resistance = above_current.min()
        
        # Find nearest support below current price
        support = current_price * 0.95  # Default 5% below
        if len(support_levels) > 0:
            below_current = support_levels[support_levels < current_price]
            if len(below_current) > 0:
                support = below_current.max()
        
        return {'support': support, 'resistance': resistance}
    
    def calculate_performance_metrics(self, df: pd.DataFrame) -> Dict:
        """Calculate performance and risk metrics"""
        if df is None or len(df) < 10:
            return {}
        
        current_price = df['close'].iloc[-1]
        returns = {}
        
        # Calculate returns for different periods
        periods = {'1W': 5, '1M': 21, '3M': 63, '6M': 126, '1Y': 252}
        
        for period_name, days in periods.items():
            if len(df) > days:
                old_price = df['close'].iloc[-(days+1)]
                if old_price > 0:
                    returns[f'return_{period_name}'] = (current_price - old_price) / old_price
        
        # Calculate daily returns for risk metrics
        df['daily_return'] = df['close'].pct_change()
        daily_returns = df['daily_return'].dropna()
        
        if len(daily_returns) > 10:
            # Risk metrics
            volatility = daily_returns.std() * np.sqrt(252)  # Annualized
            var_95 = daily_returns.quantile(0.05)  # 5% VaR
            
            # Sharpe ratio (assuming 2% risk-free rate)
            excess_return = daily_returns.mean() * 252 - 0.02
            sharpe_ratio = excess_return / volatility if volatility > 0 else 0
            
            # Maximum drawdown
            cumulative_returns = (1 + daily_returns).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            # Downside deviation
            negative_returns = daily_returns[daily_returns < 0]
            downside_deviation = negative_returns.std() * np.sqrt(252) if len(negative_returns) > 0 else 0
            
            # Sortino ratio
            sortino_ratio = excess_return / downside_deviation if downside_deviation > 0 else 0
            
        else:
            volatility = 0.3
            var_95 = -0.05
            sharpe_ratio = 0
            max_drawdown = 0
            downside_deviation = 0.2
            sortino_ratio = 0
        
        # Price momentum
        momentum_score = self._calculate_momentum_score(returns)
        
        return {
            **returns,
            'volatility': volatility,
            'var_95': var_95,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'downside_deviation': downside_deviation,
            'momentum_score': momentum_score
        }
    
    def _calculate_momentum_score(self, returns: Dict) -> float:
        """Calculate momentum score from returns (0-100)"""
        score = 50  # Neutral starting point
        
        # Weight recent performance more heavily
        weights = {'1W': 0.3, '1M': 0.3, '3M': 0.2, '6M': 0.1, '1Y': 0.1}
        
        for period, weight in weights.items():
            return_key = f'return_{period}'
            if return_key in returns:
                period_return = returns[return_key]
                # Convert return to score contribution
                if period_return > 0.2:  # >20% return
                    contribution = 25 * weight
                elif period_return > 0.1:  # >10% return
                    contribution = 15 * weight
                elif period_return > 0.05:  # >5% return
                    contribution = 10 * weight
                elif period_return > 0:  # Positive return
                    contribution = 5 * weight
                elif period_return > -0.05:  # Small loss
                    contribution = -5 * weight
                elif period_return > -0.1:  # Moderate loss
                    contribution = -10 * weight
                else:  # Large loss
                    contribution = -20 * weight
                
                score += contribution
        
        return max(0, min(100, score))
    
    def score_fundamental_health(self, fundamentals: Dict) -> Tuple[int, Dict]:
        """Score fundamental health (0-40 points) with detailed breakdown"""
        if not fundamentals:
            return 0, {}
        
        score = 0
        max_score = 40
        breakdown = {}
        
        # Valuation metrics (15 points)
        valuation_score = 0
        
        pe = fundamentals.get('pe_ratio')
        if pe and 5 <= pe <= 25:
            valuation_score += 8
            breakdown['pe_status'] = 'Excellent'
        elif pe and pe < 5:
            valuation_score += 4
            breakdown['pe_status'] = 'Very Low (Risky)'
        elif pe and pe <= 35:
            valuation_score += 3
            breakdown['pe_status'] = 'Acceptable'
        else:
            breakdown['pe_status'] = 'High/Unknown'
        
        pb = fundamentals.get('price_to_book')
        if pb and 0.5 <= pb <= 3:
            valuation_score += 4
            breakdown['pb_status'] = 'Good'
        elif pb and pb <= 5:
            valuation_score += 2
            breakdown['pb_status'] = 'Acceptable'
        else:
            breakdown['pb_status'] = 'High/Unknown'
        
        peg = fundamentals.get('peg_ratio')
        if peg and 0.5 <= peg <= 1.5:
            valuation_score += 3
            breakdown['peg_status'] = 'Excellent'
        elif peg and peg <= 2:
            valuation_score += 1
            breakdown['peg_status'] = 'Acceptable'
        else:
            breakdown['peg_status'] = 'High/Unknown'
        
        score += valuation_score
        breakdown['valuation_score'] = valuation_score
        
        # Profitability (15 points)
        profitability_score = 0
        
        roe = fundamentals.get('roe')
        if roe and roe >= 0.15:
            profitability_score += 8
            breakdown['roe_status'] = 'Excellent (>15%)'
        elif roe and roe >= 0.10:
            profitability_score += 5
            breakdown['roe_status'] = 'Good (>10%)'
        elif roe and roe >= 0.05:
            profitability_score += 2
            breakdown['roe_status'] = 'Acceptable (>5%)'
        else:
            breakdown['roe_status'] = 'Low/Unknown'
        
        profit_margin = fundamentals.get('profit_margin')
        if profit_margin and profit_margin >= 0.15:
            profitability_score += 4
            breakdown['margin_status'] = 'Excellent (>15%)'
        elif profit_margin and profit_margin >= 0.08:
            profitability_score += 2
            breakdown['margin_status'] = 'Good (>8%)'
        elif profit_margin and profit_margin >= 0.03:
            profitability_score += 1
            breakdown['margin_status'] = 'Acceptable (>3%)'
        else:
            breakdown['margin_status'] = 'Low/Unknown'
        
        revenue_growth = fundamentals.get('revenue_growth')
        if revenue_growth and revenue_growth >= 0.10:
            profitability_score += 3
            breakdown['growth_status'] = 'Strong (>10%)'
        elif revenue_growth and revenue_growth >= 0.05:
            profitability_score += 2
            breakdown['growth_status'] = 'Good (>5%)'
        elif revenue_growth and revenue_growth >= 0:
            profitability_score += 1
            breakdown['growth_status'] = 'Positive'
        else:
            breakdown['growth_status'] = 'Declining/Unknown'
        
        score += profitability_score
        breakdown['profitability_score'] = profitability_score
        
        # Financial stability (10 points)
        stability_score = 0
        
        debt_to_equity = fundamentals.get('debt_to_equity')
        if debt_to_equity is not None:
            if debt_to_equity <= 0.3:
                stability_score += 5
                breakdown['debt_status'] = 'Low Debt (<30%)'
            elif debt_to_equity <= 0.6:
                stability_score += 3
                breakdown['debt_status'] = 'Moderate Debt (<60%)'
            elif debt_to_equity <= 1.0:
                stability_score += 1
                breakdown['debt_status'] = 'High Debt (<100%)'
            else:
                breakdown['debt_status'] = 'Very High Debt'
        else:
            breakdown['debt_status'] = 'Unknown'
        
        dividend_yield = fundamentals.get('dividend_yield')
        if dividend_yield and 0.02 <= dividend_yield <= 0.06:
            stability_score += 3
            breakdown['dividend_status'] = f'Healthy Yield ({dividend_yield*100:.1f}%)'
        elif dividend_yield and dividend_yield <= 0.08:
            stability_score += 2
            breakdown['dividend_status'] = f'Good Yield ({dividend_yield*100:.1f}%)'
        elif dividend_yield and dividend_yield > 0:
            stability_score += 1
            breakdown['dividend_status'] = f'Dividend Paying ({dividend_yield*100:.1f}%)'
        else:
            breakdown['dividend_status'] = 'No Dividend'
        
        payout_ratio = fundamentals.get('payout_ratio')
        if payout_ratio and 0.3 <= payout_ratio <= 0.6:
            stability_score += 2
            breakdown['payout_status'] = 'Sustainable Payout'
        elif payout_ratio and payout_ratio <= 0.8:
            stability_score += 1
            breakdown['payout_status'] = 'Moderate Payout'
        elif payout_ratio:
            breakdown['payout_status'] = 'High Payout Risk'
        else:
            breakdown['payout_status'] = 'Unknown'
        
        score += stability_score
        breakdown['stability_score'] = stability_score
        
        return min(score, max_score), breakdown
    
    def score_technical_strength(self, technical: Dict) -> Tuple[int, Dict]:
        """Score technical strength (0-30 points) with detailed breakdown"""
        if not technical:
            return 0, {}
        
        score = 0
        max_score = 30
        breakdown = {}
        
        # Trend analysis (15 points)
        trend_score = 0
        current = technical.get('current_price', 0)
        sma_20 = technical.get('sma_20')
        sma_50 = technical.get('sma_50')
        sma_200 = technical.get('sma_200')
        
        if sma_20 and current > sma_20:
            trend_score += 3
            breakdown['sma_20_status'] = 'Above SMA20'
        else:
            breakdown['sma_20_status'] = 'Below SMA20'
        
        if sma_50 and current > sma_50:
            trend_score += 4
            breakdown['sma_50_status'] = 'Above SMA50'
        else:
            breakdown['sma_50_status'] = 'Below SMA50'
        
        if sma_200 and current > sma_200:
            trend_score += 5
            breakdown['sma_200_status'] = 'Above SMA200 (Bull Market)'
        elif sma_200:
            breakdown['sma_200_status'] = 'Below SMA200 (Bear Market)'
        else:
            breakdown['sma_200_status'] = 'Insufficient Data'
        
        if sma_20 and sma_50 and sma_20 > sma_50:
            trend_score += 3
            breakdown['ma_alignment'] = 'Bullish Alignment'
        else:
            breakdown['ma_alignment'] = 'Bearish/Neutral'
        
        score += trend_score
        breakdown['trend_score'] = trend_score
        
        # Momentum indicators (10 points)
        momentum_score = 0
        
        rsi = technical.get('rsi')
        if rsi:
            if 40 <= rsi <= 60:
                momentum_score += 3
                breakdown['rsi_status'] = f'Neutral Zone ({rsi:.1f})'
            elif 30 <= rsi <= 70:
                momentum_score += 2
                breakdown['rsi_status'] = f'Normal Range ({rsi:.1f})'
            elif rsi <= 30:
                momentum_score += 1
                breakdown['rsi_status'] = f'Oversold ({rsi:.1f})'
            elif rsi >= 70:
                breakdown['rsi_status'] = f'Overbought ({rsi:.1f})'
            else:
                breakdown['rsi_status'] = f'RSI: {rsi:.1f}'
        else:
            breakdown['rsi_status'] = 'Unknown'
        
        # MACD
        macd = technical.get('macd', 0)
        macd_signal = technical.get('macd_signal', 0)
        if macd > macd_signal:
            momentum_score += 2
            breakdown['macd_status'] = 'Bullish Signal'
        else:
            breakdown['macd_status'] = 'Bearish Signal'
        
        # Volume
        volume_ratio = technical.get('volume_ratio', 1)
        if volume_ratio > 1.5:
            momentum_score += 2
            breakdown['volume_status'] = 'High Volume (Strong Interest)'
        elif volume_ratio > 1.2:
            momentum_score += 1
            breakdown['volume_status'] = 'Above Average Volume'
        else:
            breakdown['volume_status'] = 'Normal Volume'
        
        # Bollinger Band position
        bb_pos = technical.get('bb_position')
        if bb_pos:
            if 0.3 <= bb_pos <= 0.7:
                momentum_score += 3
                breakdown['bb_status'] = 'Middle of Bands (Stable)'
            elif 0.1 <= bb_pos <= 0.9:
                momentum_score += 2
                breakdown['bb_status'] = 'Normal Range'
            elif bb_pos <= 0.2:
                momentum_score += 1
                breakdown['bb_status'] = 'Near Lower Band (Potential Bounce)'
            else:
                breakdown['bb_status'] = 'Near Upper Band (Resistance)'
        else:
            breakdown['bb_status'] = 'Unknown'
        
        score += momentum_score
        breakdown['momentum_score'] = momentum_score
        
        # Position analysis (5 points)
        position_score = 0
        
        week_52_pos = technical.get('52_week_position')
        if week_52_pos:
            if 0.5 <= week_52_pos <= 0.8:
                position_score += 5
                breakdown['52_week_status'] = 'Strong Position (50-80% of range)'
            elif 0.3 <= week_52_pos <= 0.9:
                position_score += 3
                breakdown['52_week_status'] = 'Good Position'
            elif week_52_pos <= 0.3:
                position_score += 2
                breakdown['52_week_status'] = 'Near 52-week Low (Value Opportunity)'
            else:
                position_score += 1
                breakdown['52_week_status'] = 'Near 52-week High (Resistance)'
        else:
            breakdown['52_week_status'] = 'Unknown'
        
        score += position_score
        breakdown['position_score'] = position_score
        
        return min(score, max_score), breakdown
    
    def score_momentum_quality(self, performance: Dict) -> Tuple[int, Dict]:
        """Score momentum and quality (0-30 points) with detailed breakdown"""
        if not performance:
            return 0, {}
        
        score = 0
        max_score = 30
        breakdown = {}
        
        # Recent performance (15 points)
        performance_score = 0
        
        # Get returns
        ret_1w = performance.get('return_1W', 0)
        ret_1m = performance.get('return_1M', 0)
        ret_3m = performance.get('return_3M', 0)
        ret_1y = performance.get('return_1Y', 0)
        
        # Count positive periods
        returns_list = [r for r in [ret_1w, ret_1m, ret_3m, ret_1y] if r is not None]
        positive_periods = sum([r > 0 for r in returns_list])
        performance_score += positive_periods * 2
        
        breakdown['positive_periods'] = f'{positive_periods}/{len(returns_list)} periods positive'
        
        # Strong recent performance
        if ret_1m and ret_1m > 0.05:
            performance_score += 3
            breakdown['1m_performance'] = f'Strong ({ret_1m*100:+.1f}%)'
        elif ret_1m and ret_1m > 0:
            performance_score += 1
            breakdown['1m_performance'] = f'Positive ({ret_1m*100:+.1f}%)'
        elif ret_1m:
            breakdown['1m_performance'] = f'Negative ({ret_1m*100:+.1f}%)'
        else:
            breakdown['1m_performance'] = 'Unknown'
        
        if ret_1y and ret_1y > 0.15:
            performance_score += 4
            breakdown['1y_performance'] = f'Excellent ({ret_1y*100:+.1f}%)'
        elif ret_1y and ret_1y > 0.05:
            performance_score += 2
            breakdown['1y_performance'] = f'Good ({ret_1y*100:+.1f}%)'
        elif ret_1y and ret_1y > 0:
            performance_score += 1
            breakdown['1y_performance'] = f'Positive ({ret_1y*100:+.1f}%)'
        elif ret_1y:
            breakdown['1y_performance'] = f'Negative ({ret_1y*100:+.1f}%)'
        else:
            breakdown['1y_performance'] = 'Unknown'
        
        score += performance_score
        breakdown['performance_score'] = performance_score
        
        # Risk-adjusted returns (10 points)
        risk_score = 0
        
        sharpe = performance.get('sharpe_ratio', 0)
        if sharpe > 1.0:
            risk_score += 6
            breakdown['sharpe_status'] = f'Excellent ({sharpe:.2f})'
        elif sharpe > 0.5:
            risk_score += 4
            breakdown['sharpe_status'] = f'Good ({sharpe:.2f})'
        elif sharpe > 0:
            risk_score += 2
            breakdown['sharpe_status'] = f'Positive ({sharpe:.2f})'
        else:
            breakdown['sharpe_status'] = f'Poor ({sharpe:.2f})'
        
        sortino = performance.get('sortino_ratio', 0)
        if sortino > 1.0:
            risk_score += 2
            breakdown['sortino_status'] = f'Excellent ({sortino:.2f})'
        elif sortino > 0.5:
            risk_score += 1
            breakdown['sortino_status'] = f'Good ({sortino:.2f})'
        else:
            breakdown['sortino_status'] = f'Needs Improvement ({sortino:.2f})'
        
        volatility = performance.get('volatility', 0)
        if volatility < 0.2:
            risk_score += 2
            breakdown['volatility_status'] = f'Low Risk ({volatility*100:.1f}%)'
        elif volatility < 0.4:
            risk_score += 1
            breakdown['volatility_status'] = f'Moderate Risk ({volatility*100:.1f}%)'
        else:
            breakdown['volatility_status'] = f'High Risk ({volatility*100:.1f}%)'
        
        score += risk_score
        breakdown['risk_score'] = risk_score
        
        # Drawdown management (5 points)
        drawdown_score = 0
        
        max_dd = performance.get('max_drawdown', 0)
        if max_dd > -0.1:
            drawdown_score += 3
            breakdown['drawdown_status'] = f'Excellent (<10%: {max_dd*100:.1f}%)'
        elif max_dd > -0.2:
            drawdown_score += 2
            breakdown['drawdown_status'] = f'Good (<20%: {max_dd*100:.1f}%)'
        elif max_dd > -0.3:
            drawdown_score += 1
            breakdown['drawdown_status'] = f'Acceptable (<30%: {max_dd*100:.1f}%)'
        else:
            breakdown['drawdown_status'] = f'High Drawdown ({max_dd*100:.1f}%)'
        
        score += drawdown_score
        breakdown['drawdown_score'] = drawdown_score
        
        return min(score, max_score), breakdown
    
    def calculate_risk_score(self, technical: Dict, performance: Dict, fundamentals: Dict) -> Tuple[int, Dict]:
        """Calculate risk score (0-100, higher = more risky)"""
        risk_score = 0
        breakdown = {}
        
        # Volatility risk (0-30)
        volatility = performance.get('volatility', 0.3)
        if volatility > 0.6:
            vol_risk = 30
        elif volatility > 0.4:
            vol_risk = 20
        elif volatility > 0.25:
            vol_risk = 10
        else:
            vol_risk = 5
        
        risk_score += vol_risk
        breakdown['volatility_risk'] = vol_risk
        
        # Beta risk (0-20)
        beta = fundamentals.get('beta', 1.0) if fundamentals else 1.0
        if beta > 1.5:
            beta_risk = 20
        elif beta > 1.2:
            beta_risk = 15
        elif beta > 0.8:
            beta_risk = 5
        else:
            beta_risk = 10  # Very low beta can also be risky
        
        risk_score += beta_risk
        breakdown['beta_risk'] = beta_risk
        
        # Financial leverage risk (0-25)
        debt_to_equity = fundamentals.get('debt_to_equity') if fundamentals else None
        if debt_to_equity is None:
            leverage_risk = 10  # Unknown = moderate risk
        elif debt_to_equity > 1.5:
            leverage_risk = 25
        elif debt_to_equity > 1.0:
            leverage_risk = 15
        elif debt_to_equity > 0.5:
            leverage_risk = 5
        else:
            leverage_risk = 0
        
        risk_score += leverage_risk
        breakdown['leverage_risk'] = leverage_risk
        
        # Technical risk (0-15)
        rsi = technical.get('rsi', 50) if technical else 50
        bb_position = technical.get('bb_position', 0.5) if technical else 0.5
        
        tech_risk = 0
        if rsi > 80 or rsi < 20:  # Extreme RSI
            tech_risk += 8
        elif rsi > 70 or rsi < 30:
            tech_risk += 4
        
        if bb_position > 0.9 or bb_position < 0.1:  # Near band extremes
            tech_risk += 7
        elif bb_position > 0.8 or bb_position < 0.2:
            tech_risk += 3
        
        risk_score += tech_risk
        breakdown['technical_risk'] = tech_risk
        
        # Drawdown risk (0-10)
        max_drawdown = performance.get('max_drawdown', 0) if performance else 0
        if max_drawdown < -0.4:  # >40% drawdown
            dd_risk = 10
        elif max_drawdown < -0.3:
            dd_risk = 8
        elif max_drawdown < -0.2:
            dd_risk = 5
        elif max_drawdown < -0.1:
            dd_risk = 2
        else:
            dd_risk = 0
        
        risk_score += dd_risk
        breakdown['drawdown_risk'] = dd_risk
        
        risk_percentage = min(100, risk_score)
        return risk_percentage, breakdown
    
    def calculate_target_pricing(self, symbol: str, fundamentals: Dict, technical: Dict, performance: Dict) -> Dict:
        """Calculate target pricing and buy recommendations"""
        current_price = technical.get('current_price', 100) if technical else 100
        
        # Conservative buy price (support level or 15% below current)
        support_level = technical.get('support_level', current_price * 0.9) if technical else current_price * 0.9
        conservative_buy = min(current_price * 0.85, support_level)
        
        # Aggressive buy price (10% below current)
        aggressive_buy = current_price * 0.90
        
        # Target price calculation
        target_methods = []
        
        # Method 1: P/E based target
        if fundamentals and fundamentals.get('pe_ratio') and fundamentals.get('earnings_growth'):
            current_pe = fundamentals['pe_ratio']
            growth_rate = fundamentals['earnings_growth']
            
            # Fair P/E based on growth (PEG = 1.0 target)
            fair_pe = min(max(growth_rate * 100 * 0.8, 10), 25)  # Clamp between 10-25
            
            # Estimate EPS
            estimated_eps = current_price / current_pe
            pe_target = estimated_eps * fair_pe
            target_methods.append(pe_target)
        
        # Method 2: Technical resistance
        if technical and technical.get('resistance_level'):
            resistance = technical['resistance_level']
            if resistance > current_price:
                target_methods.append(resistance)
        
        # Method 3: 52-week high adjusted for momentum
        if technical and technical.get('52_week_high'):
            week_52_high = technical['52_week_high']
            momentum_score = performance.get('momentum_score', 50) if performance else 50
            
            # Adjust 52-week high based on momentum
            if momentum_score > 70:
                adjusted_target = week_52_high * 1.1  # Strong momentum
            elif momentum_score > 50:
                adjusted_target = week_52_high
            else:
                adjusted_target = week_52_high * 0.9  # Weak momentum
            
            target_methods.append(adjusted_target)
        
        # Calculate final target price
        if target_methods:
            target_price = np.mean(target_methods)
        else:
            # Fallback: 15% upside target
            target_price = current_price * 1.15
        
        # Ensure target is reasonable (at least 5% upside, max 100% upside)
        target_price = max(current_price * 1.05, min(target_price, current_price * 2.0))
        
        upside_potential = (target_price - current_price) / current_price
        
        return {
            'current_price': current_price,
            'conservative_buy_price': conservative_buy,
            'aggressive_buy_price': aggressive_buy,
            'target_price': target_price,
            'upside_potential': upside_potential,
            'support_level': technical.get('support_level') if technical else current_price * 0.95,
            'resistance_level': technical.get('resistance_level') if technical else current_price * 1.05
        }
    
    def get_investment_recommendation(self, total_score: int, risk_score: int, upside_potential: float) -> str:
        """Get investment recommendation based on scores"""
        if total_score >= 80 and risk_score < 40 and upside_potential > 0.15:
            return "STRONG BUY"
        elif total_score >= 70 and risk_score < 50 and upside_potential > 0.10:
            return "BUY"
        elif total_score >= 60 and risk_score < 60:
            return "MODERATE BUY"
        elif total_score >= 50 and risk_score < 70:
            return "HOLD"
        elif total_score >= 40:
            return "WEAK HOLD"
        elif total_score >= 30:
            return "CONSIDER SELLING"
        else:
            return "SELL"
    
    def analyze_stock(self, symbol: str) -> Optional[Dict]:
        """Perform complete analysis of a stock"""
        try:
            logger.info(f"Analyzing {symbol}")
            
            # Get data from database
            price_data = self.db.get_price_data(symbol, days=252)
            fundamentals = self.db.get_latest_fundamentals(symbol)
            company_info = self.db.get_company(symbol)
            
            if price_data is None or price_data.empty:
                logger.warning(f"No price data available for {symbol}")
                return None
            
            # Calculate indicators
            technical = self.calculate_technical_indicators(price_data)
            performance = self.calculate_performance_metrics(price_data)
            
            # Calculate scores
            fundamental_score, fund_breakdown = self.score_fundamental_health(fundamentals)
            technical_score, tech_breakdown = self.score_technical_strength(technical)
            momentum_score, momentum_breakdown = self.score_momentum_quality(performance)
            risk_score, risk_breakdown = self.calculate_risk_score(technical, performance, fundamentals)
            
            # Calculate total score (ensure it's properly summed)
            total_score = int(fundamental_score + technical_score + momentum_score)
            
            # Calculate pricing
            pricing = self.calculate_target_pricing(symbol, fundamentals, technical, performance)
            
            # Get recommendation
            recommendation = self.get_investment_recommendation(
                total_score, risk_score, pricing['upside_potential']
            )
            
            # Compile analysis result
            analysis_result = {
                'symbol': symbol,
                'company_name': company_info.get('name', symbol) if company_info else symbol,
                'sector': company_info.get('sector', 'Unknown') if company_info else 'Unknown',
                'total_score': total_score,
                'fundamental_score': fundamental_score,
                'technical_score': technical_score,
                'momentum_score': momentum_score,
                'risk_score': risk_score,
                'risk_percentage': risk_score,
                'recommendation': recommendation,
                'pricing': pricing,
                'fundamentals': fundamentals or {},
                'technical': technical,
                'performance': performance,
                'breakdowns': {
                    'fundamental': fund_breakdown,
                    'technical': tech_breakdown,
                    'momentum': momentum_breakdown,
                    'risk': risk_breakdown
                },
                'analysis_date': datetime.now()
            }
            
            # Save to database
            self.db.save_analysis_result(analysis_result)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def analyze_multiple_stocks(self, symbols: List[str]) -> List[Dict]:
        """Analyze multiple stocks and return sorted results"""
        results = []
        
        for symbol in symbols:
            analysis = self.analyze_stock(symbol)
            if analysis:
                results.append(analysis)
        
        # Sort by total score (highest first)
        results.sort(key=lambda x: x['total_score'], reverse=True)
        
        return results
    
    def get_top_stocks(self, limit: int = 10, min_score: int = 60) -> List[Dict]:
        """Get top performing stocks from latest analyses"""
        try:
            all_analyses = self.db.get_all_latest_analyses()
            
            # Filter by minimum score and limit
            top_stocks = [
                analysis for analysis in all_analyses 
                if analysis['total_score'] >= min_score
            ][:limit]
            
            return top_stocks
            
        except Exception as e:
            logger.error(f"Error getting top stocks: {e}")
            return []