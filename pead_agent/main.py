import argparse
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pead_agent.engine import DecisionEngine
from pead_agent.tools.stubs import (
    StubPEADAnalyzer,
    StubTechnicalAnalyzer,
    StubFundamentalAnalyzer,
    StubNewsSentimentAnalyzer,
    StubGovernanceAnalyzer,
    StubInstitutionalFlowAnalyzer,
)

def main():
    """
    Main entry point for the PEAD Investment Agent.
    """
    parser = argparse.ArgumentParser(
        description="PEAD Investment Agent - A multi-factor analysis tool for Indian equities."
    )
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="The stock ticker symbol to analyze (e.g., RELIANCE).",
    )
    args = parser.parse_args()

    # Initialize the decision engine with stub implementations
    engine = DecisionEngine(
        pead_analyzer=StubPEADAnalyzer(),
        technical_analyzer=StubTechnicalAnalyzer(),
        fundamental_analyzer=StubFundamentalAnalyzer(),
        news_analyzer=StubNewsSentimentAnalyzer(),
        governance_analyzer=StubGovernanceAnalyzer(),
        flow_analyzer=StubInstitutionalFlowAnalyzer(),
    )

    # Run the analysis and print the report
    report = engine.run_analysis(args.symbol)
    print(report)

if __name__ == "__main__":
    main()
