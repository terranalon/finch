"""Generate test symbol files for batch price benchmark.

Run once to create test_symbols_500.txt and test_symbols_1000.txt.
"""

import pathlib

SCRIPT_DIR = pathlib.Path(__file__).parent

# S&P 500 components (503 symbols, Feb 2026)
SP500 = [
    "MMM", "AOS", "ABT", "ABBV", "ACN", "ADBE", "AMD", "AES", "AFL", "A",
    "APD", "ABNB", "AKAM", "ALB", "ARE", "ALGN", "ALLE", "LNT", "ALL", "GOOGL",
    "GOOG", "MO", "AMZN", "AMCR", "AEE", "AEP", "AXP", "AIG", "AMT", "AWK",
    "AMP", "AME", "AMGN", "APH", "ADI", "AON", "APA", "APO", "AAPL", "AMAT",
    "APP", "APTV", "ACGL", "ADM", "ARES", "ANET", "AJG", "AIZ", "T", "ATO",
    "ADSK", "ADP", "AZO", "AVB", "AVY", "AXON", "BKR", "BALL", "BAC", "BAX",
    "BDX", "BRK.B", "BBY", "TECH", "BIIB", "BLK", "BX", "XYZ", "BK", "BA",
    "BKNG", "BSX", "BMY", "AVGO", "BR", "BRO", "BF.B", "BLDR", "BG", "BXP",
    "CHRW", "CDNS", "CPT", "CPB", "COF", "CAH", "CCL", "CARR", "CVNA", "CAT",
    "CBOE", "CBRE", "CDW", "COR", "CNC", "CNP", "CF", "CRL", "SCHW", "CHTR",
    "CVX", "CMG", "CB", "CHD", "CIEN", "CI", "CINF", "CTAS", "CSCO", "C",
    "CFG", "CLX", "CME", "CMS", "KO", "CTSH", "COIN", "CL", "CMCSA", "FIX",
    "CAG", "COP", "ED", "STZ", "CEG", "COO", "CPRT", "GLW", "CPAY", "CTVA",
    "CSGP", "COST", "CTRA", "CRH", "CRWD", "CCI", "CSX", "CMI", "CVS", "DHR",
    "DRI", "DDOG", "DVA", "DECK", "DE", "DELL", "DAL", "DVN", "DXCM", "FANG",
    "DLR", "DG", "DLTR", "D", "DPZ", "DASH", "DOV", "DOW", "DHI", "DTE",
    "DUK", "DD", "ETN", "EBAY", "ECL", "EIX", "EW", "EA", "ELV", "EME",
    "EMR", "ETR", "EOG", "EPAM", "EQT", "EFX", "EQIX", "EQR", "ERIE", "ESS",
    "EL", "EG", "EVRG", "ES", "EXC", "EXE", "EXPE", "EXPD", "EXR", "XOM",
    "FFIV", "FDS", "FICO", "FAST", "FRT", "FDX", "FIS", "FITB", "FSLR", "FE",
    "FISV", "F", "FTNT", "FTV", "FOXA", "FOX", "BEN", "FCX", "GRMN", "IT",
    "GE", "GEHC", "GEV", "GEN", "GNRC", "GD", "GIS", "GM", "GPC", "GILD",
    "GPN", "GL", "GDDY", "GS", "HAL", "HIG", "HAS", "HCA", "DOC", "HSIC",
    "HSY", "HPE", "HLT", "HOLX", "HD", "HON", "HRL", "HST", "HWM", "HPQ",
    "HUBB", "HUM", "HBAN", "HII", "IBM", "IEX", "IDXX", "ITW", "INCY", "IR",
    "PODD", "INTC", "IBKR", "ICE", "IFF", "IP", "INTU", "ISRG", "IVZ", "INVH",
    "IQV", "IRM", "JBHT", "JBL", "JKHY", "J", "JNJ", "JCI", "JPM", "KVUE",
    "KDP", "KEY", "KEYS", "KMB", "KIM", "KMI", "KKR", "KLAC", "KHC", "KR",
    "LHX", "LH", "LRCX", "LW", "LVS", "LDOS", "LEN", "LII", "LLY", "LIN",
    "LYV", "LMT", "L", "LOW", "LULU", "LYB", "MTB", "MPC", "MAR", "MRSH",
    "MLM", "MAS", "MA", "MTCH", "MKC", "MCD", "MCK", "MDT", "MRK", "META",
    "MET", "MTD", "MGM", "MCHP", "MU", "MSFT", "MAA", "MRNA", "MOH", "TAP",
    "MDLZ", "MPWR", "MNST", "MCO", "MS", "MOS", "MSI", "MSCI", "NDAQ", "NTAP",
    "NFLX", "NEM", "NWSA", "NWS", "NEE", "NKE", "NI", "NDSN", "NSC", "NTRS",
    "NOC", "NCLH", "NRG", "NUE", "NVDA", "NVR", "NXPI", "ORLY", "OXY", "ODFL",
    "OMC", "ON", "OKE", "ORCL", "OTIS", "PCAR", "PKG", "PLTR", "PANW", "PSKY",
    "PH", "PAYX", "PAYC", "PYPL", "PNR", "PEP", "PFE", "PCG", "PM", "PSX",
    "PNW", "PNC", "POOL", "PPG", "PPL", "PFG", "PG", "PGR", "PLD", "PRU",
    "PEG", "PTC", "PSA", "PHM", "PWR", "QCOM", "DGX", "Q", "RL", "RJF",
    "RTX", "O", "REG", "REGN", "RF", "RSG", "RMD", "RVTY", "HOOD", "ROK",
    "ROL", "ROP", "ROST", "RCL", "SPGI", "CRM", "SNDK", "SBAC", "SLB", "STX",
    "SRE", "NOW", "SHW", "SPG", "SWKS", "SJM", "SW", "SNA", "SOLV", "SO",
    "LUV", "SWK", "SBUX", "STT", "STLD", "STE", "SYK", "SMCI", "SYF", "SNPS",
    "SYY", "TMUS", "TROW", "TTWO", "TPR", "TRGP", "TGT", "TEL", "TDY", "TER",
    "TSLA", "TXN", "TPL", "TXT", "TMO", "TJX", "TKO", "TTD", "TSCO", "TT",
    "TDG", "TRV", "TRMB", "TFC", "TYL", "TSN", "USB", "UBER", "UDR", "ULTA",
    "UNP", "UAL", "UPS", "URI", "UNH", "UHS", "VLO", "VTR", "VLTO", "VRSN",
    "VRSK", "VZ", "VRTX", "VTRS", "VICI", "V", "VST", "VMC", "WRB", "GWW",
    "WAB", "WMT", "DIS", "WBD", "WM", "WAT", "WEC", "WFC", "WELL", "WST",
    "WDC", "WY", "WSM", "WMB", "WTW", "WDAY", "WYNN", "XEL", "XYL", "YUM",
    "ZBRA", "ZBH", "ZTS",
]

# International ETFs
INTL_ETFS = [
    "VEA", "VWO", "EFA", "IEMG", "ACWI", "EEM", "INDA", "EWJ", "EWZ", "EWG",
    "EWT", "EWY", "EWA", "EWC", "EWU", "FXI", "MCHI", "THD", "EPOL", "TUR",
    "KWEB", "CQQQ", "GXC", "EIDO", "EPHE", "ECH", "EWW", "EWS", "EWH", "ENZL",
    "EWN", "EWD", "EWL", "EWI", "EWP", "EWQ", "EWK", "EDEN", "EFNL", "NORW",
    "PGAL", "GREK", "EIRL", "EIS", "QAT", "UAE", "KSA", "FLSA", "FLKR", "RSX",
]

# Israeli stocks (.TA)
ISRAELI_TA = [
    "TEVA.TA", "NICE.TA", "CHKP.TA", "MNRT.TA", "LUMI.TA", "DSCT.TA",
    "ESLT.TA", "BEZQ.TA", "ICL.TA", "POLI.TA", "CAMT.TA", "KRNT.TA",
    "SILC.TA", "FNTS.TA", "MZTF.TA", "HARL.TA", "ORA.TA", "AMOT.TA",
    "MGDL.TA", "ALHE.TA", "ARPT.TA", "FORTY.TA", "ELCO.TA", "NAWI.TA",
    "SKBN.TA", "SPNS.TA", "DLEKG.TA", "ENLT.TA", "BRMG.TA", "DIMRI.TA",
]

# Sector and bond ETFs
SECTOR_BOND_ETFS = [
    "XLF", "XLK", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XLRE",
    "XLC", "BND", "AGG", "TLT", "IEF", "SHY", "LQD", "HYG", "TIP", "VTIP",
    "MUB", "EMB", "BNDX", "IGOV", "BWX", "SPTL", "SPAB", "SPTS", "SPIB", "SPSB",
    "GOVT", "VMBS", "MBB", "GNMA", "FLOT", "NEAR", "GSY", "MINT", "SHV", "BIL",
    "JPST", "PULS", "IGSB", "VCSH", "VCIT", "VCLT", "VGSH", "VGIT", "VGLT", "SCHZ",
]

# Small/mid-cap US stocks (from Russell 2000 / S&P 600)
SMALL_MID_CAP = [
    "INSM", "SATS", "ASTS", "BE", "FTAI", "FN", "CRS", "ATI", "APG", "RVMD",
    "BBIO", "ITCI", "MDGL", "KTOS", "GH", "MTSI", "SMMT", "MLI", "AVAV", "HL",
    "CDE", "RNA", "RMBS", "AMKR", "DY", "SPXC", "ENSG", "COKE", "DDS", "STRL",
    "AIT", "COOP", "SITM", "SSB", "ALTR", "ARWR", "WTS", "GTLS", "AXSM", "SANM",
    "UMBF", "ONB", "IDCC", "LSI", "AEIS", "BPMC", "STEP", "APPF", "HALO", "IMGN",
    "ONTO", "GSAT", "CTRE", "IESC", "CADE", "CMC", "LUMN", "SFM", "HQY", "APLD",
    "HLNE", "HIMS", "CYTK", "CERE", "MOD", "TTMI", "IBP", "BECN", "KRYS", "PRIM",
    "RYTM", "SMTC", "FCFS", "CRK", "SSD", "PFSI", "FSS", "URBN", "FLR", "PJT",
    "EAT", "EXLS", "PSN", "VLY", "RRR", "AAON", "ESNT", "GKOS", "ROAD", "UEC",
    "SUM", "CWST", "PTCT", "TRNO", "GATX", "PCVX", "RHP", "EPRT", "COMP", "ANF",
    "PIPR", "KYMR", "WFRD", "GBCI", "OPEN", "SWX", "TMHC", "BOOT", "LMND", "ENS",
    "IRTC", "ETRN", "CVLT", "RDNT", "HOMB", "HWC", "POR", "PTGX", "BIPC", "PI",
    "MTDR", "UBSI", "UFPI", "KRG", "PNM", "MC", "RIOT", "REZI", "CNX", "BKH",
    "VICR", "ACA", "OPCH", "BMI", "GVA", "MMSI", "ESE", "SNEX", "MCY", "SIGI",
    "ABCB", "HRI", "AUB", "CHX", "ESGR", "BCPC", "HPP", "MAC", "LEU", "GPI",
    "AX", "CSWI", "SR", "LAUR", "ZETA", "MMS", "RDN", "BCO", "GOLF", "SKY",
    "SBRA", "GHC", "TDS", "QLYS", "ACIW", "MTH", "HCC", "CVCO", "AROC", "BDC",
    "ALKS", "NNI", "WK", "TGTX", "OGS", "ELF", "MUR", "NJR", "NPO", "ABG",
    "FORM", "WIRE", "LNTH", "LANC", "AGX", "AKRO", "DOCN", "AEO", "UPST", "ACAD",
    "FOLD", "AEL", "QTWO", "OSIS", "SLAB", "ITRI", "FELE", "IRT", "OSCR", "FFIN",
    "MGY", "NMRK", "VCTR", "ASB", "ADMA", "POWL", "BGC", "VSEC", "TCBI", "TMDX",
    "EBC", "FTDR", "IBOC", "GMS", "CRC", "BOX", "CNO", "SKYW", "PLXS", "VIAV",
    "ALHC", "COMM", "CORT", "ENVA", "HASI", "HGV", "VKTX", "NOVT", "JBT", "MDC",
    "AMRX", "NWE", "SXT", "ALE", "MATX", "SFBS", "GLNG", "HAE", "CENX", "SKT",
    "PSMT", "CALM", "ATGE", "DORM", "VRNS", "MARA", "MWA", "UCBI", "LGND", "CARG",
    "BTU", "GNW", "PATK", "NHI", "FIBK", "INDB", "TEX", "KBH", "CBT", "SHAK",
    "SLG", "CALX", "BANF", "EXPO", "PLMR", "ZION", "FHN", "CMA", "WTFC", "BANR",
    "PNFP", "FNB", "SBCF",
]


def _deduplicated(*lists: list[str]) -> list[str]:
    """Merge lists preserving order, removing duplicates."""
    seen: set[str] = set()
    result: list[str] = []
    for lst in lists:
        for sym in lst:
            if sym not in seen:
                seen.add(sym)
                result = [*result, sym]
    return result


def _fake_symbols(n: int) -> list[str]:
    return [f"FAKE{i:03d}" for i in range(1, n + 1)]


def build_500() -> list[str]:
    """Build 500-symbol test set."""
    # Start with 400 S&P 500, add extras, pad/trim to 500
    symbols = _deduplicated(
        SP500[:400],
        INTL_ETFS[:30],
        ISRAELI_TA[:15],
        SECTOR_BOND_ETFS[:20],
        SMALL_MID_CAP[:20],
    )
    fake = _fake_symbols(15)
    symbols = [*symbols, *fake]
    return symbols[:500]


def build_1000() -> list[str]:
    """Build 1000-symbol test set."""
    symbols = _deduplicated(
        SP500,
        INTL_ETFS,
        ISRAELI_TA,
        SECTOR_BOND_ETFS,
        SMALL_MID_CAP,
    )
    fake = _fake_symbols(70)
    symbols = [*symbols, *fake]
    # Pad with additional well-known tickers if needed
    extra = [
        "RIVN", "LCID", "NIO", "XPEV", "LI", "PLBY", "SOFI", "AFRM", "RBLX",
        "DKNG", "ABNB", "SNOW", "CRSP", "EDIT", "NTLA", "BEAM", "VERV", "TWST",
        "IOVA", "SANA", "FATE", "ALNY", "IONS", "SRPT", "BMRN", "RARE", "ARGX",
        "NBIX", "UTHR", "EXEL", "PCOR", "ZI", "PATH", "BRZE", "CFLT", "MNDY",
        "GTLB", "ESTC", "NEWR", "DOMO", "PRGS", "SMAR", "CWAN", "FIVN", "BAND",
        "LPSN", "CCSI", "TOST", "TOAST", "DLO", "PAYO", "FLYW", "BILL", "SHOP",
    ]
    symbols = _deduplicated(symbols, extra)
    return symbols[:1000]


def main() -> None:
    for name, builder in [("500", build_500), ("1000", build_1000)]:
        symbols = builder()
        path = SCRIPT_DIR / f"test_symbols_{name}.txt"
        path.write_text("\n".join(symbols) + "\n")
        print(f"Wrote {len(symbols)} symbols to {path.name}")


if __name__ == "__main__":
    main()
