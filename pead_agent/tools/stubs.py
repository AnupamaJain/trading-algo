from pead_agent.tools.base import (
    PEADAnalyzerBase,
    TechnicalAnalyzerBase,
    FundamentalAnalyzerBase,
    NewsSentimentAnalyzerBase,
    GovernanceAnalyzerBase,
    InstitutionalFlowAnalyzerBase,
)

class StubPEADAnalyzer(PEADAnalyzerBase):
    """Stub implementation for PEAD analysis."""
    def analyze(self, stock_symbol: str) -> dict:
        return {
            "PEAD Score": "8.5/10",
            "Earnings Surprise": "+15%",
            "Drift Direction": "Positive",
            "PEAD Verdict": "PASS",
        }

class StubTechnicalAnalyzer(TechnicalAnalyzerBase):
    """Stub implementation for technical analysis."""
    def analyze(self, stock_symbol: str) -> dict:
        return {
            "Trend": "Bullish (Daily & Weekly)",
            "Key Indicators": "RSI > 60, MACD Crossover, Above 50/200 EMA",
            "Support / Resistance": "S: 1000, R: 1200",
            "Technical Bias": "Bullish",
        }

class StubFundamentalAnalyzer(FundamentalAnalyzerBase):
    """Stub implementation for fundamental analysis."""
    def analyze(self, stock_symbol: str) -> dict:
        return {
            "Growth Summary": "Revenue +20% YoY, PAT +25% YoY",
            "Valuation Check": "PE Ratio (30) vs. Growth (25%) - Fairly Valued",
            "Fundamental Bias": "Strong",
        }

class StubNewsSentimentAnalyzer(NewsSentimentAnalyzerBase):
    """Stub implementation for news and sentiment analysis."""
    def analyze(self, stock_symbol: str) -> dict:
        return {
            "Key Headlines": "Positive management commentary on earnings call.",
            "Sentiment Bias": "Positive",
        }

class StubGovernanceAnalyzer(GovernanceAnalyzerBase):
    """Stub implementation for corporate governance analysis."""
    def analyze(self, stock_symbol: str) -> dict:
        return {
            "SEBI / Legal Issues": "None reported.",
            "Risk Level": "Low",
        }

class StubInstitutionalFlowAnalyzer(InstitutionalFlowAnalyzerBase):
    """Stub implementation for institutional flow analysis."""
    def analyze(self, stock_symbol: str) -> dict:
        return {
            "FII/DII Activity": "Recent buying from DIIs.",
            "Promoter Activity": "No change in promoter holding.",
        }
