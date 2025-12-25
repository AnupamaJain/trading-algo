from abc import ABC, abstractmethod

class PEADAnalyzerBase(ABC):
    """Abstract base class for PEAD analysis."""
    @abstractmethod
    def analyze(self, stock_symbol: str) -> dict:
        """
        Analyzes a stock for PEAD signals.

        Args:
            stock_symbol: The ticker symbol of the stock.

        Returns:
            A dictionary containing PEAD analysis results.
        """
        pass

class TechnicalAnalyzerBase(ABC):
    """Abstract base class for technical analysis."""
    @abstractmethod
    def analyze(self, stock_symbol: str) -> dict:
        """
        Performs technical analysis on a stock.

        Args:
            stock_symbol: The ticker symbol of the stock.

        Returns:
            A dictionary containing technical analysis results.
        """
        pass

class FundamentalAnalyzerBase(ABC):
    """Abstract base class for fundamental analysis."""
    @abstractmethod
    def analyze(self, stock_symbol: str) -> dict:
        """
        Performs fundamental analysis on a stock.

        Args:
            stock_symbol: The ticker symbol of the stock.

        Returns:
            A dictionary containing fundamental analysis results.
        """
        pass

class NewsSentimentAnalyzerBase(ABC):
    """Abstract base class for news and sentiment analysis."""
    @abstractmethod
    def analyze(self, stock_symbol: str) -> dict:
        """
        Analyzes news and sentiment for a stock.

        Args:
            stock_symbol: The ticker symbol of the stock.

        Returns:
            A dictionary containing news and sentiment analysis results.
        """
        pass

class GovernanceAnalyzerBase(ABC):
    """Abstract base class for corporate governance analysis."""
    @abstractmethod
    def analyze(self, stock_symbol: str) -> dict:
        """
        Performs corporate governance analysis on a stock.

        Args:
            stock_symbol: The ticker symbol of the stock.

        Returns:
            A dictionary containing governance analysis results.
        """
        pass

class InstitutionalFlowAnalyzerBase(ABC):
    """Abstract base class for institutional flow analysis."""
    @abstractmethod
    def analyze(self, stock_symbol: str) -> dict:
        """
        Analyzes institutional flow for a stock.

        Args:
            stock_symbol: The ticker symbol of the stock.

        Returns:
            A dictionary containing institutional flow analysis results.
        """
        pass
