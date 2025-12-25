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
    broker_config = config.get("broker", {})
    driver_name = broker_config.get("driver", "stub")

    if driver_name == "fyers":
        driver = FyersDriver()
        broker_name = "fyers"
    else:
        from brokers.stubs import StubBrokerDriver
        driver = StubBrokerDriver()
        broker_name = "stub"

    print(f"[Main] Using '{driver_name}' broker driver.")

    # Initialize the broker gateway
    broker_gateway = BrokerGateway(driver=driver, broker_name=broker_name)

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

    # Run the analysis to get the raw data
    analysis_data = engine.run_analysis(args.symbol)

    # Format the data into a string report and print it
    report_string = engine.format_report(analysis_data)
    print(report_string)


if __name__ == "__main__":
    main()
