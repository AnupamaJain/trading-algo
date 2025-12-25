import argparse
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from brokers.integrations.fyers.driver import FyersDriver
from brokers.core.gateway import BrokerGateway
from pead_agent.engine import DecisionEngine
from pead_agent.execution import ExecutionManager
from pead_agent.tools.stubs import (
    StubPEADAnalyzer,
    StubTechnicalAnalyzer,
    StubFundamentalAnalyzer,
    StubNewsSentimentAnalyzer,
    StubGovernanceAnalyzer,
    StubInstitutionalFlowAnalyzer,
)
import yaml


def load_config():
    """Loads the YAML configuration file."""
    config_path = os.path.join(os.path.dirname(__file__), "config.yml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def main():
    """
    Main entry point for the PEAD Investment Agent.
    """
    # Load environment variables and configuration
    load_dotenv()
    config = load_config()

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

    # --- Setup Dependencies ---
    # Initialize the Fyers driver for live trading
    fyers_driver = FyersDriver()

    # Initialize the broker gateway with the Fyers driver
    broker_gateway = BrokerGateway(driver=fyers_driver, broker_name="fyers")

    # Initialize the execution manager
    execution_manager = ExecutionManager(broker_gateway=broker_gateway)

    # Initialize the decision engine with stubs and the loaded config
    engine = DecisionEngine(
        pead_analyzer=StubPEADAnalyzer(),
        technical_analyzer=StubTechnicalAnalyzer(),
        fundamental_analyzer=StubFundamentalAnalyzer(),
        news_analyzer=StubNewsSentimentAnalyzer(),
        governance_analyzer=StubGovernanceAnalyzer(),
        flow_analyzer=StubInstitutionalFlowAnalyzer(),
        execution_manager=execution_manager,
        config=config,
    )

    # Run the analysis, which now includes the execution step
    report = engine.run(args.symbol)
    print(report)


if __name__ == "__main__":
    main()
