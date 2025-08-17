"""
Core algorithm for Bazi numerology analysis.
"""
from typing import Any, Dict, List, Optional
from .engine import get_bazi_engine
from .models import BaziAnalysis, EightChar, LunarTime, SolarTime
from .professional_analyzer import get_professional_analyzer

class BaziCalculator:
    """
    Bazi Analysis Calculator.
    """

    def __init__(self):
        self.engine = get_bazi_engine()
        self.professional_analyzer = get_professional_analyzer()

    def build_hide_heaven_object(
        self, heaven_stem: Optional[str], day_master: str
    ) -> Optional[Dict[str, str]]:
        """
        Build hide heaven object.
        """
        if not heaven_stem:
            return None

        return {
            "Heavenly Stem": heaven_stem,
            "Ten Gods": self._get_ten_star(day_master, heaven_stem),
        }

    def _get_ten_star(self, day_master: str, other_stem: str) -> str:
        """
        Calculate Ten Gods relationship.
        """
        return self.professional_analyzer.get_ten_gods_analysis(day_master, other_stem)

    def build_sixty_cycle_object(
        self, sixty_cycle, day_master: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build Sixty Cycle object.
        """
        heaven_stem = sixty_cycle.get_heaven_stem()
        earth_branch = sixty_cycle.get_earth_branch()

        current_day_master = day_master if day_master else heaven_stem.name

        return {
            "Heavenly Stem": {
                "Heavenly Stem": heaven_stem.name,
                "Five Elements": heaven_stem.element,
                "Yin Yang": "Yang" if heaven_stem.yin_yang == 1 else "Yin",
                "Ten Gods": (
                    None
                    if current_day_master == heaven_stem.name
                    else self._get_ten_star(current_day_master, heaven_stem.name)
                ),
            },
            "Earthly Branch": {
                "Earthly Branch": earth_branch.name,
                "Five Elements": earth_branch.element,
                "Yin Yang": "Yang" if earth_branch.yin_yang == 1 else "Yin",
                "Hidden Stems": {
                    "Main Qi": self.build_hide_heaven_object(
                        earth_branch.hide_heaven_main, current_day_master
                    ),
                    "Middle Qi": self.build_hide_heaven_object(
                        earth_branch.hide_heaven_middle, current_day_master
                    ),
                    "Residual Qi": self.build_hide_heaven_object(
                        earth_branch.hide_heaven_residual, current_day_master
                    ),
                },
            },
            "Sound": sixty_cycle.sound,
            "Decade": sixty_cycle.ten,
            "Void": "".join(sixty_cycle.extra_earth_branches),
            "Star Luck": self._get_terrain(current_day_master, earth_branch.name),
            "Self-seated": self._get_terrain(heaven_stem.name, earth_branch.name),
        }

    def _get_terrain(self, stem: str, branch: str) -> str:
        """
        Calculate Twelve Changsheng.
        """
        from .professional_data import get_changsheng_state

        return get_changsheng_state(stem, branch)

    def build_gods_object(
        self, eight_char: EightChar, gender: int
    ) -> Dict[str, List[str]]:
        """
        Build Gods object.
        """
        from .professional_data import get_shensha

        # Get Bazi stems and branches
        eight_char.year.heaven_stem.name
        eight_char.month.heaven_stem.name
        day_gan = eight_char.day.heaven_stem.name
        eight_char.hour.heaven_stem.name 

        year_zhi = eight_char.year.earth_branch.name
        month_zhi = eight_char.month.earth_branch.name
        day_zhi = eight_char.day.earth_branch.name
        hour_zhi = eight_char.hour.earth_branch.name

        # Shen Sha for each pillar
        result = {"Year Pillar": [], "Month Pillar": [], "Day Pillar": [], "Hour Pillar": []}

        # Tianyi Nobleman (based on day stem)
        tianyi = get_shensha(day_gan, "tianyi")
        if tianyi:
            for zhi in [year_zhi, month_zhi, day_zhi, hour_zhi]:
                if zhi in tianyi:
                    if zhi == year_zhi:
                        result["Year Pillar"].append("Tianyi Nobleman")
                    if zhi == month_zhi:
                        result["Month Pillar"].append("Tianyi Nobleman")
                    if zhi == day_zhi:
                        result["Day Pillar"].append("Tianyi Nobleman")
                    if zhi == hour_zhi:
                        result["Hour Pillar"].append("Tianyi Nobleman")

        # Wenchang Nobleman (based on day stem)
        wenchang = get_shensha(day_gan, "wenchang")
        if wenchang:
            for zhi in [year_zhi, month_zhi, day_zhi, hour_zhi]:
                if zhi == wenchang:
                    if zhi == year_zhi:
                        result["Year Pillar"].append("Wenchang Nobleman")
                    if zhi == month_zhi:
                        result["Month Pillar"].append("Wenchang Nobleman")
                    if zhi == day_zhi:
                        result["Day Pillar"].append("Wenchang Nobleman")
                    if zhi == hour_zhi:
                        result["Hour Pillar"].append("Wenchang Nobleman")

        # Yima Star (based on day branch)
        yima = get_shensha(day_zhi, "yima")
        if yima:
            for zhi in [year_zhi, month_zhi, day_zhi, hour_zhi]:
                if zhi == yima:
                    if zhi == year_zhi:
                        result["Year Pillar"].append("Yima Star")
                    if zhi == month_zhi:
                        result["Month Pillar"].append("Yima Star")
                    if zhi == day_zhi:
                        result["Day Pillar"].append("Yima Star")
                    if zhi == hour_zhi:
                        result["Hour Pillar"].append("Yima Star")

        # Taohua Star (based on day branch)
        taohua = get_shensha(day_zhi, "taohua")
        if taohua:
            for zhi in [year_zhi, month_zhi, day_zhi, hour_zhi]:
                if zhi == taohua:
                    if zhi == year_zhi:
                        result["Year Pillar"].append("Taohua Star")
                    if zhi == month_zhi:
                        result["Month Pillar"].append("Taohua Star")
                    if zhi == day_zhi:
                        result["Day Pillar"].append("Taohua Star")
                    if zhi == hour_zhi:
                        result["Hour Pillar"].append("Taohua Star")

        # Huagai Star (based on day branch)
        huagai = get_shensha(day_zhi, "huagai")
        if huagai:
            for zhi in [year_zhi, month_zhi, day_zhi, hour_zhi]:
                if zhi == huagai:
                    if zhi == year_zhi:
                        result["Year Pillar"].append("Huagai Star")
                    if zhi == month_zhi:
                        result["Month Pillar"].append("Huagai Star")
                    if zhi == day_zhi:
                        result["Day Pillar"].append("Huagai Star")
                    if zhi == hour_zhi:
                        result["Hour Pillar"].append("Huagai Star")

        return result

    def build_decade_fortune_object(
        self, solar_time: SolarTime, eight_char: EightChar, gender: int, day_master: str
    ) -> Dict[str, Any]:
        """
        Build Decade Fortune object.
        """
        # Get the Yin-Yang of the year pillar
        year_yin_yang = eight_char.year.heaven_stem.yin_yang
        month_gan = eight_char.month.heaven_stem.name
        month_zhi = eight_char.month.earth_branch.name

        fortune_list = []

        # Use professional calculation for starting age of fortune
        start_age = self._calculate_start_age(solar_time, eight_char, gender)

        for i in range(10):  # Calculate 10 steps of decade fortune
            age_start = start_age + i * 10
            age_end = age_start + 9
            year_start = solar_time.year + age_start
            year_end = solar_time.year + age_end

            # Use professional algorithm to calculate decade fortune Ganzhi
            fortune_gz = self._calculate_fortune_ganzhi(
                month_gan, month_zhi, i + 1, gender, year_yin_yang
            )
            
            # Separate decade fortune Heavenly Stem and Earthly Branch
            fortune_gan = fortune_gz[0]
            fortune_zhi = fortune_gz[1]
            
            # Calculate the Ten Gods relationship of the hidden stems in the Earthly Branch
            from .professional_data import ZHI_CANG_GAN
            zhi_ten_gods = []
            zhi_canggan = []
            
            if fortune_zhi in ZHI_CANG_GAN:
                canggan_data = ZHI_CANG_GAN[fortune_zhi]
                for hidden_gan, strength in canggan_data.items():
                    ten_god = self._get_ten_star(day_master, hidden_gan)
                    zhi_ten_gods.append(f"{ten_god}({hidden_gan})")
                    zhi_canggan.append(f"{hidden_gan}({strength})")

            fortune_list.append(
                {
                    "Ganzhi": fortune_gz,
                    "Start Year": year_start,
                    "End": year_end,
                    "Heavenly Stem Ten Gods": self._get_ten_star(day_master, fortune_gan),
                    "Earthly Branch Ten Gods": zhi_ten_gods if zhi_ten_gods else [f"Earthly Branch{fortune_zhi}"],
                    "Earthly Branch Hidden Stems": zhi_canggan if zhi_canggan else [fortune_zhi],
                    "Start Age": age_start,
                    "End Age": age_end,
                }
            )

        return {
            "Fortune Start Date": f"{solar_time.year + start_age}-{solar_time.month}-{solar_time.day}",
            "Fortune Start Age": start_age,
            "Decade Fortune": fortune_list,
        }

    def _calculate_fortune_ganzhi(
        self, month_gan: str, month_zhi: str, step: int, gender: int, year_yin_yang: int
    ) -> str:
        """Calculate Decade Fortune Ganzhi"""
        from .professional_data import GAN, ZHI

        # Determine the direction of the decade fortune: Yang male and Yin female go forward, Yin male and Yang female go backward
        if (gender == 1 and year_yin_yang == 1) or (
            gender == 0 and year_yin_yang == -1
        ):
            # Forward
            direction = 1
        else:
            # Backward
            direction = -1

        # Calculate decade fortune starting from the month pillar
        month_gan_idx = GAN.index(month_gan)
        month_zhi_idx = ZHI.index(month_zhi)

        # Calculate the Ganzhi index of the current decade fortune
        fortune_gan_idx = (month_gan_idx + step * direction) % 10
        fortune_zhi_idx = (month_zhi_idx + step * direction) % 12

        return GAN[fortune_gan_idx] + ZHI[fortune_zhi_idx]

    def build_bazi(
        self,
        solar_datetime: Optional[str] = None,
        lunar_datetime: Optional[str] = None,
        gender: int = 1,
        eight_char_provider_sect: int = 2,
    ) -> BaziAnalysis:
        """
        Build Bazi analysis.
        """

        if not solar_datetime and not lunar_datetime:
            raise ValueError("solarDatetime and lunarDatetime must be passed, and only one of them.")

        if solar_datetime:
            solar_time = self.engine.parse_solar_time(solar_datetime)
            lunar_time = self.engine.solar_to_lunar(solar_time)
        else:
            # Process lunar time
            if lunar_datetime:
                lunar_dt = self._parse_lunar_datetime(lunar_datetime)
                lunar_time = lunar_dt
                solar_time = self._lunar_to_solar(lunar_dt)
            else:
                raise ValueError("lunar_datetime cannot be None when solar_datetime is not provided.")


        # Build Bazi
        eight_char = self.engine.build_eight_char(solar_time)
        day_master = eight_char.day.heaven_stem.name

        # The zodiac should be calculated using the lunar year, not the Bazi year pillar (because the start of spring and the Spring Festival are at different times).
        zodiac = self._get_zodiac_by_lunar_year(solar_time)

        # Build analysis result
        analysis = BaziAnalysis(
            gender=["Female", "Male"][gender],
            solar_time=self.engine.format_solar_time(solar_time),
            lunar_time=str(lunar_time),
            bazi=str(eight_char),
            zodiac=zodiac,
            day_master=day_master,
            year_pillar=self.build_sixty_cycle_object(eight_char.year, day_master),
            month_pillar=self.build_sixty_cycle_object(eight_char.month, day_master),
            day_pillar=self.build_sixty_cycle_object(eight_char.day),
            hour_pillar=self.build_sixty_cycle_object(eight_char.hour, day_master),
            fetal_origin=self._calculate_fetal_origin(eight_char),
            fetal_breath=self._calculate_fetal_breath(eight_char),
            own_sign=self._calculate_own_sign(eight_char),
            body_sign=self._calculate_body_sign(eight_char),
            gods=self.build_gods_object(eight_char, gender),
            fortune=self.build_decade_fortune_object(
                solar_time, eight_char, gender, day_master
            ),
            relations=self._build_relations_object(eight_char),
        )

        # Enhance result with professional analyzer
        try:
            # Directly use Bazi data for professional analysis
            eight_char_dict = eight_char.to_dict()
            detailed_analysis = self.professional_analyzer.analyze_eight_char_structure(
                eight_char_dict
            )
            detailed_text = self.professional_analyzer.get_detailed_fortune_analysis(
                eight_char_dict
            )

            # Add professional analysis result to the return object
            analysis.professional_analysis = detailed_analysis
            analysis.detailed_fortune_text = detailed_text
        except Exception as e:
            # If professional analysis fails, log the error but do not affect basic functionality
            analysis.professional_analysis = {"error": f"Professional analysis failed: {e}"}
            analysis.detailed_fortune_text = f"Professional analysis module is temporarily unavailable: {e}"

        return analysis

    def _parse_lunar_datetime(self, lunar_datetime: str) -> LunarTime:
        """
        Parse lunar datetime string - supports multiple formats.
        """
        import re
        from datetime import datetime

        # Support Chinese lunar format: 农历2024年三月初八 [时间]
        chinese_match = re.match(r"农历(\d{4})年(\S+)月(\S+)(?:\s+(.+))?", lunar_datetime)
        if chinese_match:
            year = int(chinese_match.group(1))
            month_str = chinese_match.group(2)
            day_str = chinese_match.group(3)
            time_str = chinese_match.group(4)  # Possible time part

            # Convert Chinese month and day
            month = self._chinese_month_to_number(month_str)
            day = self._chinese_day_to_number(day_str)
            
            # Parse time part
            hour, minute, second = self._parse_time_part(time_str)

            return LunarTime(
                year=year,
                month=month,
                day=day,
                hour=hour,
                minute=minute,
                second=second,
            )

        # Support standard format
        try:
            # Try ISO format
            dt = datetime.fromisoformat(lunar_datetime)
        except ValueError:
            # Try other common formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d %H:%M",
                "%Y/%m/%d",
            ]

            dt = None
            for fmt in formats:
                try:
                    dt = datetime.strptime(lunar_datetime, fmt)
                    break
                except ValueError:
                    continue

            if dt is None:
                raise ValueError(f"Unable to parse lunar datetime format: {lunar_datetime}")

        return LunarTime(
            year=dt.year,
            month=dt.month,
            day=dt.day,
            hour=dt.hour,
            minute=dt.minute,
            second=dt.second,
        )

    def _lunar_to_solar(self, lunar_time: LunarTime) -> SolarTime:
        """
        Lunar to Solar.
        """
        try:
            from lunar_python import Lunar
            # Use lunar-python for real lunar to solar conversion
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

    def _calculate_fetal_origin(self, eight_char: EightChar) -> str:
        """
        Calculate Fetal Origin.
        """
        from .professional_data import GAN, ZHI

        # Fetal Origin = Month Pillar Heavenly Stem + 1, Month Pillar Earthly Branch + 3
        month_gan = eight_char.month.heaven_stem.name
        month_zhi = eight_char.month.earth_branch.name

        # Heavenly Stem + 1
        gan_idx = GAN.index(month_gan)
        fetal_gan = GAN[(gan_idx + 1) % 10]

        # Earthly Branch + 3
        zhi_idx = ZHI.index(month_zhi)
        fetal_zhi = ZHI[(zhi_idx + 3) % 12]

        return f"{fetal_gan}{fetal_zhi}"

    def _calculate_fetal_breath(self, eight_char: EightChar) -> str:
        """
        Calculate Fetal Breath.
        """
        from .professional_data import GAN, ZHI

        # Fetal Breath = Day Pillar Ganzhi Yin-Yang pair
        day_gan = eight_char.day.heaven_stem.name
        day_zhi = eight_char.day.earth_branch.name

        # Get corresponding Yin-Yang Ganzhi
        gan_idx = GAN.index(day_gan)
        zhi_idx = ZHI.index(day_zhi)

        # Yin-Yang conversion (odd-even switch)
        breath_gan = GAN[(gan_idx + 1) % 10 if gan_idx % 2 == 0 else (gan_idx - 1) % 10]
        breath_zhi = ZHI[(zhi_idx + 6) % 12]  # Opposite Earthly Branch

        return f"{breath_gan}{breath_zhi}"

    def _calculate_own_sign(self, eight_char: EightChar) -> str:
        """
        Calculate Own Sign (Ming Gong).
        """
        from .professional_data import GAN, ZHI

        # Own Sign calculation: Start from Yin palace for the first month, count forward to the birth month, then count backward from Mao hour to the birth hour, the result is the Own Sign.
        month_zhi = eight_char.month.earth_branch.name
        hour_zhi = eight_char.hour.earth_branch.name

        month_idx = ZHI.index(month_zhi)
        hour_idx = ZHI.index(hour_zhi)

        # Start from Yin palace for the first month, count forward to the birth month
        ming_gong_num = (month_idx - 2) % 12  # Yin=0, Mao=1...

        # Count backward from Mao hour to the birth hour
        hour_offset = (hour_idx - 3) % 12  # Mao=0, Chen=1...
        ming_gong_num = (ming_gong_num - hour_offset) % 12

        ming_gong_zhi = ZHI[(ming_gong_num + 2) % 12]  # Convert back to actual Earthly Branch

        # Match with corresponding Heavenly Stem (simplified: take the Heavenly Stem corresponding to Zi year)
        ming_gong_gan = GAN[ming_gong_num % 10]

        return f"{ming_gong_gan}{ming_gong_zhi}"

    def _calculate_body_sign(self, eight_char: EightChar) -> str:
        """
        Calculate Body Sign (Shen Gong).
        """
        from .professional_data import GAN, ZHI

        # Body Sign calculation: Count forward from the month branch to the hour branch
        month_zhi = eight_char.month.earth_branch.name
        hour_zhi = eight_char.hour.earth_branch.name

        month_idx = ZHI.index(month_zhi)
        hour_idx = ZHI.index(hour_zhi)

        # Number of Earthly Branches from month branch to hour branch
        shen_gong_idx = (month_idx + hour_idx) % 12
        shen_gong_zhi = ZHI[shen_gong_idx]

        # Match with corresponding Heavenly Stem
        shen_gong_gan = GAN[shen_gong_idx % 10]

        return f"{shen_gong_gan}{shen_gong_zhi}"

    def _build_relations_object(self, eight_char: EightChar) -> Dict[str, Any]:
        """
        Build clash, harm, combination, and meeting relationships.
        """
        from .professional_data import analyze_zhi_combinations

        # Extract the four pillar Earthly Branches
        zhi_list = [
            eight_char.year.earth_branch.name,
            eight_char.month.earth_branch.name,
            eight_char.day.earth_branch.name,
            eight_char.hour.earth_branch.name,
        ]

        # Use professional function to analyze Earthly Branch relationships
        relations = analyze_zhi_combinations(zhi_list)

        return {
            "Three Combinations": relations.get("sanhe", []),
            "Six Combinations": relations.get("liuhe", []),
            "Three Meetings": relations.get("sanhui", []),
            "Clash": relations.get("chong", []),
            "Harm": relations.get("xing", []),
            "Punishment": relations.get("hai", []),
        }

    def get_solar_times(self, bazi: str) -> List[str]:
        """
        Get possible solar times based on Bazi.
        """
        pillars = bazi.split(" ")
        if len(pillars) != 4:
            raise ValueError("Incorrect Bazi format")

        year_pillar, month_pillar, day_pillar, hour_pillar = pillars

        # Parse Bazi pillars
        if (
            len(year_pillar) != 2
            or len(month_pillar) != 2
            or len(day_pillar) != 2
            or len(hour_pillar) != 2
        ):
            raise ValueError("Incorrect Bazi format, each pillar should have two characters")

        year_gan, year_zhi = year_pillar[0], year_pillar[1]
        month_gan, month_zhi = month_pillar[0], month_pillar[1]
        day_gan, day_zhi = day_pillar[0], day_pillar[1]
        hour_gan, hour_zhi = hour_pillar[0], hour_pillar[1]

        result_times = []

        # Expand search range: 1900-2100, and optimize search strategy
        for year in range(1900, 2100):
            try:
                # Try to match year pillar
                if self._match_year_pillar(year, year_gan, year_zhi):
                    # Iterate through months
                    for month in range(1, 13):
                        if self._match_month_pillar(year, month, month_gan, month_zhi):
                            # Iterate through days, using a more accurate date range
                            import calendar
                            max_day = calendar.monthrange(year, month)[1]
                            
                            for day in range(1, max_day + 1):
                                try:
                                    if self._match_day_pillar(
                                        year, month, day, day_gan, day_zhi
                                    ):
                                        # Iterate through hours, using the center point of each hour
                                        for hour in [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]:  # Center points of the 12 two-hour periods
                                            if self._match_hour_pillar(
                                                hour, hour_gan, hour_zhi, year, month, day
                                            ):
                                                solar_time = f"{year}-{month:02d}-{day:02d} {hour:02d}:00:00"
                                                result_times.append(solar_time)

                                                # Add a reasonable limit to the number of returned results
                                                if len(result_times) >= 20:
                                                    return result_times
                                except ValueError:
                                    continue  # Skip invalid dates
            except Exception:
                continue

        return result_times[:20]  # Return the first 20 matching results

    def _calculate_start_age(
        self, solar_time: SolarTime, eight_char: EightChar, gender: int
    ) -> int:
        """
        Calculate the starting age of fortune.
        """
        from lunar_python import Solar
        from .professional_data import GAN_YINYANG

        # Get the Yin-Yang of the year pillar stem
        year_gan = eight_char.year.heaven_stem.name
        year_gan_yinyang = GAN_YINYANG.get(year_gan, 1)

        try:
            # Create a Solar object for the birth time
            birth_solar = Solar.fromYmdHms(
                solar_time.year,
                solar_time.month,
                solar_time.day,
                solar_time.hour,
                solar_time.minute,
                solar_time.second,
            )

            # Fortune rule: Yang male and Yin female go forward, Yin male and Yang female go backward
            if (gender == 1 and year_gan_yinyang == 1) or (
                gender == 0 and year_gan_yinyang == -1
            ):
                # Forward: calculate the number of days from birth to the next solar term
                lunar = birth_solar.getLunar()
                next_jieqi = lunar.getNextJieQi()

                if next_jieqi:
                    # Get the solar time of the next solar term
                    next_jieqi_solar = next_jieqi.getSolar()

                    # Calculate the day difference
                    days_diff = self._calculate_days_diff(birth_solar, next_jieqi_solar)

                    # Starting age of fortune = day difference / 3 (traditional algorithm)
                    start_age = max(1, days_diff // 3)
                else:
                    start_age = 3  # Default value
            else:
                # Backward: calculate the number of days from the previous solar term to birth
                lunar = birth_solar.getLunar()
                prev_jieqi = lunar.getPrevJieQi()

                if prev_jieqi:
                    # Get the solar time of the previous solar term
                    prev_jieqi_solar = prev_jieqi.getSolar()

                    # Calculate the day difference
                    days_diff = self._calculate_days_diff(prev_jieqi_solar, birth_solar)

                    # Starting age of fortune = day difference / 3 (traditional algorithm)
                    start_age = max(1, days_diff // 3)
                else:
                    start_age = 5  # Default value

            # Limit the starting age of fortune to a reasonable range
            return max(1, min(start_age, 10))

        except Exception:
            # If solar term calculation fails, use a simplified algorithm
            if (gender == 1 and year_gan_yinyang == 1) or (
                gender == 0 and year_gan_yinyang == -1
            ):
                base_age = 3
            else:
                base_age = 5

            # Fine-tune based on the month
            month_adjustment = {
                1: 0,
                2: 1,
                3: 0,
                4: 1,
                5: 0,
                6: 1,
                7: 0,
                8: 1,
                9: 0,
                10: 1,
                11: 0,
                12: 1,
            }

            final_age = base_age + month_adjustment.get(solar_time.month, 0)
            return max(1, min(final_age, 8))

    def _parse_time_part(self, time_str: Optional[str]) -> tuple:
        """Parse the time part, return (hour, minute, second)"""
        if not time_str:
            return (0, 0, 0)
        
        time_str = time_str.strip()
        
        # Support Shichen format: 子时, 丑时, 寅时, etc.
        shichen_map = {
            "子时": 0, "子": 0,
            "丑时": 1, "丑": 1,
            "寅时": 3, "寅": 3,
            "卯时": 5, "卯": 5,
            "辰时": 7, "辰": 7,
            "巳时": 9, "巳": 9,
            "午时": 11, "午": 11,
            "未时": 13, "未": 13,
            "申时": 15, "申": 15,
            "酉时": 17, "酉": 17,
            "戌时": 19, "戌": 19,
            "亥时": 21, "亥": 21,
        }
        
        if time_str in shichen_map:
            return (shichen_map[time_str], 0, 0)
        
        # Support numeric time format: 10时, 10:30, etc.
        import re
        
        # Match "10时30分20秒" format
        chinese_time_match = re.match(r"(\d+)时(?:(\d+)分)?(?:(\d+)秒)?", time_str)
        if chinese_time_match:
            hour = int(chinese_time_match.group(1))
            minute = int(chinese_time_match.group(2) or 0)
            second = int(chinese_time_match.group(3) or 0)
            return (hour, minute, second)
        
        # Match "10:30:20" or "10:30" format
        colon_time_match = re.match(r"(\d+):(\d+)(?::(\d+))?", time_str)
        if colon_time_match:
            hour = int(colon_time_match.group(1))
            minute = int(colon_time_match.group(2))
            second = int(colon_time_match.group(3) or 0)
            return (hour, minute, second)
        
        # Pure numeric time (hour)
        if time_str.isdigit():
            hour = int(time_str)
            return (hour, 0, 0)
        
        # Default to 0 hour
        return (0, 0, 0)

    def _chinese_month_to_number(self, month_str: str) -> int:
        """Convert Chinese month to number"""
        month_map = {
            "正": 1,
            "一": 1,
            "二": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
            "冬": 11,
            "腊": 12,
        }
        return month_map.get(month_str, 1)

    def _chinese_day_to_number(self, day_str: str) -> int:
        """Convert Chinese day to number"""
        # Number mapping table
        chinese_numbers = {
            "一": 1,
            "二": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
            "廿": 20,
            "卅": 30,
        }

        if "初" in day_str:
            day_num = day_str.replace("初", "")
            if day_num in chinese_numbers:
                return chinese_numbers[day_num]
            else:
                return int(day_num) if day_num.isdigit() else 1
        elif "十" in day_str:
            if day_str == "十":
                return 10
            elif day_str.startswith("十"):
                remaining = day_str[1:]
                return 10 + chinese_numbers.get(
                    remaining, int(remaining) if remaining.isdigit() else 0
                )
            elif day_str.endswith("十"):
                prefix = day_str[:-1]
                return (
                    chinese_numbers.get(prefix, int(prefix) if prefix.isdigit() else 1)
                    * 10
                )
        elif "廿" in day_str:
            remaining = day_str.replace("廿", "")
            if remaining in chinese_numbers:
                return 20 + chinese_numbers[remaining]
            else:
                return 20 + (int(remaining) if remaining.isdigit() else 0)
        elif "卅" in day_str:
            return 30
        else:
            # Try to convert number directly
            if day_str in chinese_numbers:
                return chinese_numbers[day_str]
            try:
                return int(day_str)
            except ValueError:
                return 1
        return 1

    def _calculate_days_diff(self, solar1, solar2) -> int:
        """Calculate the day difference between two Solar objects"""
        try:
            from datetime import datetime

            dt1 = datetime(solar1.getYear(), solar1.getMonth(), solar1.getDay())
            dt2 = datetime(solar2.getYear(), solar2.getMonth(), solar2.getDay())

            return abs((dt2 - dt1).days)
        except Exception:
            return 3  # Default value

    def _match_year_pillar(self, year: int, gan: str, zhi: str) -> bool:
        """Match year pillar - fixed version, considering the Start of Spring solar term"""
        try:
            from lunar_python import Solar
            # The year pillar is bounded by the Start of Spring, so we need to check the year pillar before and after the Start of Spring
            # Check the beginning of the year (before the Start of Spring)
            solar_start = Solar.fromYmdHms(year, 1, 1, 0, 0, 0)
            lunar_start = solar_start.getLunar()
            bazi_start = lunar_start.getEightChar()
            
            # Check the middle of the year (after the Start of Spring)
            solar_mid = Solar.fromYmdHms(year, 6, 1, 0, 0, 0)
            lunar_mid = solar_mid.getLunar()
            bazi_mid = lunar_mid.getEightChar()
            
            # Check the end of the year
            solar_end = Solar.fromYmdHms(year, 12, 31, 23, 59, 59)
            lunar_end = solar_end.getLunar()
            bazi_end = lunar_end.getEightChar()

            # If the year pillar at any point in the middle of the year matches, consider it a match
            year_gans = [bazi_start.getYearGan(), bazi_mid.getYearGan(), bazi_end.getYearGan()]
            year_zhis = [bazi_start.getYearZhi(), bazi_mid.getYearZhi(), bazi_end.getYearZhi()]
            
            for i in range(len(year_gans)):
                if year_gans[i] == gan and year_zhis[i] == zhi:
                    return True
                    
            return False
        except Exception:
            return False

    def _match_month_pillar(self, year: int, month: int, gan: str, zhi: str) -> bool:
        """Match month pillar - fixed version, considering solar term boundaries"""
        try:
            from lunar_python import Solar
            # The month pillar is bounded by solar terms, check several points in the month
            # The month pillars at the beginning, middle, and end of the month may be different, so all need to be checked
            test_days = [1, 8, 15, 22, 28]  # Check multiple dates
            
            month_pillars = set()
            for day in test_days:
                try:
                    # Ensure the date is valid
                    import calendar
                    max_day = calendar.monthrange(year, month)[1]
                    if day > max_day:
                        day = max_day
                        
                    solar = Solar.fromYmdHms(year, month, day, 12, 0, 0)
                    lunar = solar.getLunar()
                    bazi = lunar.getEightChar()

                    month_gan = bazi.getMonthGan()
                    month_zhi = bazi.getMonthZhi()
                    month_pillars.add(f"{month_gan}{month_zhi}")
                except:
                    continue
            
            # If the month pillar on any day of the month matches, consider it a match
            target_pillar = f"{gan}{zhi}"
            return target_pillar in month_pillars
            
        except Exception:
            return False

    def _match_day_pillar(
        self, year: int, month: int, day: int, gan: str, zhi: str
    ) -> bool:
        """Match day pillar"""
        try:
            from lunar_python import Solar
            solar = Solar.fromYmdHms(year, month, day, 0, 0, 0)
            lunar = solar.getLunar()
            bazi = lunar.getEightChar()

            day_gan = bazi.getDayGan()
            day_zhi = bazi.getDayZhi()

            return day_gan == gan and day_zhi == zhi
        except Exception:
            return False

    def _match_hour_pillar(self, hour: int, gan: str, zhi: str, year: Optional[int] = None, month: Optional[int] = None, day: Optional[int] = None) -> bool:
        """Match hour pillar - fixed version, using actual date"""
        try:
            from lunar_python import Solar
            # Use actual date or default date with the hour
            use_year = year if year else 2024
            use_month = month if month else 1
            use_day = day if day else 1
            
            solar = Solar.fromYmdHms(use_year, use_month, use_day, hour, 0, 0)
            lunar = solar.getLunar()
            bazi = lunar.getEightChar()

            hour_gan = bazi.getTimeGan()
            hour_zhi = bazi.getTimeZhi()

            return hour_gan == gan and hour_zhi == zhi
        except Exception:
            return False

    def _get_zodiac_by_lunar_year(self, solar_time: SolarTime) -> str:
        """
        Get zodiac based on lunar year (bounded by Spring Festival, not Start of Spring)
        """
        try:
            from lunar_python import Solar
            solar = Solar.fromYmdHms(
                solar_time.year,
                solar_time.month,
                solar_time.day,
                solar_time.hour,
                solar_time.minute,
                solar_time.second,
            )
            lunar = solar.getLunar()
            
            # Use lunar-python to directly get the lunar zodiac (bounded by Spring Festival)
            return lunar.getYearShengXiao()
        except Exception as e:
            # If it fails, use the zodiac of the Bazi year pillar as a fallback
            print(f"Failed to get lunar zodiac, using Bazi year pillar zodiac: {e}")
            eight_char = self.engine.build_eight_char(solar_time)
            return eight_char.year.earth_branch.zodiac


# Global calculator instance
_bazi_calculator = None


def get_bazi_calculator() -> BaziCalculator:
    """
    Get the Bazi calculator singleton.
    """
    global _bazi_calculator
    if _bazi_calculator is None:
        _bazi_calculator = BaziCalculator()
    return _bazi_calculator
