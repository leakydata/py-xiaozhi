"""
Data models for Bazi numerology.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HeavenStem:
    """Heavenly Stem"""

    name: str
    element: str  # Five Elements
    yin_yang: int  # Yin/Yang, 1=Yang, -1=Yin

    def __str__(self):
        return self.name

    def get_element(self):
        return self.element

    def get_yin_yang(self):
        return self.yin_yang

    def get_ten_star(self, other_stem: "HeavenStem") -> str:
        """
        Get Ten Gods relationship.
        """
        # Implement Ten Gods logic
        return self._calculate_ten_star(other_stem)

    def _calculate_ten_star(self, other: "HeavenStem") -> str:
        """Calculate Ten Gods relationship - using professional data"""
        from .professional_data import get_ten_gods_relation

        return get_ten_gods_relation(self.name, other.name)


@dataclass
class EarthBranch:
    """Earthly Branch"""

    name: str
    element: str  # Five Elements
    yin_yang: int  # Yin/Yang
    zodiac: str  # Zodiac sign
    hide_heaven_main: Optional[str] = None  # Main hidden heavenly stem
    hide_heaven_middle: Optional[str] = None  # Middle hidden heavenly stem
    hide_heaven_residual: Optional[str] = None  # Residual hidden heavenly stem

    def __str__(self):
        return self.name

    def get_element(self):
        return self.element

    def get_yin_yang(self):
        return self.yin_yang

    def get_zodiac(self):
        return self.zodiac

    def get_hide_heaven_stem_main(self):
        return self.hide_heaven_main

    def get_hide_heaven_stem_middle(self):
        return self.hide_heaven_middle

    def get_hide_heaven_stem_residual(self):
        return self.hide_heaven_residual


@dataclass
class SixtyCycle:
    """
    Sixty Jiazi Cycle.
    """

    heaven_stem: HeavenStem
    earth_branch: EarthBranch
    sound: str  # Sound element
    ten: str  # Decade
    extra_earth_branches: List[str]  # Void branches

    def __str__(self):
        return f"{self.heaven_stem.name}{self.earth_branch.name}"

    def get_heaven_stem(self):
        return self.heaven_stem

    def get_earth_branch(self):
        return self.earth_branch

    def get_sound(self):
        return self.sound

    def get_ten(self):
        return self.ten

    def get_extra_earth_branches(self):
        return self.extra_earth_branches


@dataclass
class EightChar:
    """Eight Characters (Bazi)"""

    year: SixtyCycle
    month: SixtyCycle
    day: SixtyCycle
    hour: SixtyCycle

    def __str__(self):
        return f"{self.year} {self.month} {self.day} {self.hour}"

    def get_year(self):
        return self.year

    def get_month(self):
        return self.month

    def get_day(self):
        return self.day

    def get_hour(self):
        return self.hour

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format for professional analysis.
        """
        return {
            "year": {
                "heaven_stem": {"name": self.year.heaven_stem.name},
                "earth_branch": {"name": self.year.earth_branch.name},
            },
            "month": {
                "heaven_stem": {"name": self.month.heaven_stem.name},
                "earth_branch": {"name": self.month.earth_branch.name},
            },
            "day": {
                "heaven_stem": {"name": self.day.heaven_stem.name},
                "earth_branch": {"name": self.day.earth_branch.name},
            },
            "hour": {
                "heaven_stem": {"name": self.hour.heaven_stem.name},
                "earth_branch": {"name": self.hour.earth_branch.name},
            },
        }


@dataclass
class LunarTime:
    """
    Lunar time.
    """

    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    is_leap: bool = False  # Is it a leap month

    def __str__(self):
        leap_text = "Leap " if self.is_leap else ""
        return f"Lunar {self.year}-{leap_text}{self.month}-{self.day} {self.hour}:{self.minute}:{self.second}"


@dataclass
class SolarTime:
    """
    Solar time.
    """

    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int

    def __str__(self):
        return f"{self.year}-{self.month}-{self.day} {self.hour}:{self.minute}:{self.second}"

    def get_year(self):
        return self.year

    def get_month(self):
        return self.month

    def get_day(self):
        return self.day

    def get_hour(self):
        return self.hour

    def get_minute(self):
        return self.minute

    def get_second(self):
        return self.second


@dataclass
class BaziAnalysis:
    """
    Bazi analysis result.
    """

    gender: str  # Gender
    solar_time: str  # Solar time
    lunar_time: str  # Lunar time
    bazi: str  # Eight Characters
    zodiac: str  # Zodiac sign
    day_master: str  # Day Master
    year_pillar: Dict[str, Any]  # Year Pillar
    month_pillar: Dict[str, Any]  # Month Pillar
    day_pillar: Dict[str, Any]  # Day Pillar
    hour_pillar: Dict[str, Any]  # Hour Pillar
    fetal_origin: str  # Fetal Origin
    fetal_breath: str  # Fetal Breath
    own_sign: str  # Own Sign (Ming Gong)
    body_sign: str  # Body Sign (Shen Gong)
    gods: Dict[str, List[str]]  # Gods (Shen Sha)
    fortune: Dict[str, Any]  # Decade Fortune
    relations: Dict[str, Any]  # Clash, Harm, Combination, Meeting relationships
    professional_analysis: Optional[Dict[str, Any]] = field(default=None, repr=False)
    detailed_fortune_text: Optional[str] = field(default=None, repr=False)


    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        """
        result = {
            "Gender": self.gender,
            "Solar Time": self.solar_time,
            "Lunar Time": self.lunar_time,
            "Bazi": self.bazi,
            "Zodiac": self.zodiac,
            "Day Master": self.day_master,
            "Year Pillar": self.year_pillar,
            "Month Pillar": self.month_pillar,
            "Day Pillar": self.day_pillar,
            "Hour Pillar": self.hour_pillar,
            "Fetal Origin": self.fetal_origin,
            "Fetal Breath": self.fetal_breath,
            "Own Sign": self.own_sign,
            "Body Sign": self.body_sign,
            "Gods": self.gods,
            "Decade Fortune": self.fortune,
            "Relationships": self.relations,
        }

        # Add professional analysis result (if it exists)
        if self.professional_analysis:
            result["Professional Analysis"] = self.professional_analysis
        if self.detailed_fortune_text:
            result["Detailed Fortune Analysis"] = self.detailed_fortune_text

        return result


@dataclass
class ChineseCalendar:
    """
    Chinese Almanac information.
    """

    solar_date: str  # Solar date
    lunar_date: str  # Lunar date
    gan_zhi: str  # Ganzhi
    zodiac: str  # Zodiac sign
    na_yin: str  # Na Yin
    lunar_festival: Optional[str]  # Lunar festival
    solar_festival: Optional[str]  # Solar festival
    solar_term: str  # Solar term
    twenty_eight_star: str  # 28 Mansions
    pengzu_taboo: str  # Pengzu's Taboos
    joy_direction: str  # Direction of Joy God
    yang_direction: str  # Direction of Yang Nobleman
    yin_direction: str  # Direction of Yin Nobleman
    mascot_direction: str  # Direction of Blessing God
    wealth_direction: str  # Direction of Wealth God
    clash: str  # Clash
    suitable: str  # Suitable activities
    avoid: str  # Unsuitable activities

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "Solar Date": self.solar_date,
            "Lunar Date": self.lunar_date,
            "Ganzhi": self.gan_zhi,
            "Zodiac": self.zodiac,
            "Na Yin": self.na_yin,
            "Lunar Festival": self.lunar_festival,
            "Solar Festival": self.solar_festival,
            "Solar Term": self.solar_term,
            "28 Mansions": self.twenty_eight_star,
            "Pengzu's Taboos": self.pengzu_taboo,
            "Joy God Direction": self.joy_direction,
            "Yang Nobleman Direction": self.yang_direction,
            "Yin Nobleman Direction": self.yin_direction,
            "Blessing God Direction": self.mascot_direction,
            "Wealth God Direction": self.wealth_direction,
            "Clash": self.clash,
            "Suitable": self.suitable,
            "Avoid": self.avoid,
        }
