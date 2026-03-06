"""
Marriage analysis tool functions.
"""

import json
from typing import Any, Dict, List

from src.utils.logging_config import get_logger

from .bazi_calculator import get_bazi_calculator
from .marriage_analyzer import get_marriage_analyzer

logger = get_logger(__name__)


async def analyze_marriage_timing(args: Dict[str, Any]) -> str:
    """
    Analyze marriage timing and spouse information.
    """
    try:
        solar_datetime = args.get("solar_datetime")
        lunar_datetime = args.get("lunar_datetime")
        gender = args.get("gender", 1)
        eight_char_provider_sect = args.get("eight_char_provider_sect", 2)

        if not solar_datetime and not lunar_datetime:
            return json.dumps(
                {
                    "success": False,
                    "message": "Either solar_datetime or lunar_datetime must be provided, but not both",
                },
                ensure_ascii=False,
            )

        # First get basic BaZi information
        calculator = get_bazi_calculator()
        bazi_result = calculator.build_bazi(
            solar_datetime=solar_datetime,
            lunar_datetime=lunar_datetime,
            gender=gender,
            eight_char_provider_sect=eight_char_provider_sect,
        )

        # Perform marriage-specific analysis
        marriage_analyzer = get_marriage_analyzer()

        # Build BaZi data format suitable for marriage analysis
        eight_char_dict = {
            "year": bazi_result.year_pillar,
            "month": bazi_result.month_pillar,
            "day": bazi_result.day_pillar,
            "hour": bazi_result.hour_pillar,
        }

        marriage_analysis = marriage_analyzer.analyze_marriage_timing(
            eight_char_dict, gender
        )

        # Merge results
        result = {
            "basic_info": {
                "bazi": bazi_result.bazi,
                "gender": "Male" if gender == 1 else "Female",
                "day_master": bazi_result.day_master,
                "zodiac": bazi_result.zodiac,
            },
            "marriage_analysis": marriage_analysis,
        }

        return json.dumps(
            {"success": True, "data": result}, ensure_ascii=False, indent=2
        )

    except Exception as e:
        logger.error(f"Marriage analysis failed: {e}")
        return json.dumps(
            {"success": False, "message": f"Marriage analysis failed: {str(e)}"},
            ensure_ascii=False,
        )


async def analyze_marriage_compatibility(args: Dict[str, Any]) -> str:
    """
    Analyze marriage compatibility between two people's BaZi.
    """
    try:
        # Male information
        male_solar = args.get("male_solar_datetime")
        male_lunar = args.get("male_lunar_datetime")

        # Female information
        female_solar = args.get("female_solar_datetime")
        female_lunar = args.get("female_lunar_datetime")

        if not (male_solar or male_lunar) or not (female_solar or female_lunar):
            return json.dumps(
                {
                    "success": False,
                    "message": "Time information for both male and female must be provided",
                },
                ensure_ascii=False,
            )

        calculator = get_bazi_calculator()

        # Get male BaZi
        male_bazi = calculator.build_bazi(
            solar_datetime=male_solar, lunar_datetime=male_lunar, gender=1
        )

        # Get female BaZi
        female_bazi = calculator.build_bazi(
            solar_datetime=female_solar, lunar_datetime=female_lunar, gender=0
        )

        # Perform compatibility analysis
        compatibility_result = _analyze_compatibility(male_bazi, female_bazi)

        result = {
            "male_info": {
                "bazi": male_bazi.bazi,
                "day_master": male_bazi.day_master,
                "zodiac": male_bazi.zodiac,
            },
            "female_info": {
                "bazi": female_bazi.bazi,
                "day_master": female_bazi.day_master,
                "zodiac": female_bazi.zodiac,
            },
            "compatibility": compatibility_result,
        }

        return json.dumps(
            {"success": True, "data": result}, ensure_ascii=False, indent=2
        )

    except Exception as e:
        logger.error(f"Compatibility analysis failed: {e}")
        return json.dumps(
            {"success": False, "message": f"Compatibility analysis failed: {str(e)}"},
            ensure_ascii=False,
        )


def _analyze_compatibility(male_bazi, female_bazi) -> Dict[str, Any]:
    """Analyze marriage compatibility between two BaZi - using professional algorithm"""
    # Get both parties' day pillars
    male_day_gan = male_bazi.day_master
    female_day_gan = female_bazi.day_pillar["天干"]["天干"]

    male_day_zhi = male_bazi.day_pillar["地支"]["地支"]
    female_day_zhi = female_bazi.day_pillar["地支"]["地支"]

    # Professional Five Elements analysis
    element_analysis = _analyze_element_compatibility(male_day_gan, female_day_gan)

    # Zodiac compatibility analysis
    zodiac_analysis = _analyze_zodiac_compatibility(
        male_bazi.zodiac, female_bazi.zodiac
    )

    # Day Pillar compatibility analysis
    pillar_analysis = _analyze_pillar_compatibility(
        male_day_gan + male_day_zhi, female_day_gan + female_day_zhi
    )

    # Earthly Branch relationship analysis
    branch_analysis = _analyze_branch_relationships(male_bazi, female_bazi)

    # BaZi complementarity analysis
    complement_analysis = _analyze_complement(male_bazi, female_bazi)

    # Overall score
    total_score = (
        element_analysis["score"] * 0.3
        + zodiac_analysis["score"] * 0.2
        + pillar_analysis["score"] * 0.2
        + branch_analysis["score"] * 0.15
        + complement_analysis["score"] * 0.15
    )

    return {
        "overall_score": round(total_score, 1),
        "overall_level": _get_compatibility_level(total_score),
        "element_analysis": element_analysis,
        "zodiac_analysis": zodiac_analysis,
        "pillar_analysis": pillar_analysis,
        "branch_analysis": branch_analysis,
        "complement_analysis": complement_analysis,
        "suggestions": _get_professional_suggestions(
            total_score, element_analysis, zodiac_analysis
        ),
    }


def _analyze_element_compatibility(male_gan: str, female_gan: str) -> Dict[str, Any]:
    """
    Professional Five Elements compatibility analysis.
    """
    from .professional_data import GAN_WUXING, WUXING_RELATIONS

    male_element = GAN_WUXING.get(male_gan, "")
    female_element = GAN_WUXING.get(female_gan, "")

    element_relation = WUXING_RELATIONS.get((male_element, female_element), "")

    # Five Elements analysis
    score_map = {
        "↓": 90,  # Male generates Female, loving couple
        "=": 80,  # Same element, like-minded
        "←": 50,  # Female overcomes Male, strong wife weak husband
        "→": 55,  # Male overcomes Female, strong husband weak wife
        "↑": 85,  # Female generates Male, virtuous wife noble husband
    }

    desc_map = {
        "↓": "Male generates Female, loving couple, harmonious family",
        "=": "Same element, like-minded, easy to understand each other",
        "←": "Female overcomes Male, strong wife weak husband, needs balance",
        "→": "Male overcomes Female, strong husband weak wife, needs tolerance",
        "↑": "Female generates Male, virtuous wife noble husband, mutual achievement",
    }

    return {
        "male_element": male_element,
        "female_element": female_element,
        "relation": element_relation,
        "score": score_map.get(element_relation, 70),
        "description": desc_map.get(element_relation, "Harmonious relationship"),
    }


def _analyze_zodiac_compatibility(
    male_zodiac: str, female_zodiac: str
) -> Dict[str, Any]:
    """
    Professional zodiac compatibility analysis.
    """
    from .professional_data import ZHI_CHONG, ZHI_HAI, ZHI_LIUHE, ZHI_SANHE, ZHI_XING

    # Zodiac to Earthly Branch mapping
    zodiac_to_zhi = {
        "鼠": "子",
        "牛": "丑",
        "虎": "寅",
        "兔": "卯",
        "龙": "辰",
        "蛇": "巳",
        "马": "午",
        "羊": "未",
        "猴": "申",
        "鸡": "酉",
        "狗": "戌",
        "猪": "亥",
    }

    male_zhi = zodiac_to_zhi.get(male_zodiac, "")
    female_zhi = zodiac_to_zhi.get(female_zodiac, "")

    # Check relationships
    if (male_zhi, female_zhi) in ZHI_LIUHE or (female_zhi, male_zhi) in ZHI_LIUHE:
        return {
            "score": 90,
            "level": "Perfect Match",
            "description": "Six Combination zodiac, deep affection",
            "relation": "Six Combination",
        }

    # Check Three Combinations
    for sanhe_group in ZHI_SANHE:
        if male_zhi in sanhe_group and female_zhi in sanhe_group:
            return {
                "score": 85,
                "level": "Perfect Match",
                "description": "Three Combination zodiac, harmonious relationship",
                "relation": "Three Combination",
            }

    # Check Clashes
    if (male_zhi, female_zhi) in ZHI_CHONG or (female_zhi, male_zhi) in ZHI_CHONG:
        return {
            "score": 30,
            "level": "Clash Incompatible",
            "description": "Zodiac clash, many conflicts",
            "relation": "Clash",
        }

    # Check Punishments
    for xing_group in ZHI_XING:
        if male_zhi in xing_group and female_zhi in xing_group:
            return {
                "score": 40,
                "level": "Punishment Incompatible",
                "description": "Zodiac punishment, needs resolution",
                "relation": "Punishment",
            }

    # Check Harm
    if (male_zhi, female_zhi) in ZHI_HAI or (female_zhi, male_zhi) in ZHI_HAI:
        return {
            "score": 45,
            "level": "Harm Incompatible",
            "description": "Zodiac harm, minor incompatibility",
            "relation": "Harm",
        }

    # Normal relationship
    return {
        "score": 70,
        "level": "Average",
        "description": "Zodiac neutral, no particular conflicts",
        "relation": "Neutral",
    }


def _analyze_pillar_compatibility(
    male_pillar: str, female_pillar: str
) -> Dict[str, Any]:
    """
    Professional Day Pillar compatibility analysis.
    """
    if male_pillar == female_pillar:
        return {"score": 55, "description": "Same Day Pillar, many commonalities but needs differentiation"}

    # Analyze stem-branch combination
    male_gan, male_zhi = male_pillar[0], male_pillar[1]
    female_gan, female_zhi = female_pillar[0], female_pillar[1]

    score = 70  # Base score

    # Heavenly Stem relationship
    from .professional_data import get_ten_gods_relation

    gan_relation = get_ten_gods_relation(male_gan, female_gan)
    if gan_relation in ["正财", "偏财", "正官", "七杀"]:
        score += 10

    # Earthly Branch relationship
    from .professional_data import ZHI_CHONG, ZHI_LIUHE

    if (male_zhi, female_zhi) in ZHI_LIUHE or (female_zhi, male_zhi) in ZHI_LIUHE:
        score += 15
    elif (male_zhi, female_zhi) in ZHI_CHONG or (female_zhi, male_zhi) in ZHI_CHONG:
        score -= 20

    return {
        "score": min(95, max(30, score)),
        "description": f"Day Pillar combination analysis: {gan_relation} relationship",
    }


def _analyze_branch_relationships(male_bazi, female_bazi) -> Dict[str, Any]:
    """
    Analyze Earthly Branch relationships.
    """
    # Get both parties' four pillar Earthly Branches
    male_branches = [
        male_bazi.year_pillar["地支"]["地支"],
        male_bazi.month_pillar["地支"]["地支"],
        male_bazi.day_pillar["地支"]["地支"],
        male_bazi.hour_pillar["地支"]["地支"],
    ]

    female_branches = [
        female_bazi.year_pillar["地支"]["地支"],
        female_bazi.month_pillar["地支"]["地支"],
        female_bazi.day_pillar["地支"]["地支"],
        female_bazi.hour_pillar["地支"]["地支"],
    ]

    # Analyze Earthly Branch relationships
    from .professional_data import analyze_zhi_combinations

    combined_branches = male_branches + female_branches
    relationships = analyze_zhi_combinations(combined_branches)

    score = 70
    if relationships.get("liuhe", []):
        score += 10
    if relationships.get("sanhe", []):
        score += 8
    if relationships.get("chong", []):
        score -= 15
    if relationships.get("xing", []):
        score -= 10

    return {
        "score": min(95, max(30, score)),
        "relationships": relationships,
        "description": f"Earthly Branch analysis: {len(relationships.get('liuhe', []))} Six Combinations, {len(relationships.get('chong', []))} Clashes",
    }


def _analyze_complement(male_bazi, female_bazi) -> Dict[str, Any]:
    """
    Analyze BaZi complementarity.
    """
    # Analyze Five Elements complementarity
    from .professional_data import GAN_WUXING, ZHI_WUXING, WUXING

    male_elements = []
    female_elements = []

    # Get male Five Elements
    for pillar in [
        male_bazi.year_pillar,
        male_bazi.month_pillar,
        male_bazi.day_pillar,
        male_bazi.hour_pillar,
    ]:
        gan = pillar["天干"]["天干"]
        zhi = pillar["地支"]["地支"]
        male_elements.extend([GAN_WUXING.get(gan, ""), ZHI_WUXING.get(zhi, "")])

    # Get female Five Elements
    for pillar in [
        female_bazi.year_pillar,
        female_bazi.month_pillar,
        female_bazi.day_pillar,
        female_bazi.hour_pillar,
    ]:
        gan = pillar["天干"]["天干"]
        zhi = pillar["地支"]["地支"]
        female_elements.extend([GAN_WUXING.get(gan, ""), ZHI_WUXING.get(zhi, "")])

    # Count Five Elements distribution
    from collections import Counter

    male_counter = Counter(male_elements)
    female_counter = Counter(female_elements)

    # Calculate complementarity
    complement_score = 0
    for element in WUXING:
        male_count = male_counter.get(element, 0)
        female_count = female_counter.get(element, 0)

        # Complementarity bonus
        if male_count > 0 and female_count == 0:
            complement_score += 5
        elif male_count == 0 and female_count > 0:
            complement_score += 5
        elif abs(male_count - female_count) <= 1:
            complement_score += 2

    return {
        "score": min(90, 50 + complement_score),
        "male_elements": dict(male_counter),
        "female_elements": dict(female_counter),
        "description": f"Five Elements complementarity analysis, complement score {complement_score}",
    }


def _get_professional_suggestions(
    total_score: float,
    element_analysis: Dict[str, Any],
    zodiac_analysis: Dict[str, Any],
) -> List[str]:
    """
    Get professional marriage compatibility suggestions.
    """
    suggestions = []

    if total_score >= 80:
        suggestions.extend(["Perfect match, happy marriage", "Mutual support, growing old together"])
    elif total_score >= 70:
        suggestions.extend(["Good foundation, needs adjustment", "More communication and understanding for lasting relationship"])
    elif total_score >= 60:
        suggestions.extend(["Requires effort to maintain", "More tolerance, resolve conflicts"])
    else:
        suggestions.extend(["Consider carefully", "If marrying, choose an auspicious date for resolution"])

    # Add suggestions based on Five Elements analysis
    if element_analysis["relation"] == "←":
        suggestions.append("The wife should be more understanding, avoid being too dominant")
    elif element_analysis["relation"] == "→":
        suggestions.append("The husband should be more caring, avoid being too authoritative")

    # Add suggestions based on zodiac analysis
    if zodiac_analysis["relation"] == "Clash":
        suggestions.append("Zodiac clash, consider wearing resolution items or choosing an auspicious wedding date")

    return suggestions


def _get_compatibility_level(score: float) -> str:
    """
    Get compatibility grade.
    """
    if score >= 80:
        return "Excellent Match"
    elif score >= 70:
        return "Good Match"
    elif score >= 60:
        return "Average Match"
    else:
        return "Below Average Match"


def _get_compatibility_suggestions(score: float) -> List[str]:
    """Get compatibility suggestions"""
    if score >= 80:
        return ["Perfect match, happy marriage", "Mutual support, growing old together", "Continue maintaining good communication"]
    elif score >= 70:
        return ["Good foundation, needs adjustment", "More communication and understanding for lasting relationship", "Focus on cultivating common interests"]
    elif score >= 60:
        return [
            "Requires effort to maintain",
            "More tolerance, resolve conflicts",
            "Pre-marriage counseling recommended",
            "Establish marriage rules together",
        ]
    else:
        return [
            "Consider carefully",
            "If marrying, choose an auspicious date for resolution",
            "Do good deeds to improve fortune",
            "Professional guidance needed",
        ]
