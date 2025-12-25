import sys
import os
from flask import Flask, jsonify

# Ensure the project root is on the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pead_agent.main import load_config
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

app = Flask(__name__)

# --- Global Engine Initialization ---
decision_engine = None

def initialize_engine():
    """Initializes the decision engine and its dependencies."""
    global decision_engine
    if decision_engine is None:
        print("Initializing Decision Engine for the first time...")
        load_dotenv()
        config = load_config()

        broker_config = config.get("broker", {})
        driver_name = broker_config.get("driver", "stub")

        if driver_name == "fyers":
            driver = FyersDriver()
            broker_name = "fyers"
        else:
            from brokers.stubs import StubBrokerDriver
            driver = StubBrokerDriver()
            broker_name = "stub"

        print(f"[API Server] Using '{driver_name}' broker driver.")

        broker_gateway = BrokerGateway(driver=driver, broker_name=broker_name)
        execution_manager = ExecutionManager(broker_gateway=broker_gateway)

        decision_engine = DecisionEngine(
            pead_analyzer=StubPEADAnalyzer(),
            technical_analyzer=StubTechnicalAnalyzer(),
            fundamental_analyzer=StubFundamentalAnalyzer(),
            news_analyzer=StubNewsSentimentAnalyzer(),
            governance_analyzer=StubGovernanceAnalyzer(),
            flow_analyzer=StubInstitutionalFlowAnalyzer(),
            execution_manager=execution_manager,
            config=config,
        )
        print("Decision Engine initialized.")

@app.route('/api/analyze/<string:stock_symbol>', methods=['GET'])
def analyze_stock(stock_symbol):
    """
    Runs the PEAD analysis for a given stock symbol and returns the data as JSON.
    """
    if decision_engine is None:
        return jsonify({"error": "Decision engine not initialized"}), 500

    try:
        analysis_data = decision_engine.run_analysis(stock_symbol.upper())
        return jsonify(analysis_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    initialize_engine()
    # Note: This is a development server. For production, use a proper WSGI server like Gunicorn.
    app.run(debug=True, port=5000)
