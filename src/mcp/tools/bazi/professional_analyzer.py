"""
BaZi professional analyzer. Uses built-in professional data for accurate traditional fortune analysis.
"""

from typing import Any, Dict, List

from .professional_data import (
    GAN_WUXING,
    WUXING_RELATIONS,
    ZHI_CANG_GAN,
    ZHI_WUXING,
    WUXING,
    analyze_zhi_combinations,
    get_changsheng_state,
    get_nayin,
    get_shensha,
    get_ten_gods_relation,
)


class ProfessionalAnalyzer:
    """Professional BaZi Analyzer - Uses complete traditional fortune data"""

    def __init__(self):
        """
        Initialize the analyzer.
        """

    def get_ten_gods_analysis(self, day_master: str, other_stem: str) -> str:
        """
        Get Ten Gods analysis.
        """
        return get_ten_gods_relation(day_master, other_stem)

    def analyze_eight_char_structure(
        self, eight_char_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Comprehensive analysis of the BaZi structure.
        """
        year_gan = (
            eight_char_data.get("year", {}).get("heaven_stem", {}).get("name", "")
        )
        year_zhi = (
            eight_char_data.get("year", {}).get("earth_branch", {}).get("name", "")
        )
        month_gan = (
            eight_char_data.get("month", {}).get("heaven_stem", {}).get("name", "")
        )
        month_zhi = (
            eight_char_data.get("month", {}).get("earth_branch", {}).get("name", "")
        )
        day_gan = eight_char_data.get("day", {}).get("heaven_stem", {}).get("name", "")
        day_zhi = eight_char_data.get("day", {}).get("earth_branch", {}).get("name", "")
        hour_gan = (
            eight_char_data.get("hour", {}).get("heaven_stem", {}).get("name", "")
        )
        hour_zhi = (
            eight_char_data.get("hour", {}).get("earth_branch", {}).get("name", "")
        )

        # Basic information
        gan_list = [year_gan, month_gan, day_gan, hour_gan]
        zhi_list = [year_zhi, month_zhi, day_zhi, hour_zhi]

        analysis = {
            "day_master": day_gan,
            "ten_gods": self._analyze_ten_gods(day_gan, gan_list, zhi_list),
            "nayin": self._analyze_nayin(gan_list, zhi_list),
            "changsheng": self._analyze_changsheng(day_gan, zhi_list),
            "zhi_relations": analyze_zhi_combinations(zhi_list),
            "wuxing_balance": self._analyze_wuxing_balance(gan_list, zhi_list),
            "shensha": self._analyze_shensha(gan_list, zhi_list),
            "strength": self._analyze_day_master_strength(day_gan, month_zhi, zhi_list),
            "useful_god": self._determine_useful_god(
                day_gan, month_zhi, gan_list, zhi_list
            ),
        }

        return analysis

    def _analyze_ten_gods(
        self, day_master: str, gan_list: List[str], zhi_list: List[str]
    ) -> Dict[str, List[str]]:
        """
        Analyze Ten Gods distribution.
        """
        ten_gods = {
            "Bi Jian (Companion)": [],
            "Jie Cai (Rob Wealth)": [],
            "Shi Shen (Eating God)": [],
            "Shang Guan (Hurting Officer)": [],
            "Pian Cai (Indirect Wealth)": [],
            "Zheng Cai (Direct Wealth)": [],
            "Qi Sha (Seven Killings)": [],
            "Zheng Guan (Direct Officer)": [],
            "Pian Yin (Indirect Seal)": [],
            "Zheng Yin (Direct Seal)": [],
        }

        # Heavenly Stem Ten Gods
        for i, gan in enumerate(gan_list):
            if gan == day_master:
                continue

            ten_god = get_ten_gods_relation(day_master, gan)
            pillar_names = ["Year Stem", "Month Stem", "Day Stem", "Hour Stem"]
            if ten_god in ten_gods:
                ten_gods[ten_god].append(f"{pillar_names[i]}{gan}")

        # Earthly Branch Hidden Stem Ten Gods
        pillar_names = ["Year Branch", "Month Branch", "Day Branch", "Hour Branch"]
        for i, zhi in enumerate(zhi_list):
            cang_gan = ZHI_CANG_GAN.get(zhi, {})
            for gan, strength in cang_gan.items():
                if gan == day_master:
                    continue

                ten_god = get_ten_gods_relation(day_master, gan)
                if ten_god in ten_gods:
                    ten_gods[ten_god].append(
                        f"{pillar_names[i]}{zhi} hidden {gan}({strength})"
                    )

        return ten_gods

    def _analyze_nayin(self, gan_list: List[str], zhi_list: List[str]) -> List[str]:
        """
        Analyze NaYin (Sound of Five Elements).
        """
        nayin_list = []
        pillar_names = ["Year Pillar", "Month Pillar", "Day Pillar", "Hour Pillar"]

        for i, (gan, zhi) in enumerate(zip(gan_list, zhi_list)):
            nayin = get_nayin(gan, zhi)
            nayin_list.append(f"{pillar_names[i]}{gan}{zhi}: {nayin}")

        return nayin_list

    def _analyze_changsheng(self, day_master: str, zhi_list: List[str]) -> List[str]:
        """
        Analyze the Twelve Stages of Life Cycle.
        """
        changsheng_list = []
        pillar_names = ["Year Branch", "Month Branch", "Day Branch", "Hour Branch"]

        for i, zhi in enumerate(zhi_list):
            state = get_changsheng_state(day_master, zhi)
            changsheng_list.append(f"{pillar_names[i]}{zhi}: {state}")

        return changsheng_list

    def _analyze_wuxing_balance(
        self, gan_list: List[str], zhi_list: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze Five Elements balance.
        """
        wuxing_count = {element: 0 for element in WUXING}

        # Heavenly Stem Five Elements
        for gan in gan_list:
            wuxing = GAN_WUXING.get(gan, "")
            if wuxing in wuxing_count:
                wuxing_count[wuxing] += 2  # Heavenly Stems have stronger influence

        # Earthly Branch Five Elements
        for zhi in zhi_list:
            wuxing = ZHI_WUXING.get(zhi, "")
            if wuxing in wuxing_count:
                wuxing_count[wuxing] += 1

            # Hidden Stems in Earthly Branches
            cang_gan = ZHI_CANG_GAN.get(zhi, {})
            for gan, strength in cang_gan.items():
                wuxing = GAN_WUXING.get(gan, "")
                if wuxing in wuxing_count:
                    wuxing_count[wuxing] += strength / 10  # Hidden stems have weaker influence

        # Find the strongest and weakest elements
        max_wuxing = max(wuxing_count, key=wuxing_count.get)
        min_wuxing = min(wuxing_count, key=wuxing_count.get)

        return {
            "distribution": wuxing_count,
            "strongest": max_wuxing,
            "weakest": min_wuxing,
            "balance_score": self._calculate_balance_score(wuxing_count),
        }

    def _calculate_balance_score(self, wuxing_count: Dict[str, float]) -> float:
        """
        Calculate Five Elements balance score (0-100, 100 = perfectly balanced)
        """
        values = list(wuxing_count.values())
        if not values:
            return 0

        average = sum(values) / len(values)
        variance = sum((v - average) ** 2 for v in values) / len(values)
        # Convert to 0-100 score; lower variance means higher score
        balance_score = max(0, 100 - variance * 10)
        return round(balance_score, 2)

    def _analyze_shensha(
        self, gan_list: List[str], zhi_list: List[str]
    ) -> Dict[str, List[str]]:
        """
        Analyze Shen Sha (Spirit Stars) - Fixed version, correctly distinguishes between those looked up by Day Stem and Day Branch.
        """
        shensha = {
            "Tianyi Noble": [],
            "Wenchang Noble": [],
            "Yima Star": [],
            "Peach Blossom Star": [],
            "Huagai Star": [],
        }

        day_gan = gan_list[2] if len(gan_list) > 2 else ""
        day_zhi = zhi_list[2] if len(zhi_list) > 2 else ""
        pillar_names = ["Year Branch", "Month Branch", "Day Branch", "Hour Branch"]

        # Shen Sha looked up by Day Stem
        day_gan_shensha = [
            ("tianyi", "Tianyi Noble"),
            ("wenchang", "Wenchang Noble"),
        ]

        for shensha_type, shensha_name in day_gan_shensha:
            shensha_zhi = get_shensha(day_gan, shensha_type)
            if shensha_zhi:
                for i, zhi in enumerate(zhi_list):
                    if zhi in shensha_zhi:
                        shensha[shensha_name].append(f"{pillar_names[i]}{zhi}")

        # Shen Sha looked up by Day Branch
        day_zhi_shensha = [
            ("yima", "Yima Star"),
            ("taohua", "Peach Blossom Star"),
            ("huagai", "Huagai Star"),
        ]

        for shensha_type, shensha_name in day_zhi_shensha:
            shensha_zhi = get_shensha(day_zhi, shensha_type)
            if shensha_zhi:
                for i, zhi in enumerate(zhi_list):
                    if zhi == shensha_zhi:  # These Shen Sha return a single Earthly Branch
                        shensha[shensha_name].append(f"{pillar_names[i]}{zhi}")

        return shensha

    def _analyze_day_master_strength(
        self, day_master: str, month_zhi: str, zhi_list: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze Day Master strength.
        """
        # Base monthly command strength
        month_element = ZHI_WUXING.get(month_zhi, "")
        day_element = GAN_WUXING.get(day_master, "")

        # Monthly command generating/overcoming relationship
        month_relation = WUXING_RELATIONS.get((day_element, month_element), "")

        # Calculate support and assistance
        same_element_count = 0
        help_element_count = 0

        for zhi in zhi_list:
            zhi_element = ZHI_WUXING.get(zhi, "")
            if zhi_element == day_element:
                same_element_count += 1
            elif WUXING_RELATIONS.get((zhi_element, day_element)) == "↓":  # Generates me
                help_element_count += 1

        # Simple strength assessment
        strength_score = 0
        if month_relation == "↑":  # I generate the month
            strength_score -= 30
        elif month_relation == "↓":  # Month generates me
            strength_score += 30
        elif month_relation == "=":  # Same element
            strength_score += 20
        elif month_relation == "←":  # Month overcomes me
            strength_score -= 20
        elif month_relation == "→":  # I overcome the month
            strength_score -= 10

        strength_score += same_element_count * 15
        strength_score += help_element_count * 10

        if strength_score >= 30:
            strength_level = "Somewhat Strong"
        elif strength_score >= 10:
            strength_level = "Balanced"
        elif strength_score >= -10:
            strength_level = "Somewhat Weak"
        else:
            strength_level = "Very Weak"

        return {
            "level": strength_level,
            "score": strength_score,
            "month_relation": month_relation,
            "same_element_count": same_element_count,
            "help_element_count": help_element_count,
        }

    def _determine_useful_god(
        self, day_master: str, month_zhi: str, gan_list: List[str], zhi_list: List[str]
    ) -> Dict[str, Any]:
        """
        Determine the Useful God (Yong Shen).
        """
        day_element = GAN_WUXING.get(day_master, "")
        strength_analysis = self._analyze_day_master_strength(
            day_master, month_zhi, zhi_list
        )

        useful_gods = []
        avoid_gods = []

        if strength_analysis["level"] in ["Somewhat Strong", "Very Strong"]:
            # Strong Day Master uses overcoming, draining, and exhausting
            for element in WUXING:
                relation = WUXING_RELATIONS.get((day_element, element), "")
                if relation == "→":  # What I overcome is Wealth
                    useful_gods.append(f"{element} (Wealth Star)")
                elif relation == "↓":  # What I generate is Food/Injury
                    useful_gods.append(f"{element} (Food/Injury)")
                elif relation == "←":  # What overcomes me is Officer/Killing
                    useful_gods.append(f"{element} (Officer/Killing)")
        else:
            # Weak Day Master uses generating and supporting
            for element in WUXING:
                relation = WUXING_RELATIONS.get((element, day_element), "")
                if relation == "↓":  # What generates me is Seal
                    useful_gods.append(f"{element} (Seal Star)")
                elif relation == "=":  # Same as me is Companion/Rob
                    useful_gods.append(f"{element} (Companion/Rob)")

        return {
            "useful_gods": useful_gods[:3],  # Take top 3
            "avoid_gods": avoid_gods[:3],  # Take top 3
            "strategy": (
                "Support" if strength_analysis["level"] in ["Somewhat Weak", "Very Weak"] else "Restrain"
            ),
        }

    def get_detailed_fortune_analysis(self, eight_char_data: Dict[str, Any]) -> str:
        """
        Get detailed fortune analysis text.
        """
        analysis = self.analyze_eight_char_structure(eight_char_data)

        result_lines = []
        result_lines.append("=== Detailed BaZi Fortune Analysis ===\n")

        # Day Master analysis
        result_lines.append(
            f"[Day Master] {analysis['day_master']} ({GAN_WUXING.get(analysis['day_master'], '')})"
        )
        result_lines.append(
            f"[Strength] {analysis['strength']['level']} (Score: {analysis['strength']['score']})"
        )
        result_lines.append("")

        # Ten Gods analysis
        result_lines.append("[Ten Gods Distribution]")
        for god_name, positions in analysis["ten_gods"].items():
            if positions:
                result_lines.append(f"  {god_name}: {', '.join(positions)}")
        result_lines.append("")

        # Useful God analysis
        result_lines.append("[Useful God Analysis]")
        result_lines.append(f"  Strategy: {analysis['useful_god']['strategy']}")
        if analysis["useful_god"]["useful_gods"]:
            result_lines.append(
                f"  Useful Gods: {', '.join(analysis['useful_god']['useful_gods'])}"
            )
        result_lines.append("")

        # Five Elements balance
        result_lines.append("[Five Elements Distribution]")
        for element, count in analysis["wuxing_balance"]["distribution"].items():
            result_lines.append(f"  {element}: {count:.1f}")
        result_lines.append(f"  Balance Score: {analysis['wuxing_balance']['balance_score']}")
        result_lines.append("")

        # Earthly Branch relationships
        result_lines.append("[Earthly Branch Relationships]")
        for relation_type, relations in analysis["zhi_relations"].items():
            if relations:
                result_lines.append(f"  {relation_type}: {', '.join(relations)}")
        result_lines.append("")

        # Shen Sha
        result_lines.append("[Shen Sha Analysis]")
        for shensha_name, positions in analysis["shensha"].items():
            if positions:
                result_lines.append(f"  {shensha_name}: {', '.join(positions)}")
        result_lines.append("")

        # NaYin
        result_lines.append("[NaYin Five Elements]")
        for nayin in analysis["nayin"]:
            result_lines.append(f"  {nayin}")

        return "\n".join(result_lines)


# Global analyzer instance
_professional_analyzer = None


def get_professional_analyzer() -> ProfessionalAnalyzer:
    """
    Get the professional analyzer singleton.
    """
    global _professional_analyzer
    if _professional_analyzer is None:
        _professional_analyzer = ProfessionalAnalyzer()
    return _professional_analyzer
