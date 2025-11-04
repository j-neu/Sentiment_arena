"""
Constants for Sentiment Arena

This module contains constant values used throughout the application,
including stock symbols, market configuration, and other fixed values.
"""

# DAX 40 Stock Symbols (German Stock Market)
# These are the top 40 companies traded on the Frankfurt Stock Exchange
DAX_40_STOCKS = [
    # Top 10 by market cap
    "SAP.DE",           # SAP SE - Software
    "SIE.DE",           # Siemens AG - Industrial conglomerate
    "AIR.DE",           # Airbus SE - Aerospace
    "DTE.DE",           # Deutsche Telekom - Telecommunications
    "VOW3.DE",          # Volkswagen - Automotive
    "ALV.DE",           # Allianz SE - Insurance/Financial services
    "BAS.DE",           # BASF SE - Chemicals
    "MBG.DE",           # Mercedes-Benz Group - Automotive
    "BMW.DE",           # BMW - Automotive
    "MUV2.DE",          # Munich Re - Reinsurance

    # Next 10
    "DBK.DE",           # Deutsche Bank - Banking
    "DB1.DE",           # Deutsche Börse - Stock exchange operator
    "RWE.DE",           # RWE AG - Utilities
    "DHL.DE",           # DHL Group (Deutsche Post) - Logistics
    "1COV.DE",          # Covestro - Materials
    "HNR1.DE",          # Hannover Re - Reinsurance
    "HEI.DE",           # Heidelberg Materials - Building materials
    "EOAN.DE",          # E.ON SE - Utilities
    "SHL.DE",           # Siemens Healthineers - Healthcare
    "ZAL.DE",           # Zalando - E-commerce

    # Next 10
    "ADS.DE",           # Adidas - Sportswear
    "PUM.DE",           # Puma - Sportswear
    "HEN3.DE",          # Henkel - Consumer goods
    "BEI.DE",           # Beiersdorf - Consumer goods
    "FRE.DE",           # Fresenius SE - Healthcare
    "FME.DE",           # Fresenius Medical Care - Healthcare
    "MTX.DE",           # MTU Aero Engines - Aerospace
    "IFX.DE",           # Infineon - Semiconductors
    "SRT3.DE",          # Sartorius - Laboratory equipment
    "QIA.DE",           # QIAGEN - Biotechnology

    # Final 10
    "P911.DE",          # Porsche - Automotive
    "CON.DE",           # Continental - Automotive supplier
    "SY1.DE",           # Symrise - Flavors & fragrances
    "EVT.DE",           # Evotec - Biotechnology
    "G24.DE",           # Commerzbank - Banking
    "RHM.DE",           # Rheinmetall - Defense/Automotive
    "NEM.DE",           # Nemetschek - Software
    "WAF.DE",           # Siltronic (Wacker Chemie) - Semiconductors
    "VNA.DE",           # Vonovia - Real estate
    "LXS.DE",           # Lanxess - Specialty chemicals
]

# Top 10 DAX stocks for initial trading (most liquid)
DAX_TOP_10 = DAX_40_STOCKS[:10]

# Top 5 DAX stocks for testing (highest volume)
DAX_TOP_5 = DAX_40_STOCKS[:5]

# Stock categories for research
DAX_BY_SECTOR = {
    "Technology": ["SAP.DE", "IFX.DE", "NEM.DE"],
    "Automotive": ["VOW3.DE", "MBG.DE", "BMW.DE", "P911.DE", "CON.DE"],
    "Industrial": ["SIE.DE", "AIR.DE", "MTU.DE", "RHM.DE"],
    "Financial": ["ALV.DE", "MUV2.DE", "DBK.DE", "DB1.DE", "G24.DE"],
    "Healthcare": ["SHL.DE", "FRE.DE", "FME.DE", "QIA.DE", "EVT.DE"],
    "Consumer": ["ADS.DE", "PUM.DE", "HEN3.DE", "BEI.DE", "ZAL.DE"],
    "Chemicals": ["BAS.DE", "1COV.DE", "LXS.DE", "SY1.DE"],
    "Utilities": ["RWE.DE", "EOAN.DE"],
}

# Market configuration
MARKET_NAME = "XETRA"  # Frankfurt Stock Exchange
MARKET_TIMEZONE = "Europe/Berlin"
MARKET_CURRENCY = "EUR"

# Trading configuration defaults (can be overridden in settings)
DEFAULT_STARTING_CAPITAL = 1000.0
DEFAULT_TRADING_FEE = 5.0
DEFAULT_MAX_POSITION_SIZE = 0.3  # 30% of portfolio max per position
DEFAULT_MIN_TRADE_SIZE = 50.0    # Minimum €50 per trade
