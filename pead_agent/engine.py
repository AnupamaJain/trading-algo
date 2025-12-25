from pead_agent.tools.base import (
    PEADAnalyzerBase,
    TechnicalAnalyzerBase,
    FundamentalAnalyzerBase,
    NewsSentimentAnalyzerBase,
    GovernanceAnalyzerBase,
    InstitutionalFlowAnalyzerBase,
)

class DecisionEngine:
    """
    Orchestrates the multi-tool analysis pipeline and makes a final decision.
    """
    def __init__(
        self,
        pead_analyzer: PEADAnalyzerBase,
        technical_analyzer: TechnicalAnalyzerBase,
        fundamental_analyzer: FundamentalAnalyzerBase,
        news_analyzer: NewsSentimentAnalyzerBase,
        governance_analyzer: GovernanceAnalyzerBase,
        flow_analyzer: InstitutionalFlowAnalyzerBase,
    ):
        self.pead_analyzer = pead_analyzer
        self.technical_analyzer = technical_analyzer
        self.fundamental_analyzer = fundamental_analyzer
        self.news_analyzer = news_analyzer
        self.governance_analyzer = governance_analyzer
        self.flow_analyzer = flow_analyzer

    def run_analysis(self, stock_symbol: str) -> str:
        """
        Runs the full analysis pipeline for a given stock symbol.

        Args:
            stock_symbol: The ticker symbol of the stock to analyze.

        Returns:
            A formatted string containing the complete analysis report.
        """
        # --- 1. Run all analyses ---
        pead_results = self.pead_analyzer.analyze(stock_symbol)

        # PEAD is a mandatory filter
        if pead_results.get("PEAD Verdict") != "PASS":
            final_verdict = "REJECT"
            confidence = 0
            risks = "Stock did not pass the initial PEAD filter."
            # Set default values for other results to avoid errors in formatting
            tech_results = {"Trend": "N/A", "Key Indicators": "N/A", "Support / Resistance": "N/A", "Technical Bias": "N/A"}
            fund_results = {"Growth Summary": "N/A", "Valuation Check": "N/A", "Fundamental Bias": "N/A"}
            news_results = {"Key Headlines": "N/A", "Sentiment Bias": "N/A"}
            gov_results = {"SEBI / Legal Issues": "N/A", "Risk Level": "N/A"}
            flow_results = {"FII/DII Activity": "N/A", "Promoter Activity": "N/A"}
        else:
            tech_results = self.technical_analyzer.analyze(stock_symbol)
            fund_results = self.fundamental_analyzer.analyze(stock_symbol)
            news_results = self.news_analyzer.analyze(stock_symbol)
            gov_results = self.governance_analyzer.analyze(stock_symbol)
            flow_results = self.flow_analyzer.analyze(stock_symbol)

            # --- 2. Apply Decision Logic ---
            final_verdict = "HOLD"  # Default verdict if not rejected
            confidence = 50  # Neutral confidence
            risks_list = []

            # Rule: HIGH governance risk -> IMMEDIATE REJECT
            if gov_results.get("Risk Level", "").lower() in ["medium", "high"]:
                final_verdict = "REJECT"
                confidence = 0
                risks_list.append("Medium to High governance risk detected.")

            # Rule: PEAD + Technical + Fundamentals MUST align for BUY
            is_pead_strong = pead_results.get("PEAD Verdict") == "PASS"
            is_tech_bullish = tech_results.get("Technical Bias", "").lower() == "bullish"
            is_fund_strong = fund_results.get("Fundamental Bias", "").lower() == "strong"

            if final_verdict != "REJECT":
                if is_pead_strong and is_tech_bullish and is_fund_strong:
                    final_verdict = "STRONG BUY"
                    confidence = 90
                elif is_pead_strong and is_tech_bullish:
                    final_verdict = "BUY"
                    confidence = 75
                elif is_pead_strong and not is_tech_bullish:
                    final_verdict = "HOLD"
                    confidence = 60
                    risks_list.append("PEAD signal is positive, but technicals are weak or neutral.")

            if not is_fund_strong:
                risks_list.append("Fundamentals are average or weak.")

            risks = ", ".join(risks_list) if risks_list else "Standard market risks apply."

        # --- 3. Format the Output ---
        report = f"""
--------------------------------------------------
STOCK: {stock_symbol}
MARKET: NSE / BSE

PEAD ANALYSIS:
- PEAD Score: {pead_results.get('PEAD Score', 'N/A')}
- Earnings Surprise: {pead_results.get('Earnings Surprise', 'N/A')}
- Drift Direction: {pead_results.get('Drift Direction', 'N/A')}
- PEAD Verdict: {pead_results.get('PEAD Verdict', 'N/A')}

TECHNICAL ANALYSIS:
- Trend: {tech_results.get('Trend', 'N/A')}
- Key Indicators: {tech_results.get('Key Indicators', 'N/A')}
- Support / Resistance: {tech_results.get('Support / Resistance', 'N/A')}
- Technical Bias: {tech_results.get('Technical Bias', 'N/A')}

FUNDAMENTAL ANALYSIS:
- Growth Summary: {fund_results.get('Growth Summary', 'N/A')}
- Valuation Check: {fund_results.get('Valuation Check', 'N/A')}
- Fundamental Bias: {fund_results.get('Fundamental Bias', 'N/A')}

NEWS & SENTIMENT:
- Key Headlines: {news_results.get('Key Headlines', 'N/A')}
- Sentiment Bias: {news_results.get('Sentiment Bias', 'N/A')}

GOVERNANCE & FRAUD CHECK:
- SEBI / Legal Issues: {gov_results.get('SEBI / Legal Issues', 'N/A')}
- Risk Level: {gov_results.get('Risk Level', 'N/A')}

INSTITUTIONAL FLOW:
- FII/DII Activity: {flow_results.get('FII/DII Activity', 'N/A')}
- Promoter Activity: {flow_results.get('Promoter Activity', 'N/A')}

FINAL DECISION:
- Verdict: {final_verdict}
- Confidence Score: {confidence}
- Time Horizon: Swing / Positional
- Key Risks: {risks}
--------------------------------------------------
"""
        return report.strip()
