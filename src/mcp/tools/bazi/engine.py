"""
BaZi calculation core engine.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pendulum
from lunar_python import Lunar, Solar

from .models import (
    ChineseCalendar,
    EarthBranch,
    EightChar,
    HeavenStem,
    LunarTime,
    SixtyCycle,
    SolarTime,
)
from .professional_data import (
    GAN,
    GAN_WUXING,
    GAN_YINYANG,
    GANZHI_60,
    SHENG_XIAO,
    ZHI,
    ZHI_CANG_GAN,
    ZHI_WUXING,
    ZHI_YINYANG,
)


class BaziEngine:
    """BaZi Calculation Engine"""

    # Dynamically build Heavenly Stem mapping - based on professional_data.py data
    HEAVEN_STEMS = {}
    for gan in GAN:
        HEAVEN_STEMS[gan] = HeavenStem(
            name=gan,
            element=GAN_WUXING[gan],
            yin_yang=GAN_YINYANG[gan]
        )

    # Dynamically build Earthly Branch mapping - based on professional_data.py data
    EARTH_BRANCHES = {}
    for i, zhi in enumerate(ZHI):
        # Get hidden stems of the Earthly Branch
        cang_gan = ZHI_CANG_GAN.get(zhi, {})
        cang_gan_list = list(cang_gan.keys())

        # Build EarthBranch object
        EARTH_BRANCHES[zhi] = EarthBranch(
            name=zhi,
            element=ZHI_WUXING[zhi],
            yin_yang=ZHI_YINYANG[zhi],
            zodiac=SHENG_XIAO[i],
            hide_heaven_main=cang_gan_list[0] if len(cang_gan_list) > 0 else None,
            hide_heaven_middle=cang_gan_list[1] if len(cang_gan_list) > 1 else None,
            hide_heaven_residual=cang_gan_list[2] if len(cang_gan_list) > 2 else None,
        )

    def __init__(self):
        """
        Initialize.
        """

    def parse_solar_time(self, iso_date: str) -> SolarTime:
        """
        Parse solar time string (supports multiple formats) - optimized with pendulum, enhanced timezone handling.
        """
        try:
            # Parse time using pendulum, supports more formats
            dt = pendulum.parse(iso_date)

            # Smart timezone handling
            if dt.timezone_name == "UTC":
                # If pendulum parses as UTC (meaning the original input had no timezone), treat as Beijing time
                dt = dt.replace(tzinfo=pendulum.timezone("Asia/Shanghai"))
            elif dt.timezone_name is None:
                # If no timezone info, set to Beijing time
                dt = dt.replace(tzinfo=pendulum.timezone("Asia/Shanghai"))
            elif dt.timezone_name != "Asia/Shanghai":
                # Convert to Beijing time
                dt = dt.in_timezone("Asia/Shanghai")

            return SolarTime(
                year=dt.year,
                month=dt.month,
                day=dt.day,
                hour=dt.hour,
                minute=dt.minute,
                second=dt.second,
            )
        except Exception as e:
            # If pendulum parsing fails, try other formats
            formats = [
                "%Y-%m-%dT%H:%M:%S+08:00",
                "%Y-%m-%dT%H:%M:%S+0800",
                "%Y-%m-%dT%H:%M:%S.%f+08:00",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M+08:00",
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d %H:%M",
                "%Y/%m/%d",
                "%Y年%m月%d日 %H时%M分%S秒",
                "%Y年%m月%d日 %H时%M分",
                "%Y年%m月%d日",
            ]

            dt = None
            for fmt in formats:
                try:
                    dt = datetime.strptime(iso_date, fmt)
                    break
                except ValueError:
                    continue

            if dt is None:
                raise ValueError(
                    f"Unable to parse time format: {iso_date}, supported formats include ISO8601, Chinese format, etc."
                )

            return SolarTime(
                year=dt.year,
                month=dt.month,
                day=dt.day,
                hour=dt.hour,
                minute=dt.minute,
                second=dt.second,
            )

    def solar_to_lunar(self, solar_time: SolarTime) -> LunarTime:
        """
        Solar to Lunar conversion - enhanced leap month handling.
        """
        try:
            # Use lunar-python for actual solar-to-lunar conversion
            solar = Solar.fromYmdHms(
                solar_time.year,
                solar_time.month,
                solar_time.day,
                solar_time.hour,
                solar_time.minute,
                solar_time.second,
            )
            lunar = solar.getLunar()

            # Check if it's a leap month
            is_leap = lunar.isLeap() if hasattr(lunar, "isLeap") else False

            # If lunar-python doesn't have isLeap method, use another approach
            if not hasattr(lunar, "isLeap"):
                # Check via the month string (if it contains the leap character)
                month_str = lunar.getMonthInChinese()
                is_leap = "闰" in month_str

            return LunarTime(
                year=lunar.getYear(),
                month=lunar.getMonth(),
                day=lunar.getDay(),
                hour=lunar.getHour(),
                minute=lunar.getMinute(),
                second=lunar.getSecond(),
                is_leap=is_leap,
            )
        except Exception as e:
            raise ValueError(f"Solar to lunar conversion failed: {e}")

    def lunar_to_solar(self, lunar_time: LunarTime) -> SolarTime:
        """
        Lunar to Solar conversion - enhanced leap month handling.
        """
        try:
            # Handle leap month
            if lunar_time.is_leap:
                # If it's a leap month, use special method to create lunar object
                lunar = Lunar.fromYmdHms(
                    lunar_time.year,
                    -lunar_time.month,  # Leap month uses negative number
                    lunar_time.day,
                    lunar_time.hour,
                    lunar_time.minute,
                    lunar_time.second,
                )
            else:
                # Normal month
                lunar = Lunar.fromYmdHms(
                    lunar_time.year,
                    lunar_time.month,
                    lunar_time.day,
                    lunar_time.hour,
                    lunar_time.minute,
                    lunar_time.second,
                )

            solar = lunar.getSolar()

            return SolarTime(
                year=solar.getYear(),
                month=solar.getMonth(),
                day=solar.getDay(),
                hour=solar.getHour(),
                minute=solar.getMinute(),
                second=solar.getSecond(),
            )
        except Exception as e:
            raise ValueError(f"Lunar to solar conversion failed: {e}")

    def build_eight_char(self, solar_time: SolarTime) -> EightChar:
        """
        Build the Eight Characters (BaZi).
        """
        try:
            # Use lunar-python to calculate BaZi
            solar = Solar.fromYmdHms(
                solar_time.year,
                solar_time.month,
                solar_time.day,
                solar_time.hour,
                solar_time.minute,
                solar_time.second,
            )
            lunar = solar.getLunar()
            bazi = lunar.getEightChar()

            # Get Year Pillar
            year_gan = bazi.getYearGan()
            year_zhi = bazi.getYearZhi()
            year_cycle = self._create_sixty_cycle(year_gan, year_zhi)

            # Get Month Pillar
            month_gan = bazi.getMonthGan()
            month_zhi = bazi.getMonthZhi()
            month_cycle = self._create_sixty_cycle(month_gan, month_zhi)

            # Get Day Pillar
            day_gan = bazi.getDayGan()
            day_zhi = bazi.getDayZhi()
            day_cycle = self._create_sixty_cycle(day_gan, day_zhi)

            # Get Hour Pillar
            time_gan = bazi.getTimeGan()
            time_zhi = bazi.getTimeZhi()
            time_cycle = self._create_sixty_cycle(time_gan, time_zhi)

            return EightChar(
                year=year_cycle, month=month_cycle, day=day_cycle, hour=time_cycle
            )
        except Exception as e:
            raise ValueError(f"Failed to build BaZi: {e}")

    def _create_sixty_cycle(self, gan_name: str, zhi_name: str) -> SixtyCycle:
        """
        Create a Sixty Jiazi (Sexagenary Cycle) object.
        """
        heaven_stem = self.HEAVEN_STEMS[gan_name]
        earth_branch = self.EARTH_BRANCHES[zhi_name]

        # Calculate NaYin
        try:
            # Use NaYin data
            sound = self._get_nayin(gan_name, zhi_name)
        except Exception as e:
            # Log the specific error, but don't affect overall functionality
            print(f"NaYin calculation failed: {gan_name}{zhi_name} - {e}")
            sound = "Unknown"

        # Calculate the Decade and Void - simplified implementation
        ten = self._get_ten(gan_name, zhi_name)
        extra_branches = self._get_kong_wang(gan_name, zhi_name)

        return SixtyCycle(
            heaven_stem=heaven_stem,
            earth_branch=earth_branch,
            sound=sound,
            ten=ten,
            extra_earth_branches=extra_branches,
        )

    def _get_nayin(self, gan: str, zhi: str) -> str:
        """Get NaYin"""
        from .professional_data import get_nayin

        return get_nayin(gan, zhi)

    def _get_ten(self, gan: str, zhi: str) -> str:
        """Get Decade - using Sixty Jiazi Decade Void algorithm"""
        from .professional_data import GAN, ZHI

        try:
            # Use standard Sixty Jiazi calculation method
            gan_idx = GAN.index(gan)
            zhi_idx = ZHI.index(zhi)

            # Calculate the ordinal number in the Sixty Jiazi (starting from 1)
            jiazi_number = (gan_idx * 6 + zhi_idx * 5) % 60
            if jiazi_number == 0:
                jiazi_number = 60

            # Decade heads of the six decades
            xun_starts = ["甲子", "甲戌", "甲申", "甲午", "甲辰", "甲寅"]

            # Determine which decade (every 10 is one decade)
            xun_index = (jiazi_number - 1) // 10

            if 0 <= xun_index < len(xun_starts):
                return xun_starts[xun_index]
            else:
                # Use more precise calculation method
                return self._calculate_xun_by_position(jiazi_number)
        except (ValueError, IndexError) as e:
            print(f"Decade calculation failed: {gan}{zhi} - {e}")
            return "甲子"

    def _get_kong_wang(self, gan: str, zhi: str) -> List[str]:
        """Get Void (Kong Wang) - using traditional Decade Void algorithm"""
        from .professional_data import GAN, ZHI

        try:
            gan_idx = GAN.index(gan)
            zhi_idx = ZHI.index(zhi)

            # Calculate the ordinal number in the Sixty Jiazi
            jiazi_number = (gan_idx * 6 + zhi_idx * 5) % 60
            if jiazi_number == 0:
                jiazi_number = 60

            # Determine which decade
            xun_index = (jiazi_number - 1) // 10

            # Void Earthly Branches for the six decades
            kong_wang_table = [
                ["戌", "亥"],  # Jia Zi Decade
                ["申", "酉"],  # Jia Xu Decade
                ["午", "未"],  # Jia Shen Decade
                ["辰", "巳"],  # Jia Wu Decade
                ["寅", "卯"],  # Jia Chen Decade
                ["子", "丑"],  # Jia Yin Decade
            ]

            if 0 <= xun_index < len(kong_wang_table):
                return kong_wang_table[xun_index]
            else:
                # Backup calculation method
                return self._calculate_kong_wang_by_position(jiazi_number)
        except (ValueError, IndexError) as e:
            print(f"Void calculation failed: {gan}{zhi} - {e}")
            return ["戌", "亥"]  # Default to Jia Zi Decade void

    def format_solar_time(self, solar_time: SolarTime) -> str:
        """
        Format solar time.
        """
        return f"{solar_time.year}Y{solar_time.month}M{solar_time.day}D {solar_time.hour}h{solar_time.minute}m{solar_time.second}s"

    def format_lunar_time(self, lunar_time: LunarTime) -> str:
        """
        Format lunar time.
        """
        return f"Lunar {lunar_time.year}Y{lunar_time.month}M{lunar_time.day}D {lunar_time.hour}h{lunar_time.minute}m{lunar_time.second}s"

    def get_chinese_calendar(
        self, solar_time: Optional[SolarTime] = None
    ) -> ChineseCalendar:
        """Get Chinese traditional calendar information - using lunar-python"""
        if solar_time is None:
            # Use today
            now = pendulum.now("Asia/Shanghai")
            solar_time = SolarTime(
                now.year, now.month, now.day, now.hour, now.minute, now.second
            )

        try:
            solar = Solar.fromYmdHms(
                solar_time.year,
                solar_time.month,
                solar_time.day,
                solar_time.hour,
                solar_time.minute,
                solar_time.second,
            )
            lunar = solar.getLunar()

            # Get detailed information
            bazi = lunar.getEightChar()

            return ChineseCalendar(
                solar_date=self.format_solar_time(solar_time),
                lunar_date=f"{lunar.getYearInChinese()}Y {lunar.getMonthInChinese()}M {lunar.getDayInChinese()}",
                gan_zhi=f"{bazi.getYear()} {bazi.getMonth()} {bazi.getDay()}",
                zodiac=lunar.getYearShengXiao(),
                na_yin=lunar.getDayNaYin(),
                lunar_festival=(
                    ", ".join(lunar.getFestivals()) if lunar.getFestivals() else None
                ),
                solar_festival=(
                    ", ".join(solar.getFestivals()) if solar.getFestivals() else None
                ),
                solar_term=lunar.getJieQi() or "None",
                twenty_eight_star=lunar.getXiu(),
                pengzu_taboo=lunar.getPengZuGan() + " " + lunar.getPengZuZhi(),
                joy_direction=lunar.getPositionXi(),
                yang_direction=lunar.getPositionYangGui(),
                yin_direction=lunar.getPositionYinGui(),
                mascot_direction=lunar.getPositionFu(),
                wealth_direction=lunar.getPositionCai(),
                clash=f"Clash {lunar.getDayChongDesc()}",
                suitable=", ".join(lunar.getDayYi()[:5]),  # Take top 5
                avoid=", ".join(lunar.getDayJi()[:5]),  # Take top 5
            )
        except Exception as e:
            raise ValueError(f"Failed to get Chinese calendar info: {e}")

    def _calculate_xun_by_position(self, jiazi_number: int) -> str:
        """Calculate Decade by Sixty Jiazi ordinal number"""
        # From professional_data.py using GANZHI_60
        # Decade heads of each decade
        xun_starts = ["甲子", "甲戌", "甲申", "甲午", "甲辰", "甲寅"]

        xun_index = (jiazi_number - 1) // 10
        if 0 <= xun_index < len(xun_starts):
            return xun_starts[xun_index]
        else:
            return "甲子"

    def _calculate_kong_wang_by_position(self, jiazi_number: int) -> List[str]:
        """Calculate Void by Sixty Jiazi ordinal number"""
        # Void Earthly Branches for the six decades
        kong_wang_table = [
            ["戌", "亥"],  # Jia Zi Decade
            ["申", "酉"],  # Jia Xu Decade
            ["午", "未"],  # Jia Shen Decade
            ["辰", "巳"],  # Jia Wu Decade
            ["寅", "卯"],  # Jia Chen Decade
            ["子", "丑"],  # Jia Yin Decade
        ]

        xun_index = (jiazi_number - 1) // 10
        if 0 <= xun_index < len(kong_wang_table):
            return kong_wang_table[xun_index]
        else:
            return ["戌", "亥"]

    def get_detailed_lunar_info(self, solar_time: SolarTime) -> Dict[str, Any]:
        """Get detailed lunar information"""
        try:
            solar = Solar.fromYmdHms(
                solar_time.year,
                solar_time.month,
                solar_time.day,
                solar_time.hour,
                solar_time.minute,
                solar_time.second,
            )
            lunar = solar.getLunar()

            # Get solar term information
            current_jieqi = lunar.getJieQi()
            next_jieqi = lunar.getNextJieQi()
            prev_jieqi = lunar.getPrevJieQi()

            # Get more traditional information
            return {
                "current_jieqi": current_jieqi,
                "next_jieqi": next_jieqi.toString() if next_jieqi else None,
                "prev_jieqi": prev_jieqi.toString() if prev_jieqi else None,
                "lunar_festivals": lunar.getFestivals(),
                "solar_festivals": solar.getFestivals(),
                "twenty_eight_star": lunar.getXiu(),
                "day_position": {
                    "xi": lunar.getPositionXi(),
                    "yang_gui": lunar.getPositionYangGui(),
                    "yin_gui": lunar.getPositionYinGui(),
                    "fu": lunar.getPositionFu(),
                    "cai": lunar.getPositionCai(),
                },
                "pengzu_taboo": {
                    "gan": lunar.getPengZuGan(),
                    "zhi": lunar.getPengZuZhi(),
                },
                "day_suitable": lunar.getDayYi(),
                "day_avoid": lunar.getDayJi(),
                "day_clash": lunar.getDayChongDesc(),
            }
        except Exception as e:
            print(f"Failed to get detailed lunar info: {e}")
            return {}


# Global engine instance
_bazi_engine = None


def get_bazi_engine() -> BaziEngine:
    """
    Get BaZi engine singleton.
    """
    global _bazi_engine
    if _bazi_engine is None:
        _bazi_engine = BaziEngine()
    return _bazi_engine
