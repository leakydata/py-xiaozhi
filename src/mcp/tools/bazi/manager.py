"""
BaZi Manager. Responsible for BaZi analysis and fortune calculation core functions.
"""

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BaziManager:
    """
    BaZi Manager.
    """

    def __init__(self):
        """
        Initialize BaZi manager.
        """

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        Initialize and register all BaZi tools.
        """
        from .marriage_tools import (
            analyze_marriage_compatibility,
            analyze_marriage_timing,
        )
        from .tools import (
            build_bazi_from_lunar_datetime,
            build_bazi_from_solar_datetime,
            get_bazi_detail,
            get_chinese_calendar,
            get_solar_times,
        )

        # Get BaZi details (primary tool)
        bazi_detail_props = PropertyList(
            [
                Property("solar_datetime", PropertyType.STRING, default_value=""),
                Property("lunar_datetime", PropertyType.STRING, default_value=""),
                Property("gender", PropertyType.INTEGER, default_value=1),
                Property(
                    "eight_char_provider_sect", PropertyType.INTEGER, default_value=2
                ),
            ]
        )
        add_tool(
            (
                "self.bazi.get_bazi_detail",
                "Get complete BaZi fortune analysis information based on time (solar or lunar) and gender. "
                "This is the core tool for BaZi analysis, providing comprehensive fortune interpretation.\n"
                "Use cases:\n"
                "1. Personal BaZi fortune analysis\n"
                "2. Birth chart inquiry\n"
                "3. Fortune consultation and interpretation\n"
                "4. Marriage compatibility analysis\n"
                "5. Fortune trend base data\n"
                "\nFeatures:\n"
                "- Supports both solar and lunar time input\n"
                "- Provides complete Four Pillars BaZi information\n"
                "- Includes Shen Sha, Decade Fortune, punishment/clash/combination/meeting analysis\n"
                "- Supports different Zi hour calculation configurations\n"
                "\nParameter description:\n"
                "  solar_datetime: Solar time, ISO format, e.g. '2008-03-01T13:00:00+08:00'\n"
                "  lunar_datetime: Lunar time, e.g. '2000-5-5 12:00:00'\n"
                "  gender: Gender, 0=Female, 1=Male\n"
                "  eight_char_provider_sect: Early/late Zi hour config, 1=23:00-23:59 day stem is next day, 2=current day (default)\n"
                "\nNote: Either solar_datetime or lunar_datetime must be provided, but not both",
                bazi_detail_props,
                get_bazi_detail,
            )
        )

        # Get solar times from BaZi
        solar_times_props = PropertyList([Property("bazi", PropertyType.STRING)])
        add_tool(
            (
                "self.bazi.get_solar_times",
                "Calculate possible solar time list from BaZi. Returned time format: YYYY-MM-DD hh:mm:ss.\n"
                "Use cases:\n"
                "1. Reverse calculate birth time from BaZi\n"
                "2. Verify BaZi accuracy\n"
                "3. Find historical time points with the same BaZi\n"
                "4. BaZi time verification\n"
                "\nFeatures:\n"
                "- Calculate time based on BaZi stem-branch combinations\n"
                "- Support querying multiple possible times\n"
                "- Configurable time range\n"
                "\nParameter description:\n"
                "  bazi: BaZi, in order of Year Pillar, Month Pillar, Day Pillar, Hour Pillar, separated by spaces\n"
                "        Example: '戊寅 己未 己卯 辛未'",
                solar_times_props,
                get_solar_times,
            )
        )

        # Get Chinese calendar information
        chinese_calendar_props = PropertyList(
            [Property("solar_datetime", PropertyType.STRING, default_value="")]
        )
        add_tool(
            (
                "self.bazi.get_chinese_calendar",
                "Get Chinese traditional calendar (Huang Li) information for the specified solar time (defaults to today). "
                "Provides complete lunar date, Gan-Zhi, suitable/unsuitable activities, Shen Sha directions, etc.\n"
                "Use cases:\n"
                "1. Query today's calendar suitable/unsuitable activities\n"
                "2. Date and time selection reference\n"
                "3. Traditional festival inquiry\n"
                "4. Feng Shui direction guidance\n"
                "5. Folk culture understanding\n"
                "\nFeatures:\n"
                "- Complete lunar information\n"
                "- Twenty-eight Mansions and solar term information\n"
                "- Shen Sha direction guidance\n"
                "- Pengzu taboo reminders\n"
                "- Traditional festival marking\n"
                "- Suitable/unsuitable activity suggestions\n"
                "\nParameter description:\n"
                "  solar_datetime: Solar time, ISO format, e.g. '2008-03-01T13:00:00+08:00'\n"
                "                 If not provided, defaults to current time",
                chinese_calendar_props,
                get_chinese_calendar,
            )
        )

        # Get BaZi from lunar time (deprecated)
        lunar_bazi_props = PropertyList(
            [
                Property("lunar_datetime", PropertyType.STRING),
                Property("gender", PropertyType.INTEGER, default_value=1),
                Property(
                    "eight_char_provider_sect", PropertyType.INTEGER, default_value=2
                ),
            ]
        )
        add_tool(
            (
                "self.bazi.build_bazi_from_lunar_datetime",
                "Get BaZi information from lunar time and gender.\n"
                "Note: This tool is deprecated, use get_bazi_detail instead.\n"
                "\nParameter description:\n"
                "  lunar_datetime: Lunar time, e.g.: '2000-5-15 12:00:00'\n"
                "  gender: Gender, 0=Female, 1=Male\n"
                "  eight_char_provider_sect: Early/late Zi hour configuration",
                lunar_bazi_props,
                build_bazi_from_lunar_datetime,
            )
        )

        # Get BaZi from solar time (deprecated)
        solar_bazi_props = PropertyList(
            [
                Property("solar_datetime", PropertyType.STRING),
                Property("gender", PropertyType.INTEGER, default_value=1),
                Property(
                    "eight_char_provider_sect", PropertyType.INTEGER, default_value=2
                ),
            ]
        )
        add_tool(
            (
                "self.bazi.build_bazi_from_solar_datetime",
                "Get BaZi information from solar time and gender.\n"
                "Note: This tool is deprecated, use get_bazi_detail instead.\n"
                "\nParameter description:\n"
                "  solar_datetime: Solar time, ISO format, e.g. '2008-03-01T13:00:00+08:00'\n"
                "  gender: Gender, 0=Female, 1=Male\n"
                "  eight_char_provider_sect: Early/late Zi hour configuration",
                solar_bazi_props,
                build_bazi_from_solar_datetime,
            )
        )

        # Marriage timing analysis
        marriage_timing_props = PropertyList(
            [
                Property("solar_datetime", PropertyType.STRING, default_value=""),
                Property("lunar_datetime", PropertyType.STRING, default_value=""),
                Property("gender", PropertyType.INTEGER, default_value=1),
                Property(
                    "eight_char_provider_sect", PropertyType.INTEGER, default_value=2
                ),
            ]
        )
        add_tool(
            (
                "self.bazi.analyze_marriage_timing",
                "Analyze marriage timing, spouse characteristics, and marriage quality. "
                "Specialized fortune analysis for marriage-related matters, including wedding time prediction, spouse characteristics, etc.\\n"
                "Use cases:\\n"
                "1. Predict best marriage timing\\n"
                "2. Analyze spouse appearance and personality traits\\n"
                "3. Assess marriage quality and stability\\n"
                "4. Identify potential marriage obstacles\\n"
                "5. Find favorable marriage years\\n"
                "\\nFeatures:\\n"
                "- Spouse star strength analysis\\n"
                "- Marriage age range prediction\\n"
                "- Spouse palace detailed interpretation\\n"
                "- Marriage obstacle identification\\n"
                "- Favorable time recommendation\\n"
                "\\nParameter description:\\n"
                "  solar_datetime: Solar time, ISO format, e.g. '2008-03-01T13:00:00+08:00'\\n"
                "  lunar_datetime: Lunar time, e.g. '2000-5-5 12:00:00'\\n"
                "  gender: Gender, 0=Female, 1=Male\\n"
                "  eight_char_provider_sect: Early/late Zi hour configuration\\n"
                "\\nNote: Either solar_datetime or lunar_datetime must be provided, but not both",
                marriage_timing_props,
                analyze_marriage_timing,
            )
        )

        # Marriage compatibility analysis
        marriage_compatibility_props = PropertyList(
            [
                Property("male_solar_datetime", PropertyType.STRING, default_value=""),
                Property("male_lunar_datetime", PropertyType.STRING, default_value=""),
                Property(
                    "female_solar_datetime", PropertyType.STRING, default_value=""
                ),
                Property(
                    "female_lunar_datetime", PropertyType.STRING, default_value=""
                ),
            ]
        )
        add_tool(
            (
                "self.bazi.analyze_marriage_compatibility",
                "Analyze marriage compatibility between two people's BaZi, evaluate marriage match degree and relationship patterns. "
                "Compare both parties' BaZi to analyze marriage compatibility and considerations.\\n"
                "Use cases:\\n"
                "1. Pre-marriage compatibility analysis\\n"
                "2. Evaluate compatibility between both parties\\n"
                "3. Identify relationship issues\\n"
                "4. Get marriage improvement suggestions\\n"
                "5. Choose best wedding timing\\n"
                "\\nFeatures:\\n"
                "- Five Elements matching analysis\\n"
                "- Zodiac compatibility assessment\\n"
                "- Day Pillar combination evaluation\\n"
                "- Comprehensive compatibility scoring\\n"
                "- Specific improvement suggestions\\n"
                "\\nParameter description:\\n"
                "  male_solar_datetime: Male's solar time\\n"
                "  male_lunar_datetime: Male's lunar time\\n"
                "  female_solar_datetime: Female's solar time\\n"
                "  female_lunar_datetime: Female's lunar time\\n"
                "\\nNote: For each party, only one of solar or lunar time is needed",
                marriage_compatibility_props,
                analyze_marriage_compatibility,
            )
        )


# Global manager instance
_bazi_manager = None


def get_bazi_manager() -> BaziManager:
    """
    Get BaZi manager singleton.
    """
    global _bazi_manager
    if _bazi_manager is None:
        _bazi_manager = BaziManager()
    return _bazi_manager
