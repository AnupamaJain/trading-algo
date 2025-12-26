from abc import ABC, abstractmethod

from datetime import date
from typing import Optional

class PEADAnalyzerBase(ABC):
    """Abstract base class for PEAD analysis."""
    @abstractmethod
    def analyze(self, stock_symbol: str, analysis_date: Optional[date] = None) -> dict:
        """
        Analyzes a stock for PEAD signals.

        Args:
            stock_symbol: The ticker symbol of the stock.
            analysis_date: The date for which to perform the analysis (for backtesting).

        Returns:
            A dictionary containing PEAD analysis results.
        """
        pass

class TechnicalAnalyzerBase(ABC):
    """Abstract base class for technical analysis."""
    @abstractmethod
    def analyze(self, stock_symbol: str, analysis_date: Optional[date] = None) -> dict:
        """
        Performs technical analysis on a stock.

        Args:
            stock_symbol: The ticker symbol of the stock.
            analysis_date: The date for which to perform the analysis (for backtesting).

        Returns:
            A dictionary containing technical analysis results.
        """
        pass

class FundamentalAnalyzerBase(ABC):
    """Abstract base class for fundamental analysis."""
    @abstractmethod
    def analyze(self, stock_symbol: str, analysis_date: Optional[date] = None) -> dict:
        """
        Performs fundamental analysis on a stock.

        Args:
            stock_symbol: The ticker symbol of the stock.
            analysis_date: The date for which to perform the analysis (for backtesting).

        Returns:
            A dictionary containing fundamental analysis results.
        """
        pass

class NewsSentimentAnalyzerBase(ABC):
    """Abstract base class for news and sentiment analysis."""
    @abstractmethod
    def analyze(self, stock_symbol: str, analysis_date: Optional[date] = None) -> dict:
        """
        Analyzes news and sentiment for a stock.

        Args:
            stock_symbol: The ticker symbol of the stock.
            analysis_date: The date for which to perform the analysis (for backtesting).

        Returns:
            A dictionary containing news and sentiment analysis results.
        """
        pass

class GovernanceAnalyzerBase(ABC):
    """Abstract base class for corporate governance analysis."""
    @abstractmethod
    def analyze(self, stock_symbol: str, analysis_date: Optional[date] = None) -> dict:
        """
        Performs corporate governance analysis on a stock.

        Args:
            stock_symbol: The ticker symbol of the stock.
            analysis_date: The date for which to perform the analysis (for backtesting).

        Returns:
            A dictionary containing governance analysis results.
        """
        pass

class InstitutionalFlowAnalyzerBase(ABC):
    """Abstract base class for institutional flow analysis."""
    @abstractmethod
    def analyze(self, stock_symbol: str, analysis_date: Optional[date] = None) -> dict:
        """
        Analyzes institutional flow for a stock.

        Args:
            stock_symbol: The ticker symbol of the stock.
            analysis_date: The date for which to perform the analysis (for backtesting).

        Returns:
            A dictionary containing institutional flow analysis results.
        """
        pass
