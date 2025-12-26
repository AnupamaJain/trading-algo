from datetime import date
from typing import Optional
from pead_agent.tools.base import (
    PEADAnalyzerBase,
    TechnicalAnalyzerBase,
    FundamentalAnalyzerBase,
    NewsSentimentAnalyzerBase,
    GovernanceAnalyzerBase,
    InstitutionalFlowAnalyzerBase,
)

# --- Historical Scenarios ---
# This dictionary simulates different analysis results for a stock on specific dates.
# This allows the backtester to test different decision paths.
HISTORICAL_DATA = {
    "RELIANCE": {
        date(2023, 1, 15): {
            "pead": {"PEAD Verdict": "PASS", "PEAD Score": "8.0/10"},
            "tech": {"Technical Bias": "Bullish"},
            "fund": {"Fundamental Bias": "Strong"},
            "gov": {"Risk Level": "Low"},
        },
        date(2023, 3, 10): {
            "pead": {"PEAD Verdict": "PASS", "PEAD Score": "7.5/10"},
            "tech": {"Technical Bias": "Neutral"},
            "fund": {"Fundamental Bias": "Strong"},
            "gov": {"Risk Level": "Low"},
        },
        date(2023, 5, 20): {
            "pead": {"PEAD Verdict": "FAIL", "PEAD Score": "4.0/10"},
            "tech": {"Technical Bias": "Bearish"},
            "fund": {"Fundamental Bias": "Average"},
            "gov": {"Risk Level": "Low"},
        },
    }
}

class HistoricalPEADAnalyzer(PEADAnalyzerBase):
    def analyze(self, stock_symbol: str, analysis_date: Optional[date] = None) -> dict:
        data = HISTORICAL_DATA.get(stock_symbol, {}).get(analysis_date, {})
        return data.get("pead", {"PEAD Verdict": "FAIL"})

class HistoricalTechnicalAnalyzer(TechnicalAnalyzerBase):
    def analyze(self, stock_symbol: str, analysis_date: Optional[date] = None) -> dict:
        data = HISTORICAL_DATA.get(stock_symbol, {}).get(analysis_date, {})
        return data.get("tech", {"Technical Bias": "Neutral"})

class HistoricalFundamentalAnalyzer(FundamentalAnalyzerBase):
    def analyze(self, stock_symbol: str, analysis_date: Optional[date] = None) -> dict:
        data = HISTORICAL_DATA.get(stock_symbol, {}).get(analysis_date, {})
        return data.get("fund", {"Fundamental Bias": "Average"})

class HistoricalGovernanceAnalyzer(GovernanceAnalyzerBase):
    def analyze(self, stock_symbol: str, analysis_date: Optional[date] = None) -> dict:
        data = HISTORICAL_DATA.get(stock_symbol, {}).get(analysis_date, {})
        return data.get("gov", {"Risk Level": "Low"})

# --- Generic Stubs for Unused Analyzers ---
# For the backtest, we only need to simulate the core decision factors.
# The other analyzers can return generic, non-influential data.

class StubNewsSentimentAnalyzer(NewsSentimentAnalyzerBase):
    def analyze(self, stock_symbol: str, analysis_date: Optional[date] = None) -> dict:
        return {"Sentiment Bias": "Neutral"}

class StubInstitutionalFlowAnalyzer(InstitutionalFlowAnalyzerBase):
    def analyze(self, stock_symbol: str, analysis_date: Optional[date] = None) -> dict:
        return {"FII/DII Activity": "Mixed"}
