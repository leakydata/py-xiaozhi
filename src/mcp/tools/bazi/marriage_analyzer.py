"""
BaZi marriage analysis extension module. Specialized for marriage timing, spouse information, and related analysis.
"""

from typing import Any, Dict, List

from .professional_data import TAOHUA_XING, get_ten_gods_relation, WUXING


class MarriageAnalyzer:
    """
    Marriage Analyzer.
    """

    def __init__(self):
        self.marriage_gods = {
            "male": ["正财", "偏财"],  # Male destiny wife star
            "female": ["正官", "七杀"],  # Female destiny husband star
        }

    def analyze_marriage_timing(
        self, eight_char_data: Dict[str, Any], gender: int
    ) -> Dict[str, Any]:
        """
        Analyze marriage timing.
        """
        result = {
            "marriage_star_analysis": self._analyze_marriage_star(
                eight_char_data, gender
            ),
            "marriage_age_range": self._predict_marriage_age(eight_char_data, gender),
            "favorable_years": self._get_favorable_marriage_years(
                eight_char_data, gender
            ),
            "marriage_obstacles": self._analyze_marriage_obstacles(eight_char_data),
            "spouse_characteristics": self._analyze_spouse_features(
                eight_char_data, gender
            ),
            "marriage_quality": self._evaluate_marriage_quality(
                eight_char_data, gender
            ),
        }
        return result

    def _analyze_marriage_star(
        self, eight_char_data: Dict[str, Any], gender: int
    ) -> Dict[str, Any]:
        """Analyze spouse star"""
        from .professional_data import ZHI_CANG_GAN, CHANGSHENG_TWELVE, get_changsheng_state

        gender_key = "male" if gender == 1 else "female"
        target_gods = self.marriage_gods[gender_key]

        # Unified Heavenly Stem data format extraction
        year_gan = self._extract_gan_from_pillar(eight_char_data.get("year", {}))
        month_gan = self._extract_gan_from_pillar(eight_char_data.get("month", {}))
        day_gan = self._extract_gan_from_pillar(eight_char_data.get("day", {}))
        hour_gan = self._extract_gan_from_pillar(eight_char_data.get("hour", {}))

        marriage_stars = []

        # Check Heavenly Stem spouse stars
        for position, gan in [
            ("Year Stem", year_gan),
            ("Month Stem", month_gan),
            ("Hour Stem", hour_gan),
        ]:
            if gan and gan != day_gan:
                ten_god = get_ten_gods_relation(day_gan, gan)
                if ten_god in target_gods:
                    # Get more detailed analysis
                    star_info = {
                        "position": position,
                        "star": ten_god,
                        "strength": self._evaluate_star_strength(position),
                        "element": self._get_gan_element(gan),
                        "quality": self._evaluate_star_quality(position, ten_god),
                        "seasonal_strength": self._get_seasonal_strength(gan, month_gan),
                    }
                    marriage_stars.append(star_info)

        # Analyze spouse stars in Earthly Branch hidden stems
        for position, pillar in [
            ("Year Branch", eight_char_data.get("year", {})),
            ("Month Branch", eight_char_data.get("month", {})),
            ("Hour Branch", eight_char_data.get("hour", {})),
        ]:
            zhi_name = self._extract_zhi_from_pillar(pillar)
            if zhi_name and zhi_name in ZHI_CANG_GAN:
                cang_gan_data = ZHI_CANG_GAN[zhi_name]

                for hidden_gan, strength in cang_gan_data.items():
                    if hidden_gan != day_gan:
                        ten_god = get_ten_gods_relation(day_gan, hidden_gan)
                        if ten_god in target_gods:
                            # Determine type based on hidden stem strength
                            gan_type = self._determine_canggan_type(strength)

                            star_info = {
                                "position": position,
                                "star": ten_god,
                                "strength": self._get_hidden_strength(gan_type),
                                "element": self._get_gan_element(hidden_gan),
                                "type": f"Hidden Stem {gan_type}",
                                "quality": self._evaluate_hidden_star_quality(zhi_name, hidden_gan, strength),
                                "changsheng_state": get_changsheng_state(day_gan, zhi_name),
                            }
                            marriage_stars.append(star_info)

        # Comprehensive spouse star analysis
        star_analysis = self._comprehensive_star_analysis(marriage_stars, day_gan, gender)

        return {
            "has_marriage_star": len(marriage_stars) > 0,
            "marriage_stars": marriage_stars,
            "star_count": len(marriage_stars),
            "star_strength": star_analysis["strength"],
            "star_quality": star_analysis["quality"],
            "star_distribution": star_analysis["distribution"],
            "marriage_potential": star_analysis["potential"],
            "improvement_suggestions": star_analysis["suggestions"],
        }

    def _predict_marriage_age(
        self, eight_char_data: Dict[str, Any], gender: int
    ) -> Dict[str, Any]:
        """Predict marriage age range"""
        from .professional_data import (
            CHANGSHENG_TWELVE, TIANYI_GUIREN, WENCHANG_GUIREN,
            HUAGAI_XING, GAN_WUXING, ZHI_WUXING, WUXING_RELATIONS
        )

        day_gan = self._extract_gan_from_pillar(eight_char_data.get("day", {}))
        day_zhi = self._extract_zhi_from_pillar(eight_char_data.get("day", {}))
        month_gan = self._extract_gan_from_pillar(eight_char_data.get("month", {}))
        month_zhi = self._extract_zhi_from_pillar(eight_char_data.get("month", {}))
        year_zhi = self._extract_zhi_from_pillar(eight_char_data.get("year", {}))
        hour_zhi = self._extract_zhi_from_pillar(eight_char_data.get("hour", {}))

        # Professional analysis factors
        factors = {
            "early_signs": [],
            "late_signs": [],
            "score": 50,  # Base score
            "detailed_analysis": []
        }

        # 1. Day Branch analysis (most important)
        if day_zhi in "子午卯酉":
            factors["early_signs"].append("Day Branch Peach Blossom Star")
            factors["score"] -= 12
            factors["detailed_analysis"].append("Day Branch Peach Blossom Star favors early romantic development")

        if day_zhi in "寅申巳亥":
            factors["early_signs"].append("Day Branch Post Horse Star")
            factors["score"] -= 8
            factors["detailed_analysis"].append("Day Branch Post Horse Star indicates change, romance comes quickly")

        if day_zhi in "辰戌丑未":
            factors["late_signs"].append("Day Branch Four Storages")
            factors["score"] += 15
            factors["detailed_analysis"].append("Day Branch Four Storages indicates stability, romantic development is slower")

        # 2. Spouse star analysis
        marriage_star_analysis = self._analyze_marriage_star(eight_char_data, gender)
        star_strength = marriage_star_analysis.get("star_strength", "Weak")
        star_count = marriage_star_analysis.get("star_count", 0)

        if star_strength == "Very Strong":
            factors["score"] -= 8
            factors["early_signs"].append("Very strong spouse star")
            factors["detailed_analysis"].append("Very strong spouse star, excellent romantic fortune")
        elif star_strength == "Strong":
            factors["score"] -= 5
            factors["early_signs"].append("Strong spouse star")
        elif star_strength == "Weak" or star_strength == "No Star":
            factors["score"] += 10
            factors["late_signs"].append("Weak spouse star")
            factors["detailed_analysis"].append("Spouse star is weak, patience required")

        # 3. Twelve Stages of Life Cycle analysis
        if day_gan in CHANGSHENG_TWELVE:
            changsheng_state = CHANGSHENG_TWELVE[day_gan].get(day_zhi, "")
            if changsheng_state in ["长生", "帝旺", "建禄"]:
                factors["score"] -= 6
                factors["early_signs"].append(f"Day Master at Day Branch {changsheng_state}")
                factors["detailed_analysis"].append(f"Day Master at {changsheng_state}, confident and attractive")
            elif changsheng_state in ["墓", "死", "绝"]:
                factors["score"] += 8
                factors["late_signs"].append(f"Day Master at Day Branch {changsheng_state}")
                factors["detailed_analysis"].append(f"Day Master at {changsheng_state}, needs time to accumulate")

        # 4. Shen Sha analysis
        all_zhi = [year_zhi, month_zhi, day_zhi, hour_zhi]

        # Tianyi Noble
        tianyi_zhi = TIANYI_GUIREN.get(day_gan, "")
        if tianyi_zhi and any(zhi in tianyi_zhi for zhi in all_zhi):
            factors["score"] -= 5
            factors["early_signs"].append("Has Tianyi Noble")
            factors["detailed_analysis"].append("Tianyi Noble assists, noble person helps find a good match")

        # Huagai Star
        huagai_zhi = HUAGAI_XING.get(day_zhi, "")
        if huagai_zhi and any(zhi == huagai_zhi for zhi in all_zhi):
            factors["score"] += 12
            factors["late_signs"].append("Has Huagai Star")
            factors["detailed_analysis"].append("Huagai Star indicates solitude, romantic development is slower")

        # 5. Five Elements balance analysis
        day_element = GAN_WUXING.get(day_gan, "")
        month_element = ZHI_WUXING.get(month_zhi, "")

        if day_element and month_element:
            relation = WUXING_RELATIONS.get((month_element, day_element), "")
            if relation == "↓":  # Month generates Day Master
                factors["score"] -= 6
                factors["early_signs"].append("Month generates Day Master")
                factors["detailed_analysis"].append("Month generates Day Master, favorable timing for romance")
            elif relation == "←":  # Month overcomes Day Master
                factors["score"] += 8
                factors["late_signs"].append("Month overcomes Day Master")
                factors["detailed_analysis"].append("Month overcomes Day Master, needs time to build confidence")

        # 6. Spouse palace analysis
        spouse_palace_analysis = self._analyze_spouse_palace(day_zhi, month_zhi)
        factors["score"] += spouse_palace_analysis["age_adjustment"]
        factors["detailed_analysis"].extend(spouse_palace_analysis["analysis"])

        # 7. Gender difference analysis
        if gender == 1:  # Male
            factors["score"] -= 3  # Males statistically marry slightly later
            factors["detailed_analysis"].append("Males statistically marry at a slightly later age")
        else:  # Female
            factors["score"] += 2
            factors["detailed_analysis"].append("Females tend to develop romantic relationships relatively earlier")

        # 8. Comprehensive assessment
        final_score = max(20, min(80, factors["score"]))

        # Predict age range based on score
        if final_score <= 30:
            age_prediction = "Very Early"
            age_range = "18-24 years"
            tendency = "Excellent romantic fortune, good match found early"
        elif final_score <= 40:
            age_prediction = "Relatively Early"
            age_range = "22-27 years"
            tendency = "Smooth romantic development, suitable for early marriage"
        elif final_score <= 60:
            age_prediction = "Moderate"
            age_range = "25-30 years"
            tendency = "Normal romantic development, suitable for marriage at appropriate age"
        elif final_score <= 70:
            age_prediction = "Relatively Late"
            age_range = "28-35 years"
            tendency = "Slower romantic development, patience required"
        else:
            age_prediction = "Very Late"
            age_range = "30-40 years"
            tendency = "Difficult romantic development, need to proactively create opportunities"

        return {
            "prediction": age_prediction,
            "age_range": age_range,
            "tendency": tendency,
            "score": final_score,
            "early_factors": factors["early_signs"],
            "late_factors": factors["late_signs"],
            "detailed_analysis": factors["detailed_analysis"],
            "analysis_basis": f"Professional analysis based on Day Pillar {day_gan}{day_zhi}",
            "confidence": self._calculate_prediction_confidence(factors),
        }

    def _get_favorable_marriage_years(
        self, eight_char_data: Dict[str, Any], gender: int
    ) -> List[str]:
        """
        Get favorable marriage years - using complete Earthly Branch relationship analysis.
        """
        from .professional_data import ZHI_RELATIONS, ZHI_SAN_HE, ZHI_SAN_HUI, YIMA_XING

        day_zhi = eight_char_data.get("day", {}).get("earth_branch", {}).get("name", "")
        month_zhi = eight_char_data.get("month", {}).get("earth_branch", {}).get("name", "")
        year_zhi = eight_char_data.get("year", {}).get("earth_branch", {}).get("name", "")

        favorable_branches = []

        # 1. Six Combination relationship - most favorable
        if day_zhi in ZHI_RELATIONS:
            liuhe_zhi = ZHI_RELATIONS[day_zhi].get("六", "")
            if liuhe_zhi:
                favorable_branches.append({"zhi": liuhe_zhi, "reason": "Day Branch Six Combination", "priority": "High"})

        # 2. Three Combination relationship - very favorable
        for sanhe_combo, element in ZHI_SAN_HE.items():
            if day_zhi in sanhe_combo:
                # Find other Earthly Branches in the Three Combination
                for zhi in sanhe_combo:
                    if zhi != day_zhi:
                        favorable_branches.append({"zhi": zhi, "reason": f"Three Combination {element} Formation", "priority": "High"})

        # 3. Three Meeting Direction - favorable
        for sanhui_combo, element in ZHI_SAN_HUI.items():
            if day_zhi in sanhui_combo:
                for zhi in sanhui_combo:
                    if zhi != day_zhi:
                        favorable_branches.append({"zhi": zhi, "reason": f"Three Meeting {element} Direction", "priority": "Medium"})

        # 4. Peach Blossom Star - good romantic fortune
        taohua_zhi = TAOHUA_XING.get(day_zhi, "")
        if taohua_zhi:
            favorable_branches.append({"zhi": taohua_zhi, "reason": "Peach Blossom Star", "priority": "Medium"})

        # 5. Post Horse Star - year of change, suitable for marriage
        yima_zhi = YIMA_XING.get(day_zhi, "")
        if yima_zhi:
            favorable_branches.append({"zhi": yima_zhi, "reason": "Post Horse Star", "priority": "Medium"})

        # 6. Month Branch related favorable years
        if month_zhi in ZHI_RELATIONS:
            month_liuhe = ZHI_RELATIONS[month_zhi].get("六", "")
            if month_liuhe:
                favorable_branches.append({"zhi": month_liuhe, "reason": "Month Branch Six Combination", "priority": "Medium"})

        # 7. Year Branch related favorable years
        if year_zhi in ZHI_RELATIONS:
            year_liuhe = ZHI_RELATIONS[year_zhi].get("六", "")
            if year_liuhe:
                favorable_branches.append({"zhi": year_liuhe, "reason": "Year Branch Six Combination", "priority": "Low"})

        # Deduplicate and sort by priority
        unique_branches = {}
        for branch in favorable_branches:
            zhi = branch["zhi"]
            if zhi not in unique_branches or branch["priority"] == "High":
                unique_branches[zhi] = branch

        # Sort by priority
        priority_order = {"High": 1, "Medium": 2, "Low": 3}
        sorted_branches = sorted(unique_branches.values(),
                               key=lambda x: priority_order[x["priority"]])

        return [f"{branch['zhi']} year ({branch['reason']})" for branch in sorted_branches]

    def _analyze_spouse_palace(self, day_zhi: str, month_zhi: str) -> Dict[str, Any]:
        """Analyze spouse palace (Day Branch) impact on marriage timing"""
        from .professional_data import ZHI_WUXING, WUXING_RELATIONS

        palace_analysis = {"age_adjustment": 0, "analysis": []}

        # Day Branch Five Elements analysis
        day_element = ZHI_WUXING.get(day_zhi, "")
        month_element = ZHI_WUXING.get(month_zhi, "")

        if day_element and month_element:
            relation = WUXING_RELATIONS.get((month_element, day_element), "")
            if relation == "↓":  # Month generates spouse palace
                palace_analysis["age_adjustment"] -= 4
                palace_analysis["analysis"].append("Month generates spouse palace, spouse palace is empowered")
            elif relation == "←":  # Month overcomes spouse palace
                palace_analysis["age_adjustment"] += 6
                palace_analysis["analysis"].append("Month overcomes spouse palace, spouse palace is restricted")

        # Spouse palace characteristic analysis
        palace_characteristics = {
            "子": {"adjustment": -2, "desc": "Zi Water spouse palace is flexible, romantic development is faster"},
            "丑": {"adjustment": 4, "desc": "Chou Earth spouse palace is steady, romantic development is slower"},
            "寅": {"adjustment": -3, "desc": "Yin Wood spouse palace is active, romantic development is faster"},
            "卯": {"adjustment": 0, "desc": "Mao Wood spouse palace is gentle, romantic development is normal"},
            "辰": {"adjustment": 5, "desc": "Chen Earth spouse palace is conservative, romantic development is slower"},
            "巳": {"adjustment": -1, "desc": "Si Fire spouse palace is wise, romantic development is moderate"},
            "午": {"adjustment": -4, "desc": "Wu Fire spouse palace is passionate, romantic development is faster"},
            "未": {"adjustment": 3, "desc": "Wei Earth spouse palace is gentle, romantic development is slightly slow"},
            "申": {"adjustment": -2, "desc": "Shen Metal spouse palace is adaptable, romantic development is faster"},
            "酉": {"adjustment": 1, "desc": "You Metal spouse palace is perfectionist, romantic development is moderate"},
            "戌": {"adjustment": 6, "desc": "Xu Earth spouse palace is loyal, romantic development is slower"},
            "亥": {"adjustment": -1, "desc": "Hai Water spouse palace is inclusive, romantic development is moderate"},
        }

        if day_zhi in palace_characteristics:
            char = palace_characteristics[day_zhi]
            palace_analysis["age_adjustment"] += char["adjustment"]
            palace_analysis["analysis"].append(char["desc"])

        return palace_analysis

    def _calculate_prediction_confidence(self, factors: Dict[str, Any]) -> str:
        """Calculate prediction confidence"""
        early_count = len(factors["early_signs"])
        late_count = len(factors["late_signs"])
        analysis_count = len(factors["detailed_analysis"])

        # Calculate factor consistency
        if early_count >= 4 and late_count <= 1:
            consistency = "High"
        elif late_count >= 4 and early_count <= 1:
            consistency = "High"
        elif abs(early_count - late_count) <= 1:
            consistency = "Medium"
        else:
            consistency = "Low"

        # Calculate analysis depth
        if analysis_count >= 8:
            depth = "Thorough"
        elif analysis_count >= 5:
            depth = "Sufficient"
        else:
            depth = "General"

        # Comprehensive assessment
        if consistency == "High" and depth == "Thorough":
            return "Very High"
        elif consistency == "High" or depth == "Thorough":
            return "High"
        elif consistency == "Medium" and depth == "Sufficient":
            return "Fairly High"
        elif consistency == "Medium" or depth == "Sufficient":
            return "Medium"
        else:
            return "Fairly Low"

    def _analyze_marriage_obstacles(self, eight_char_data: Dict[str, Any]) -> List[str]:
        """
        Analyze marriage obstacles.
        """
        from .professional_data import ZHI_RELATIONS, analyze_zhi_combinations, HUAGAI_XING

        obstacles = []

        # Extract four pillar Earthly Branches
        zhi_list = [
            eight_char_data.get("year", {}).get("earth_branch", {}).get("name", ""),
            eight_char_data.get("month", {}).get("earth_branch", {}).get("name", ""),
            eight_char_data.get("day", {}).get("earth_branch", {}).get("name", ""),
            eight_char_data.get("hour", {}).get("earth_branch", {}).get("name", ""),
        ]

        # Get Day Branch (spouse palace)
        day_zhi = zhi_list[2] if len(zhi_list) > 2 else ""

        # Use professional function to analyze Earthly Branch combinations
        zhi_relations = analyze_zhi_combinations(zhi_list)

        # 1. Analyze Clashes - most serious obstacle
        if zhi_relations.get("chong"):
            for chong_desc in zhi_relations["chong"]:
                if day_zhi in chong_desc:
                    obstacles.append(f"Spouse palace {chong_desc}, seriously affects marriage stability")
                else:
                    obstacles.append(f"{chong_desc}, affects marital harmony")

        # 2. Analyze Punishments - second most serious
        if zhi_relations.get("xing"):
            for xing_desc in zhi_relations["xing"]:
                if day_zhi in xing_desc:
                    obstacles.append(f"Spouse palace {xing_desc}, tense couple relationship")
                else:
                    obstacles.append(f"{xing_desc}, complex family relationships")

        # 3. Analyze Harm - third most serious
        if zhi_relations.get("hai"):
            for hai_desc in zhi_relations["hai"]:
                if day_zhi in hai_desc:
                    obstacles.append(f"Spouse palace {hai_desc}, emotions easily hurt")
                else:
                    obstacles.append(f"{hai_desc}, obstacles in romantic development")

        # 4. Huagai Star analysis - solitary tendency
        day_gan = self._extract_gan_from_pillar(eight_char_data.get("day", {}))
        if day_gan:
            huagai_zhi = HUAGAI_XING.get(day_gan, "")
            if huagai_zhi and huagai_zhi in zhi_list:
                obstacles.append(f"Destiny has Huagai Star, solitary personality, not easy to approach")

        # 5. Spouse palace special situation analysis
        if day_zhi:
            spouse_palace_obstacles = self._analyze_spouse_palace_obstacles(day_zhi, zhi_list)
            obstacles.extend(spouse_palace_obstacles)

        # 6. Spouse star being overcome analysis
        marriage_star_analysis = self._analyze_marriage_star(eight_char_data, 1)  # Use male analysis first
        if marriage_star_analysis.get("star_count", 0) == 0:
            obstacles.append("No obvious spouse star in BaZi, difficult romantic development")
        elif marriage_star_analysis.get("star_strength") in ["Weak", "No Star"]:
            obstacles.append("Spouse star is weak, poor romantic fortune")

        # 7. Five Elements imbalance analysis
        wuxing_obstacles = self._analyze_wuxing_marriage_obstacles(eight_char_data)
        obstacles.extend(wuxing_obstacles)

        # Deduplicate and limit quantity
        unique_obstacles = list(set(obstacles))
        return unique_obstacles[:8]  # Return at most 8 main obstacles

    def _analyze_spouse_palace_obstacles(self, day_zhi: str, zhi_list: List[str]) -> List[str]:
        """Analyze spouse palace special obstacles"""
        obstacles = []

        # Spouse palace special situations
        palace_issues = {
            "辰": "Chen Earth spouse palace is conservative, slow romantic development",
            "戌": "Xu Earth spouse palace is stubborn, prone to emotional disputes",
            "丑": "Chou Earth spouse palace is introverted, poor at expressing emotions",
            "未": "Wei Earth spouse palace is sensitive, prone to emotional fluctuations",
        }

        if day_zhi in palace_issues:
            obstacles.append(palace_issues[day_zhi])

        # Spouse palace appearing repeatedly
        if zhi_list.count(day_zhi) > 1:
            obstacles.append(f"Spouse palace {day_zhi} appears repeatedly, emotional pattern is fixed")

        return obstacles

    def _analyze_wuxing_marriage_obstacles(self, eight_char_data: Dict[str, Any]) -> List[str]:
        """Analyze Five Elements imbalance impact on marriage"""
        from .professional_data import GAN_WUXING, ZHI_WUXING

        obstacles = []

        # Collect all Five Elements
        wuxing_count = {element: 0 for element in WUXING}

        # Heavenly Stem Five Elements
        for pillar_key in ["year", "month", "day", "hour"]:
            gan = self._extract_gan_from_pillar(eight_char_data.get(pillar_key, {}))
            if gan:
                element = GAN_WUXING.get(gan, "")
                if element in wuxing_count:
                    wuxing_count[element] += 1

        # Earthly Branch Five Elements
        for pillar_key in ["year", "month", "day", "hour"]:
            zhi = self._extract_zhi_from_pillar(eight_char_data.get(pillar_key, {}))
            if zhi:
                element = ZHI_WUXING.get(zhi, "")
                if element in wuxing_count:
                    wuxing_count[element] += 1

        # Analyze Five Elements imbalance
        total_count = sum(wuxing_count.values())
        if total_count > 0:
            # Check for excessive or deficient elements
            for element, count in wuxing_count.items():
                ratio = count / total_count
                if ratio >= 0.5:  # Over 50%
                    obstacles.append(f"{element} element is excessive, stubborn personality affects romance")
                elif ratio == 0:  # Completely missing
                    element_effects = {
                        "金": "Missing Metal, not decisive enough, misses opportunities",
                        "木": "Missing Wood, not proactive enough, passive in romance",
                        "水": "Missing Water, not flexible enough, rigid in romance",
                        "火": "Missing Fire, not passionate enough, cold in romance",
                        "土": "Missing Earth, not stable enough, changeable in romance",
                    }
                    if element in element_effects:
                        obstacles.append(element_effects[element])

        return obstacles

    def _analyze_spouse_features(
        self, eight_char_data: Dict[str, Any], gender: int
    ) -> Dict[str, str]:
        """
        Analyze spouse characteristics - using Five Elements generating/overcoming analysis.
        """
        from .professional_data import ZHI_WUXING, GAN_WUXING, WUXING_RELATIONS, ZHI_CANG_GAN

        day_zhi = eight_char_data.get("day", {}).get("earth_branch", {}).get("name", "")
        day_gan = self._extract_gan_from_pillar(eight_char_data.get("day", {}))
        month_zhi = self._extract_zhi_from_pillar(eight_char_data.get("month", {}))

        # Basic spouse features
        basic_features = self._get_basic_spouse_features(day_zhi)

        # Five Elements influence
        wuxing_influence = self._analyze_wuxing_spouse_influence(day_zhi, month_zhi)

        # Hidden stem influence
        canggan_influence = self._analyze_canggan_spouse_influence(day_zhi, day_gan)

        # Spouse star influence
        star_influence = self._analyze_marriage_star_spouse_influence(eight_char_data, gender)

        # Comprehensive analysis
        return {
            "personality": self._synthesize_personality(basic_features["personality"], wuxing_influence["personality"], star_influence["personality"]),
            "appearance": self._synthesize_appearance(basic_features["appearance"], wuxing_influence["appearance"], canggan_influence["appearance"]),
            "career_tendency": self._synthesize_career(basic_features["career"], wuxing_influence["career"], star_influence["career"]),
            "relationship_mode": star_influence["relationship_mode"],
            "compatibility": self._evaluate_compatibility(day_gan, day_zhi, month_zhi),
            "improvement_suggestions": self._generate_spouse_improvement_suggestions(day_zhi, wuxing_influence, star_influence),
        }

    def _get_basic_spouse_features(self, day_zhi: str) -> Dict[str, str]:
        """Get basic spouse features"""
        spouse_features = {
            "子": {
                "personality": "Smart and resourceful, good at managing finances, lively personality, strong adaptability",
                "appearance": "Medium build, delicate features, bright eyes",
                "career": "Technology, finance, trade, IT industry",
            },
            "丑": {
                "personality": "Down-to-earth and steady, hardworking, slightly introverted, strong sense of responsibility",
                "appearance": "Sturdy build, simple appearance, composed temperament",
                "career": "Agriculture, construction, manufacturing, service industry",
            },
            "寅": {
                "personality": "Enthusiastic and outgoing, leadership ability, slightly impatient, strong sense of justice",
                "appearance": "Tall build, square face, masculine temperament",
                "career": "Management, government, education, sports industry",
            },
            "卯": {
                "personality": "Gentle and kind, artistic temperament, pursuit of perfection, sensitive and delicate",
                "appearance": "Slender build, beautiful features, elegant temperament",
                "career": "Arts, design, beauty, cultural industry",
            },
            "辰": {
                "personality": "Mature and steady, responsible, rather conservative, deep-thinking",
                "appearance": "Medium build, honest appearance, steady temperament",
                "career": "Civil engineering, real estate, warehousing, logistics",
            },
            "巳": {
                "personality": "Smart and wise, socially adept, mysterious, quick-thinking",
                "appearance": "Moderate build, refined features, mysterious temperament",
                "career": "Culture, consulting, communications, psychology industry",
            },
            "午": {
                "personality": "Passionate and outgoing, proactive, slightly impatient, strong desire to express",
                "appearance": "Well-proportioned build, rosy complexion, passionate temperament",
                "career": "Energy, sports, entertainment, sales industry",
            },
            "未": {
                "personality": "Gentle and caring, thoughtful, inclusive, slightly sensitive",
                "appearance": "Medium build, gentle features, soft temperament",
                "career": "Service, food & beverage, gardening, nursing industry",
            },
            "申": {
                "personality": "Quick-witted and flexible, adaptable, slightly changeable, strong innovation ability",
                "appearance": "Agile build, alert features, lively temperament",
                "career": "Manufacturing, transportation, technology, innovation industry",
            },
            "酉": {
                "personality": "Dignified and elegant, image-conscious, perfectionist tendency, perfectionism",
                "appearance": "Petite build, proper features, refined temperament",
                "career": "Finance, jewelry, fashion, beauty industry",
            },
            "戌": {
                "personality": "Loyal and reliable, strong sense of justice, slightly stubborn, protective",
                "appearance": "Solid build, square face, upright temperament",
                "career": "Military/police, security, construction, legal industry",
            },
            "亥": {
                "personality": "Kind and simple, compassionate, rather emotional, highly inclusive",
                "appearance": "Full-figured, kind face, gentle temperament",
                "career": "Water conservancy, fishery, charity, medical industry",
            },
        }

        return spouse_features.get(day_zhi, {
            "personality": "Gentle personality, upright character",
            "appearance": "Proper appearance, good temperament",
            "career": "All industries are possible"
        })

    def _analyze_wuxing_spouse_influence(self, day_zhi: str, month_zhi: str) -> Dict[str, str]:
        """Analyze Five Elements influence on spouse characteristics"""
        from .professional_data import ZHI_WUXING, WUXING_RELATIONS

        day_element = ZHI_WUXING.get(day_zhi, "")
        month_element = ZHI_WUXING.get(month_zhi, "")

        influence = {"personality": "", "appearance": "", "career": ""}

        if day_element and month_element:
            relation = WUXING_RELATIONS.get((month_element, day_element), "")

            if relation == "↓":  # Month generates spouse palace
                influence["personality"] = "Supported by monthly command, positive and optimistic personality"
                influence["appearance"] = "Good complexion, energetic"
                influence["career"] = "Good career fortune, smooth development"
            elif relation == "←":  # Month overcomes spouse palace
                influence["personality"] = "Restricted by monthly command, rather reserved personality"
                influence["appearance"] = "Slightly fatigued, needs rest"
                influence["career"] = "Career development has obstacles, effort needed"
            elif relation == "=":  # Same element
                influence["personality"] = "Stable personality, not easily changeable"
                influence["appearance"] = "Coordinated appearance, stable temperament"
                influence["career"] = "Career development progresses steadily"

        return influence

    def _analyze_canggan_spouse_influence(self, day_zhi: str, day_gan: str) -> Dict[str, str]:
        """Analyze hidden stem influence on spouse characteristics"""
        from .professional_data import ZHI_CANG_GAN, GAN_WUXING

        influence = {"appearance": ""}

        if day_zhi in ZHI_CANG_GAN:
            canggan_data = ZHI_CANG_GAN[day_zhi]

            # Analyze main qi influence
            main_gans = [gan for gan, strength in canggan_data.items() if strength >= 5]
            if main_gans:
                main_gan = main_gans[0]
                main_element = GAN_WUXING.get(main_gan, "")

                element_appearance = {
                    "金": "Delicate features, fair skin, well-proportioned bone structure",
                    "木": "Slender build, refined features, literary temperament",
                    "水": "Round face, smooth skin, gentle eyes",
                    "火": "Rosy complexion, energetic, passionate temperament",
                    "土": "Honest appearance, solid build, steady temperament",
                }

                if main_element in element_appearance:
                    influence["appearance"] = element_appearance[main_element]

        return influence

    def _analyze_marriage_star_spouse_influence(self, eight_char_data: Dict[str, Any], gender: int) -> Dict[str, str]:
        """Analyze spouse star influence on spouse characteristics"""
        star_analysis = self._analyze_marriage_star(eight_char_data, gender)

        influence = {"personality": "", "career": "", "relationship_mode": ""}

        if star_analysis["has_marriage_star"]:
            star_strength = star_analysis["star_strength"]
            star_quality = star_analysis["star_quality"]

            # Influence based on spouse star strength
            if star_strength in ["Very Strong", "Strong"]:
                influence["personality"] = "Distinctive personality, prominent individuality"
                influence["career"] = "Strong career ability, development potential"
                influence["relationship_mode"] = "Intense feelings, stable relationship"
            elif star_strength == "Medium":
                influence["personality"] = "Moderate personality, balanced individuality"
                influence["career"] = "Steady career development"
                influence["relationship_mode"] = "Harmonious feelings, balanced relationship"
            else:
                influence["personality"] = "Reserved personality, less prominent individuality"
                influence["career"] = "Career development needs time"
                influence["relationship_mode"] = "Slower romantic development, needs cultivation"
        else:
            influence["personality"] = "Personality hard to grasp, changeable individuality"
            influence["career"] = "Career direction unclear"
            influence["relationship_mode"] = "Difficult romantic development, patience needed"

        return influence

    def _synthesize_personality(self, basic: str, wuxing: str, star: str) -> str:
        """Synthesize personality characteristics"""
        result = basic
        if wuxing:
            result += f", {wuxing}"
        if star:
            result += f", {star}"
        return result

    def _synthesize_appearance(self, basic: str, wuxing: str, canggan: str) -> str:
        """Synthesize appearance characteristics"""
        result = basic
        if canggan:
            result = canggan  # Hidden stem influence is more direct
        if wuxing:
            result += f", {wuxing}"
        return result

    def _synthesize_career(self, basic: str, wuxing: str, star: str) -> str:
        """Synthesize career tendency"""
        result = basic
        if star:
            result = f"{basic}, {star}"
        if wuxing:
            result += f", {wuxing}"
        return result

    def _evaluate_compatibility(self, day_gan: str, day_zhi: str, month_zhi: str) -> str:
        """Evaluate spouse compatibility"""
        from .professional_data import ZHI_RELATIONS

        compatibility_score = 70  # Base score

        # Check Earthly Branch relationships
        if day_zhi in ZHI_RELATIONS:
            relations = ZHI_RELATIONS[day_zhi]
            if month_zhi == relations.get("六", ""):
                compatibility_score += 20
                return "Excellent spouse compatibility, a natural pair"
            elif month_zhi in relations.get("合", ()):
                compatibility_score += 15
                return "Very good spouse compatibility, harmonious together"
            elif month_zhi == relations.get("冲", ""):
                compatibility_score -= 30
                return "Poor spouse compatibility, needs adjustment"

        if compatibility_score >= 85:
            return "Excellent spouse compatibility"
        elif compatibility_score >= 70:
            return "Good spouse compatibility"
        elif compatibility_score >= 50:
            return "Average spouse compatibility"
        else:
            return "Poor spouse compatibility"

    def _generate_spouse_improvement_suggestions(self, day_zhi: str, wuxing_influence: Dict[str, str], star_influence: Dict[str, str]) -> List[str]:
        """Generate spouse relationship improvement suggestions"""
        suggestions = []

        # Give suggestions based on spouse palace characteristics
        zhi_suggestions = {
            "子": ["Communicate more, avoid misunderstandings", "Give enough personal space"],
            "丑": ["Be patient, don't rush", "Give more care and understanding"],
            "寅": ["Avoid being competitive, learn to compromise", "Give enough room for development"],
            "卯": ["Create a romantic atmosphere, enhance feelings", "Respect each other's aesthetics and pursuits"],
            "辰": ["Build trust, avoid suspicion", "Provide a sense of security and stability"],
            "巳": ["Maintain mystery, don't be too direct", "Engage in more intellectual exchanges"],
            "午": ["Maintain passion, avoid emotional coldness", "Give full attention and praise"],
            "未": ["Be more caring and considerate, treat gently", "Avoid being too harsh with criticism"],
            "申": ["Keep things fresh, avoid monotony", "Provide variety and stimulation"],
            "酉": ["Pay attention to image, maintain tidiness", "Avoid roughness and carelessness"],
            "戌": ["Build trust, remain loyal", "Provide a sense of security and belonging"],
            "亥": ["Give more love, avoid causing hurt", "Maintain inclusiveness and understanding"],
        }

        if day_zhi in zhi_suggestions:
            suggestions.extend(zhi_suggestions[day_zhi])

        # Give suggestions based on Five Elements influence
        if "reserved" in wuxing_influence.get("personality", "").lower():
            suggestions.append("Encourage more expression, build an open communication environment")

        # Give suggestions based on spouse star influence
        if "slower" in star_influence.get("relationship_mode", "").lower():
            suggestions.append("Be patient, gradually cultivate feelings")

        return suggestions[:4]  # Return at most 4 suggestions

    def _get_spouse_appearance(self, day_zhi: str) -> str:
        """
        Predict spouse appearance based on Day Branch.
        """
        appearance_map = {
            "子": "Medium build, delicate features",
            "丑": "Sturdy build, simple appearance",
            "寅": "Tall build, square face",
            "卯": "Slender build, beautiful features",
            "辰": "Medium build, honest appearance",
            "巳": "Moderate build, refined features",
            "午": "Well-proportioned build, rosy complexion",
            "未": "Medium build, gentle features",
            "申": "Agile build, alert features",
            "酉": "Petite build, proper features",
            "戌": "Solid build, square face",
            "亥": "Full-figured, kind face",
        }
        return appearance_map.get(day_zhi, "Proper appearance")

    def _get_spouse_career(self, day_zhi: str) -> str:
        """
        Predict spouse career tendency based on Day Branch.
        """
        career_map = {
            "子": "Technology, finance, trade related",
            "丑": "Agriculture, construction, service industry",
            "寅": "Management, government, education industry",
            "卯": "Arts, design, beauty industry",
            "辰": "Civil engineering, real estate, warehousing",
            "巳": "Culture, consulting, communications",
            "午": "Energy, sports, entertainment",
            "未": "Service, food & beverage, gardening",
            "申": "Manufacturing, transportation, technology",
            "酉": "Finance, jewelry, fashion",
            "戌": "Military/police, security, construction",
            "亥": "Water conservancy, fishery, charity",
        }
        return career_map.get(day_zhi, "All industries are possible")

    def _evaluate_marriage_quality(
        self, eight_char_data: Dict[str, Any], gender: int
    ) -> Dict[str, Any]:
        """
        Evaluate marriage quality.
        """
        day_gan = eight_char_data.get("day", {}).get("heaven_stem", {}).get("name", "")
        day_zhi = eight_char_data.get("day", {}).get("earth_branch", {}).get("name", "")

        # Day Pillar combination analysis for marriage quality
        good_combinations = [
            "甲子",
            "乙丑",
            "丙寅",
            "丁卯",
            "戊辰",
            "己巳",
            "庚午",
            "辛未",
            "壬申",
            "癸酉",
        ]

        day_pillar = day_gan + day_zhi
        quality_score = 75  # Base score

        if day_pillar in good_combinations:
            quality_score += 10

        return {
            "score": quality_score,
            "level": (
                "Excellent"
                if quality_score >= 85
                else "Good" if quality_score >= 75 else "Average"
            ),
            "advice": self._get_marriage_advice(quality_score),
        }

    def _get_marriage_advice(self, score: int) -> str:
        """
        Get marriage advice.
        """
        if score >= 85:
            return "Good marriage fortune, focus on communication, relationship can be lasting and stable"
        elif score >= 75:
            return "Solid marriage foundation, both parties need to work together to maintain feelings"
        else:
            return "Marriage needs more tolerance and understanding, more communication recommended to resolve conflicts"

    def _evaluate_star_strength(self, position: str) -> str:
        """Evaluate star strength"""
        strength_map = {
            "Year Stem": "Strong",
            "Month Stem": "Strongest",
            "Hour Stem": "Medium",
            "Year Branch": "Medium Strong",
            "Month Branch": "Strong",
            "Hour Branch": "Medium",
        }
        return strength_map.get(position, "Weak")

    def _extract_gan_from_pillar(self, pillar: Dict[str, Any]) -> str:
        """
        Extract Heavenly Stem from pillar.
        """
        if "天干" in pillar:
            return pillar["天干"].get("天干", "")
        elif "heaven_stem" in pillar:
            return pillar["heaven_stem"].get("name", "")
        return ""

    def _extract_zhi_from_pillar(self, pillar: Dict[str, Any]) -> str:
        """
        Extract Earthly Branch from pillar.
        """
        if "地支" in pillar:
            return pillar["地支"].get("地支", "")
        elif "earth_branch" in pillar:
            return pillar["earth_branch"].get("name", "")
        return ""

    def _get_gan_element(self, gan: str) -> str:
        """
        Get Heavenly Stem Five Elements.
        """
        from .professional_data import GAN_WUXING

        return GAN_WUXING.get(gan, "")

    def _analyze_hidden_marriage_stars(
        self, pillar: Dict[str, Any], day_gan: str, target_gods: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Analyze spouse stars in Earthly Branch hidden stems.
        """
        hidden_stars = []

        if "地支" in pillar and "藏干" in pillar["地支"]:
            canggan = pillar["地支"]["藏干"]
            for gan_type, gan_info in canggan.items():
                if gan_info and "天干" in gan_info:
                    hidden_gan = gan_info["天干"]
                    ten_god = get_ten_gods_relation(day_gan, hidden_gan)
                    if ten_god in target_gods:
                        hidden_stars.append(
                            {
                                "star": ten_god,
                                "strength": self._get_hidden_strength(gan_type),
                                "element": self._get_gan_element(hidden_gan),
                                "type": f"Hidden Stem {gan_type}",
                            }
                        )

        return hidden_stars

    def _get_hidden_strength(self, gan_type: str) -> str:
        """
        Get hidden stem strength.
        """
        strength_map = {"Main Qi": "Strong", "Middle Qi": "Medium", "Residual Qi": "Weak"}
        return strength_map.get(gan_type, "Weak")

    def _evaluate_marriage_star_quality(
        self, marriage_stars: List[Dict[str, Any]]
    ) -> str:
        """
        Evaluate spouse star quality.
        """
        if not marriage_stars:
            return "No Star"

        strong_stars = sum(
            1 for star in marriage_stars if star["strength"] in ["Strongest", "Strong"]
        )
        total_stars = len(marriage_stars)

        if strong_stars >= 2:
            return "Excellent"
        elif strong_stars == 1 and total_stars >= 2:
            return "Good"
        elif total_stars >= 1:
            return "Average"
        else:
            return "Weak"


    def _evaluate_star_quality(self, position: str, ten_god: str) -> str:
        """Evaluate spouse star quality"""
        # Evaluate quality based on position and Ten Gods type
        if position == "Month Stem":
            return "Excellent"  # Month Stem spouse star is best
        elif position == "Year Stem":
            return "Good"  # Year Stem spouse star is second best
        elif position == "Hour Stem":
            return "Average"  # Hour Stem spouse star is average
        else:
            return "Acceptable"

    def _get_seasonal_strength(self, gan: str, month_gan: str) -> str:
        """Get seasonal strength"""
        from .professional_data import GAN_WUXING, WUXING_RELATIONS

        gan_element = GAN_WUXING.get(gan, "")
        month_element = GAN_WUXING.get(month_gan, "")

        if not gan_element or not month_element:
            return "Medium"

        # Check Five Elements relationship
        relation = WUXING_RELATIONS.get((month_element, gan_element), "")
        if relation == "↓":  # Month generates me
            return "Prosperous"
        elif relation == "=":  # Same element
            return "In Season"
        elif relation == "←":  # Month overcomes me
            return "Out of Season"
        elif relation == "→":  # I overcome month
            return "Draining"
        else:
            return "Medium"

    def _determine_canggan_type(self, strength: int) -> str:
        """Determine type based on hidden stem strength"""
        if strength >= 5:
            return "Main Qi"
        elif strength >= 2:
            return "Middle Qi"
        else:
            return "Residual Qi"

    def _evaluate_hidden_star_quality(self, zhi_name: str, hidden_gan: str, strength: int) -> str:
        """Evaluate hidden stem spouse star quality"""
        if strength >= 5:
            return "Excellent"
        elif strength >= 3:
            return "Good"
        elif strength >= 1:
            return "Average"
        else:
            return "Weak"

    def _comprehensive_star_analysis(self, marriage_stars: List[Dict[str, Any]], day_gan: str, gender: int) -> Dict[str, Any]:
        """Comprehensive spouse star analysis"""
        if not marriage_stars:
            return {
                "strength": "No Star",
                "quality": "No Star",
                "distribution": "No spouse star",
                "potential": "Weak",
                "suggestions": ["Can supplement spouse star through Decade Fortune and Annual Fortune", "Pay attention to timing of romantic development"]
            }

        # Analyze star distribution
        positions = [star["position"] for star in marriage_stars]
        star_types = [star["star"] for star in marriage_stars]

        # Calculate comprehensive strength
        strength_score = 0
        for star in marriage_stars:
            if star["strength"] == "Strongest":
                strength_score += 5
            elif star["strength"] == "Strong":
                strength_score += 3
            elif star["strength"] == "Medium":
                strength_score += 2
            else:
                strength_score += 1

        # Determine strength level
        if strength_score >= 8:
            strength_level = "Very Strong"
        elif strength_score >= 5:
            strength_level = "Strong"
        elif strength_score >= 3:
            strength_level = "Medium"
        else:
            strength_level = "Weak"

        # Analyze quality
        quality_scores = []
        for star in marriage_stars:
            quality = star.get("quality", "Average")
            if quality == "Excellent":
                quality_scores.append(4)
            elif quality == "Good":
                quality_scores.append(3)
            elif quality == "Average":
                quality_scores.append(2)
            else:
                quality_scores.append(1)

        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 1
        if avg_quality >= 3.5:
            quality_level = "Excellent"
        elif avg_quality >= 2.5:
            quality_level = "Good"
        elif avg_quality >= 1.5:
            quality_level = "Average"
        else:
            quality_level = "Poor"

        # Analyze distribution
        distribution_desc = f"Total {len(marriage_stars)} spouse stars, distributed across {len(set(positions))} positions"

        # Marriage potential assessment
        if strength_score >= 6 and avg_quality >= 3:
            potential = "Very Good"
        elif strength_score >= 4 and avg_quality >= 2:
            potential = "Good"
        elif strength_score >= 2:
            potential = "Average"
        else:
            potential = "Weak"

        # Improvement suggestions
        suggestions = []
        if strength_score < 3:
            suggestions.append("Spouse star is weak, can be supplemented through Decade Fortune and Annual Fortune")
        if avg_quality < 2:
            suggestions.append("Spouse star quality is not high, need patience to wait for the right timing")
        if "Month Stem" not in positions and "Month Branch" not in positions:
            suggestions.append("No spouse star in Month Pillar, romantic development may be slower")
        if len(set(star_types)) == 1:
            suggestions.append("Single type of spouse star, romantic pattern is relatively fixed")

        return {
            "strength": strength_level,
            "quality": quality_level,
            "distribution": distribution_desc,
            "potential": potential,
            "suggestions": suggestions if suggestions else ["Spouse star configuration is good, romantic development is smooth"]
        }


# Global analyzer instance
_marriage_analyzer = None


def get_marriage_analyzer():
    """
    Get marriage analyzer singleton.
    """
    global _marriage_analyzer
    if _marriage_analyzer is None:
        _marriage_analyzer = MarriageAnalyzer()
    return _marriage_analyzer
