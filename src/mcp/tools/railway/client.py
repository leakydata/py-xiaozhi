"""12306 API client.

Provides access to the 12306 official API.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode

import aiohttp
from dateutil import tz

from src.utils.logging_config import get_logger

from .models import SeatPrice, StationInfo, TrainTicket, TransferTicket

logger = get_logger(__name__)


class Railway12306Client:
    """
    12306 client.
    """

    def __init__(self):
        self.api_base = "https://kyfw.12306.cn"
        self.web_url = "https://www.12306.cn/index/"
        self.lcquery_init_url = "https://kyfw.12306.cn/otn/lcQuery/init"

        # Station data cache
        self._stations: Dict[str, StationInfo] = {}  # code -> StationInfo
        self._city_stations: Dict[str, List[StationInfo]] = (
            {}
        )  # city -> List[StationInfo]
        self._city_codes: Dict[str, StationInfo] = {}  # city -> StationInfo
        self._name_stations: Dict[str, StationInfo] = {}  # name -> StationInfo
        self._lcquery_path: Optional[str] = None

        # Seat type mapping
        self.seat_types = {
            "9": {"name": "Business Class", "short": "swz"},
            "P": {"name": "Premier Class", "short": "tz"},
            "M": {"name": "First Class", "short": "zy"},
            "D": {"name": "Premium First Class", "short": "zy"},
            "O": {"name": "Second Class", "short": "ze"},
            "S": {"name": "Second Class Compartment", "short": "ze"},
            "6": {"name": "Deluxe Soft Sleeper", "short": "gr"},
            "A": {"name": "Deluxe EMU Sleeper", "short": "gr"},
            "4": {"name": "Soft Sleeper", "short": "rw"},
            "I": {"name": "First Class Sleeper", "short": "rw"},
            "F": {"name": "EMU Sleeper", "short": "rw"},
            "3": {"name": "Hard Sleeper", "short": "yw"},
            "J": {"name": "Second Class Sleeper", "short": "yw"},
            "2": {"name": "Soft Seat", "short": "rz"},
            "1": {"name": "Hard Seat", "short": "yz"},
            "W": {"name": "Standing", "short": "wz"},
            "WZ": {"name": "Standing", "short": "wz"},
            "H": {"name": "Other", "short": "qt"},
        }

        # Train type filters
        self.train_filters = {
            "G": lambda code: code.startswith("G") or code.startswith("C"),
            "D": lambda code: code.startswith("D"),
            "Z": lambda code: code.startswith("Z"),
            "T": lambda code: code.startswith("T"),
            "K": lambda code: code.startswith("K"),
            "O": lambda code: not any(
                [
                    code.startswith("G"),
                    code.startswith("C"),
                    code.startswith("D"),
                    code.startswith("Z"),
                    code.startswith("T"),
                    code.startswith("K"),
                ]
            ),
        }

        # Feature flags
        self.dw_flags = [
            "Smart EMU",
            "Fuxing",
            "Quiet Car",
            "Comfort Sleeper",
            "Vibrant Express",
            "Berth Selection",
            "Senior Discount",
        ]

    async def initialize(self) -> bool:
        """
        Initialize client and load station data.
        """
        try:
            logger.info("Starting 12306 client initialization...")

            # Load station data
            await self._load_stations()

            # Get transfer query path
            await self._get_lcquery_path()

            logger.info("Initialization complete")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            return False

    async def _load_stations(self):
        """
        Load station data.
        """
        try:
            # Get station JS file
            async with aiohttp.ClientSession() as session:
                async with session.get(self.web_url) as response:
                    html = await response.text()

                # Find station JS file path
                match = re.search(r"\.(.*station_name.*?\.js)", html)
                if not match:
                    raise Exception("Station data file not found")

                js_path = match.group(0)
                js_url = f"{self.web_url.rstrip('/')}/{js_path.lstrip('.')}"

                # Get station data
                async with session.get(js_url) as response:
                    js_content = await response.text()

                # Parse station data
                station_data = (
                    js_content.replace("var station_names =", "").strip().rstrip(";")
                )
                station_data = station_data.strip("\"'")

                self._parse_stations_data(station_data)

        except Exception as e:
            logger.error(f"Failed to load station data: {e}")
            # Use default station data
            self._load_default_stations()

    def _parse_stations_data(self, raw_data: str):
        """
        Parse station data.
        """
        try:
            data_array = raw_data.split("|")

            # Every 10 elements form one station
            for i in range(0, len(data_array), 10):
                if i + 9 >= len(data_array):
                    break

                group = data_array[i : i + 10]
                if len(group) < 10 or not group[2]:  # station_code不能为空
                    continue

                station = StationInfo(
                    station_id=group[0],
                    station_name=group[1],
                    station_code=group[2],
                    station_pinyin=group[3],
                    station_short=group[4],
                    city=group[7],
                    code=group[6],
                )

                # Index by code
                self._stations[station.station_code] = station

                # Index by city
                if station.city not in self._city_stations:
                    self._city_stations[station.city] = []
                self._city_stations[station.city].append(station)

                # Index by name
                self._name_stations[station.station_name] = station

            # Generate representative station codes for cities (station with same name as city)
            for city, stations in self._city_stations.items():
                for station in stations:
                    if station.station_name == city:
                        self._city_codes[city] = station
                        break

            # Add missing stations
            self._add_missing_stations()

            logger.info(f"Loaded {len(self._stations)} stations")

        except Exception as e:
            logger.error(f"Failed to parse station data: {e}")
            raise

    def _add_missing_stations(self):
        """
        Add missing stations.
        """
        missing_stations = [
            StationInfo(
                station_id="@cdd",
                station_name="成都东",
                station_code="WEI",
                station_pinyin="chengdudong",
                station_short="cdd",
                city="成都",
                code="1707",
            ),
            StationInfo(
                station_id="@szb",
                station_name="深圳北",
                station_code="IOQ",
                station_pinyin="shenzhenbei",
                station_short="szb",
                city="深圳",
                code="1708",
            ),
        ]

        for station in missing_stations:
            if station.station_code not in self._stations:
                self._stations[station.station_code] = station

                if station.city not in self._city_stations:
                    self._city_stations[station.city] = []
                self._city_stations[station.city].append(station)

                self._name_stations[station.station_name] = station

    def _load_default_stations(self):
        """
        Load default station data (fallback).
        """
        default_stations = [
            {
                "station_id": "@bjb",
                "station_name": "北京",
                "station_code": "BJP",
                "station_pinyin": "beijing",
                "station_short": "bjb",
                "city": "北京",
                "code": "0001",
            },
            {
                "station_id": "@shh",
                "station_name": "上海",
                "station_code": "SHH",
                "station_pinyin": "shanghai",
                "station_short": "shh",
                "city": "上海",
                "code": "0002",
            },
        ]

        for data in default_stations:
            station = StationInfo(**data)
            self._stations[station.station_code] = station

            if station.city not in self._city_stations:
                self._city_stations[station.city] = []
            self._city_stations[station.city].append(station)

            self._name_stations[station.station_name] = station
            self._city_codes[station.city] = station

    async def _get_lcquery_path(self):
        """
        Get transfer query path.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.lcquery_init_url) as response:
                    html = await response.text()

                match = re.search(r"var lc_search_url = '(.+?)'", html)
                if match:
                    self._lcquery_path = match.group(1)
                    logger.debug(f"Got transfer query path: {self._lcquery_path}")
                else:
                    logger.warning("Transfer query path not found")

        except Exception as e:
            logger.error(f"Failed to get transfer query path: {e}")

    async def _get_cookie(self) -> Optional[str]:
        """
        Get cookie.
        """
        try:
            url = f"{self.api_base}/otn/"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    cookies = response.cookies
                    if cookies:
                        cookie_str = "; ".join(
                            [f"{k}={v.value}" for k, v in cookies.items()]
                        )
                        return cookie_str
            return None

        except Exception as e:
            logger.error(f"Failed to get cookie: {e}")
            return None

    async def _make_request(self, url: str, params: dict = None) -> Optional[dict]:
        """
        Make a request.
        """
        try:
            cookie = await self._get_cookie()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "X-Requested-With": "XMLHttpRequest",
            }
            if cookie:
                headers["Cookie"] = cookie

            async with aiohttp.ClientSession() as session:
                if params:
                    url = f"{url}?{urlencode(params)}"

                async with session.get(url, headers=headers) as response:
                    # Check if it's an error page
                    if response.content_type == "text/html":
                        text = await response.text()
                        if "error.html" in response.url.path or "error" in text.lower():
                            logger.error(f"12306 returned error page: {response.url}")
                            return None

                    return await response.json()

        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    def get_current_date(self) -> str:
        """
        Get current date (Shanghai timezone).
        """
        shanghai_tz = tz.gettz("Asia/Shanghai")
        now = datetime.now(shanghai_tz)
        return now.strftime("%Y-%m-%d")

    def get_stations_in_city(self, city: str) -> List[StationInfo]:
        """
        Get all stations in a city.
        """
        return self._city_stations.get(city, [])

    def get_city_main_station(self, city: str) -> Optional[StationInfo]:
        """
        Get the main station of a city.
        """
        return self._city_codes.get(city)

    def get_station_by_name(self, name: str) -> Optional[StationInfo]:
        “””
        Get station by name.
        “””
        # Remove trailing suffix “站” (station)
        if name.endswith("站"):
            name = name[:-1]
        return self._name_stations.get(name)

    def get_station_by_code(self, code: str) -> Optional[StationInfo]:
        """
        Get station by code.
        """
        return self._stations.get(code)

    def _check_date(self, date_str: str) -> bool:
        """
        Check if date is valid (cannot be earlier than today).
        """
        try:
            shanghai_tz = tz.gettz("Asia/Shanghai")
            now = datetime.now(shanghai_tz).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            target_date = datetime.fromisoformat(date_str).replace(tzinfo=shanghai_tz)
            target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)

            return target_date >= now

        except Exception:
            return False

    async def query_transfer_tickets(
        self,
        date: str,
        from_station: str,
        to_station: str,
        middle_station: str = "",
        show_wz: bool = False,
        train_filters: str = "",
        sort_by: str = "",
        reverse: bool = False,
        limit: int = 10,
    ) -> Tuple[bool, List[TransferTicket], str]:
        """Query transfer tickets.

        Args:
            date: Query date (YYYY-MM-DD)
            from_station: Departure station code
            to_station: Arrival station code
            middle_station: Transfer station code (optional)
            show_wz: Whether to show standing-only trains
            train_filters: Train type filter (G/D/Z/T/K/O/F/S)
            sort_by: Sort method (start_time/arrive_time/duration)
            reverse: Whether to reverse sort order
            limit: Result limit

        Returns:
            (success, transfer_tickets, message)
        """
        try:
            # Check date
            if not self._check_date(date):
                return False, [], "Date cannot be earlier than today"

            # Check stations
            if from_station not in self._stations or to_station not in self._stations:
                return False, [], "Station code does not exist"

            if middle_station and middle_station not in self._stations:
                return False, [], "Transfer station code does not exist"

            # Get transfer query path
            if not self._lcquery_path:
                await self._get_lcquery_path()
                if not self._lcquery_path:
                    return False, [], "Transfer query path unavailable"

            # Build request parameters
            params = {
                "train_date": date,
                "from_station_telecode": from_station,
                "to_station_telecode": to_station,
                "middle_station": middle_station,
                "result_index": "0",
                "can_query": "Y",
                "isShowWZ": "Y" if show_wz else "N",
                "purpose_codes": "00",  # Adult ticket
                "channel": "E",
            }

            url = f"{self.api_base}{self._lcquery_path}"
            transfers = []

            # Loop query until enough data is obtained or no more data
            while len(transfers) < limit:
                data = await self._make_request(url, params)

                if not data:
                    return False, [], "Transfer ticket query API unavailable"

                # Check query result
                if isinstance(data.get("data"), str):
                    # Query failed
                    error_msg = data.get("errorMsg", "No related train tickets found")
                    return False, [], f"No transfer tickets found: {error_msg}"

                # Parse transfer data
                data_dict = data.get("data", {})
                middle_list = data_dict.get("middleList", [])

                if not middle_list:
                    break

                # Parse and add transfer ticket information
                parsed_transfers = self._parse_transfer_data(middle_list)
                transfers.extend(parsed_transfers)

                # Check if more queries are possible
                if data_dict.get("can_query") != "Y":
                    break

                # Update query index
                params["result_index"] = str(data_dict.get("result_index", 0))

            # Filter and sort
            transfers = self._filter_and_sort_transfers(
                transfers, train_filters, sort_by, reverse, limit
            )

            return True, transfers, "Query successful"

        except Exception as e:
            logger.error(f"Failed to query transfer tickets: {e}", exc_info=True)
            return False, [], f"Query failed: {str(e)}"

    async def query_tickets(
        self,
        date: str,
        from_station: str,
        to_station: str,
        train_filters: str = "",
        sort_by: str = "",
        reverse: bool = False,
        limit: int = 0,
    ) -> Tuple[bool, List[TrainTicket], str]:
        """Query tickets.

        Args:
            date: Query date (YYYY-MM-DD)
            from_station: Departure station code
            to_station: Arrival station code
            train_filters: Train type filter (G/D/Z/T/K/O)
            sort_by: Sort method (start_time/arrive_time/duration)
            reverse: Whether to reverse sort order
            limit: Result limit

        Returns:
            (success, tickets, message)
        """
        try:
            # Check date
            if not self._check_date(date):
                return False, [], "Date cannot be earlier than today"

            # Check stations
            if from_station not in self._stations or to_station not in self._stations:
                return False, [], "Station code does not exist"

            # Build request parameters
            params = {
                "leftTicketDTO.train_date": date,
                "leftTicketDTO.from_station": from_station,
                "leftTicketDTO.to_station": to_station,
                "purpose_codes": "ADULT",
            }

            url = f"{self.api_base}/otn/leftTicket/query"
            data = await self._make_request(url, params)

            if not data or not data.get("status"):
                # When 12306 API is unavailable, return error message
                logger.warning("12306 API unavailable")
                return False, [], "12306 service unavailable, please try again later"

            # Parse data
            tickets = self._parse_tickets_data(data.get("data", {}))

            # Filter and sort
            tickets = self._filter_and_sort_tickets(
                tickets, train_filters, sort_by, reverse, limit
            )

            return True, tickets, "Query successful"

        except Exception as e:
            logger.error(f"Failed to query tickets: {e}", exc_info=True)
            return False, [], f"Query failed: {str(e)}"

    def _parse_tickets_data(self, data: dict) -> List[TrainTicket]:
        """
        Parse ticket data.
        """
        tickets = []

        try:
            results = data.get("result", [])
            station_map = data.get("map", {})

            for result_str in results:
                values = result_str.split("|")
                if len(values) < 57:  # Incomplete data
                    continue

                # Parse basic information
                train_no = values[2]
                train_code = values[3]
                start_time = values[8]
                arrive_time = values[9]
                duration = values[10]
                from_code = values[6]
                to_code = values[7]
                start_date_str = values[13]

                # Calculate date
                start_date = datetime.strptime(start_date_str, "%Y%m%d")

                # Safely parse time, handle possible format issues
                try:
                    start_hour, start_minute = map(int, start_time.split(":"))
                    if (
                        start_hour < 0
                        or start_hour > 23
                        or start_minute < 0
                        or start_minute > 59
                    ):
                        logger.warning(f"Invalid start time: {start_time}")
                        continue

                    duration_hour, duration_minute = map(int, duration.split(":"))
                    if duration_hour < 0 or duration_minute < 0:
                        logger.warning(f"Invalid duration: {duration}")
                        continue

                    start_datetime = start_date.replace(
                        hour=start_hour, minute=start_minute
                    )
                    arrive_datetime = start_datetime + timedelta(
                        hours=duration_hour, minutes=duration_minute
                    )

                except (ValueError, IndexError) as e:
                    logger.warning(
                        f"Time parsing failed start_time={start_time}, duration={duration}: {e}"
                    )
                    continue

                # Parse price information
                prices = self._parse_prices(values[42], values[54], values)

                # Parse feature flags
                features = self._parse_features(values[46])

                ticket = TrainTicket(
                    train_no=train_no,
                    start_train_code=train_code,
                    start_date=start_datetime.strftime("%Y-%m-%d"),
                    start_time=start_time,
                    arrive_date=arrive_datetime.strftime("%Y-%m-%d"),
                    arrive_time=arrive_time,
                    duration=duration,
                    from_station=station_map.get(from_code, from_code),
                    to_station=station_map.get(to_code, to_code),
                    from_station_code=from_code,
                    to_station_code=to_code,
                    prices=prices,
                    features=features,
                )

                tickets.append(ticket)

        except Exception as e:
            logger.error(f"Failed to parse ticket data: {e}")

        return tickets

    def _parse_prices(
        self, yp_info: str, discount_info: str, values: list
    ) -> List[SeatPrice]:
        """
        Parse price information.
        """
        prices = []

        try:
            # Parse discount information
            discounts = {}
            for i in range(0, len(discount_info), 5):
                if i + 4 < len(discount_info):
                    seat_code = discount_info[i]
                    discount_val = int(discount_info[i + 1 : i + 5])
                    discounts[seat_code] = discount_val

            # Parse price information
            for i in range(0, len(yp_info), 10):
                if i + 9 < len(yp_info):
                    price_str = yp_info[i : i + 10]
                    seat_code = price_str[0]

                    # Special handling for standing tickets
                    if int(price_str[6:10]) >= 3000:
                        seat_code = "W"
                    elif seat_code not in self.seat_types:
                        seat_code = "H"

                    seat_info = self.seat_types.get(
                        seat_code, {"name": "Other", "short": "qt"}
                    )
                    price_value = int(price_str[1:6]) / 10

                    # Get remaining ticket count
                    seat_num_field = f"{seat_info['short']}_num"
                    seat_num_index = self._get_seat_num_index(seat_num_field)
                    num = (
                        values[seat_num_index] if seat_num_index < len(values) else "--"
                    )

                    price = SeatPrice(
                        seat_name=seat_info["name"],
                        short=seat_info["short"],
                        seat_type_code=seat_code,
                        num=num,
                        price=price_value,
                        discount=discounts.get(seat_code),
                    )

                    prices.append(price)

        except Exception as e:
            logger.error(f"Failed to parse price information: {e}")

        return prices

    def _get_seat_num_index(self, seat_field: str) -> int:
        """
        Get the index of the seat count field.
        """
        seat_indices = {
            "gg_num": 22,
            "gr_num": 23,
            "qt_num": 24,
            "rw_num": 25,
            "rz_num": 26,
            "tz_num": 27,
            "wz_num": 28,
            "yb_num": 29,
            "yw_num": 30,
            "yz_num": 31,
            "ze_num": 32,
            "zy_num": 33,
            "swz_num": 34,
            "srrb_num": 35,
        }
        return seat_indices.get(seat_field, 24)

    def _parse_features(self, dw_flag: str) -> List[str]:
        """
        Parse feature flags.
        """
        features = []

        try:
            flags = dw_flag.split("#")

            if len(flags) > 0 and flags[0] == "5":
                features.append(self.dw_flags[0])  # Smart EMU

            if len(flags) > 1 and flags[1] == "1":
                features.append(self.dw_flags[1])  # Fuxing

            if len(flags) > 2:
                if flags[2].startswith("Q"):
                    features.append(self.dw_flags[2])  # Quiet Car
                elif flags[2].startswith("R"):
                    features.append(self.dw_flags[3])  # Comfort Sleeper

            if len(flags) > 5 and flags[5] == "D":
                features.append(self.dw_flags[4])  # Vibrant Express

            if len(flags) > 6 and flags[6] != "z":
                features.append(self.dw_flags[5])  # Berth Selection

            if len(flags) > 7 and flags[7] != "z":
                features.append(self.dw_flags[6])  # Senior Discount

        except Exception as e:
            logger.error(f"Failed to parse feature flags: {e}")

        return features

    def _filter_and_sort_tickets(
        self,
        tickets: List[TrainTicket],
        train_filters: str,
        sort_by: str,
        reverse: bool,
        limit: int,
    ) -> List[TrainTicket]:
        """
        Filter and sort tickets.
        """
        result = tickets

        # Filter train types
        if train_filters:
            filtered = []
            for ticket in result:
                for filter_char in train_filters:
                    if filter_char in self.train_filters:
                        if self.train_filters[filter_char](ticket.start_train_code):
                            filtered.append(ticket)
                            break
            result = filtered

        # Sort
        if sort_by == "start_time":
            result.sort(key=lambda t: (t.start_date, t.start_time))
        elif sort_by == "arrive_time":
            result.sort(key=lambda t: (t.arrive_date, t.arrive_time))
        elif sort_by == "duration":
            result.sort(key=lambda t: t.duration)

        if reverse:
            result.reverse()

        # Limit count
        if limit > 0:
            result = result[:limit]

        return result

    def _parse_transfer_data(self, middle_list: List[dict]) -> List[TransferTicket]:
        """
        Parse transfer data.
        """
        transfers = []

        try:
            for transfer_data in middle_list:
                # Parse basic information
                duration = self._extract_duration(transfer_data.get("all_lishi", ""))
                start_time = transfer_data.get("start_time", "")
                start_date = transfer_data.get("train_date", "")
                middle_date = transfer_data.get("middle_date", "")
                arrive_date = transfer_data.get("arrive_date", "")
                arrive_time = transfer_data.get("arrive_time", "")

                from_station_code = transfer_data.get("from_station_code", "")
                from_station_name = transfer_data.get("from_station_name", "")
                middle_station_code = transfer_data.get("middle_station_code", "")
                middle_station_name = transfer_data.get("middle_station_name", "")
                end_station_code = transfer_data.get("end_station_code", "")
                end_station_name = transfer_data.get("end_station_name", "")

                first_train_no = transfer_data.get("first_train_no", "")
                second_train_no = transfer_data.get("second_train_no", "")
                train_count = int(transfer_data.get("train_count", 2))

                same_station = transfer_data.get("same_station") == "0"
                same_train = transfer_data.get("same_train") == "Y"
                wait_time = transfer_data.get("wait_time", "")

                # Parse ticket list
                full_list = transfer_data.get("fullList", [])
                ticket_list = self._parse_transfer_tickets(full_list)

                # Get first train code
                start_train_code = (
                    ticket_list[0].start_train_code if ticket_list else ""
                )

                transfer = TransferTicket(
                    duration=duration,
                    start_time=start_time,
                    start_date=start_date,
                    middle_date=middle_date,
                    arrive_date=arrive_date,
                    arrive_time=arrive_time,
                    from_station_code=from_station_code,
                    from_station_name=from_station_name,
                    middle_station_code=middle_station_code,
                    middle_station_name=middle_station_name,
                    end_station_code=end_station_code,
                    end_station_name=end_station_name,
                    start_train_code=start_train_code,
                    first_train_no=first_train_no,
                    second_train_no=second_train_no,
                    train_count=train_count,
                    ticket_list=ticket_list,
                    same_station=same_station,
                    same_train=same_train,
                    wait_time=wait_time,
                )

                transfers.append(transfer)

        except Exception as e:
            logger.error(f"Failed to parse transfer data: {e}")

        return transfers

    def _parse_transfer_tickets(self, full_list: List[dict]) -> List[TrainTicket]:
        """
        Parse transfer ticket list.
        """
        tickets = []

        try:
            for ticket_data in full_list:
                # Parse basic information
                train_no = ticket_data.get("train_no", "")
                train_code = ticket_data.get("station_train_code", "")
                start_time = ticket_data.get("start_time", "")
                arrive_time = ticket_data.get("arrive_time", "")
                duration = ticket_data.get("lishi", "")
                start_date_str = ticket_data.get("start_train_date", "")

                from_station_name = ticket_data.get("from_station_name", "")
                to_station_name = ticket_data.get("to_station_name", "")
                from_station_code = ticket_data.get("from_station_telecode", "")
                to_station_code = ticket_data.get("to_station_telecode", "")

                # Calculate date
                try:
                    start_date = datetime.strptime(start_date_str, "%Y%m%d")
                    start_hour, start_minute = map(int, start_time.split(":"))
                    duration_hour, duration_minute = map(int, duration.split(":"))

                    start_datetime = start_date.replace(
                        hour=start_hour, minute=start_minute
                    )
                    arrive_datetime = start_datetime + timedelta(
                        hours=duration_hour, minutes=duration_minute
                    )

                    formatted_start_date = start_datetime.strftime("%Y-%m-%d")
                    formatted_arrive_date = arrive_datetime.strftime("%Y-%m-%d")

                except (ValueError, IndexError) as e:
                    logger.warning(f"Transfer ticket time parsing failed: {e}")
                    formatted_start_date = start_date_str
                    formatted_arrive_date = start_date_str

                # Parse price information
                yp_info = ticket_data.get("yp_info", "")
                discount_info = ticket_data.get("seat_discount_info", "")
                prices = self._parse_transfer_prices(
                    yp_info, discount_info, ticket_data
                )

                # Parse feature flags
                features = self._parse_features(ticket_data.get("dw_flag", ""))

                ticket = TrainTicket(
                    train_no=train_no,
                    start_train_code=train_code,
                    start_date=formatted_start_date,
                    start_time=start_time,
                    arrive_date=formatted_arrive_date,
                    arrive_time=arrive_time,
                    duration=duration,
                    from_station=from_station_name,
                    to_station=to_station_name,
                    from_station_code=from_station_code,
                    to_station_code=to_station_code,
                    prices=prices,
                    features=features,
                )

                tickets.append(ticket)

        except Exception as e:
            logger.error(f"Failed to parse transfer tickets: {e}")

        return tickets

    def _parse_transfer_prices(
        self, yp_info: str, discount_info: str, ticket_data: dict
    ) -> List[SeatPrice]:
        """
        Parse transfer ticket price information.
        """
        prices = []

        try:
            # Parse discount information
            discounts = {}
            for i in range(0, len(discount_info), 5):
                if i + 4 < len(discount_info):
                    seat_code = discount_info[i]
                    discount_val = int(discount_info[i + 1 : i + 5])
                    discounts[seat_code] = discount_val

            # Parse price information
            for i in range(0, len(yp_info), 10):
                if i + 9 < len(yp_info):
                    price_str = yp_info[i : i + 10]
                    seat_code = price_str[0]

                    # Special handling for standing tickets
                    if int(price_str[6:10]) >= 3000:
                        seat_code = "W"
                    elif seat_code not in self.seat_types:
                        seat_code = "H"

                    seat_info = self.seat_types.get(
                        seat_code, {"name": "Other", "short": "qt"}
                    )
                    price_value = int(price_str[1:6]) / 10

                    # Get remaining ticket count from ticket_data
                    seat_short = seat_info["short"]
                    num_field = f"{seat_short}_num"
                    num = ticket_data.get(num_field, "--")

                    price = SeatPrice(
                        seat_name=seat_info["name"],
                        short=seat_info["short"],
                        seat_type_code=seat_code,
                        num=num,
                        price=price_value,
                        discount=discounts.get(seat_code),
                    )

                    prices.append(price)

        except Exception as e:
            logger.error(f"Failed to parse transfer price information: {e}")

        return prices

    def _extract_duration(self, all_lishi: str) -> str:
        """
        Extract duration information, formatted as HH:MM.
        """
        try:
            # Match "X小时Y分钟" or "Y分钟" format
            import re

            match = re.search(r"(?:(\d+)小时)?(\d+)分钟", all_lishi)
            if match:
                hours = int(match.group(1)) if match.group(1) else 0
                minutes = int(match.group(2))
                return f"{hours:02d}:{minutes:02d}"
            return all_lishi

        except Exception as e:
            logger.error(f"Failed to parse duration: {e}")
            return all_lishi

    def _filter_and_sort_transfers(
        self,
        transfers: List[TransferTicket],
        train_filters: str,
        sort_by: str,
        reverse: bool,
        limit: int,
    ) -> List[TransferTicket]:
        """
        Filter and sort transfer tickets.
        """
        result = transfers

        # Filter train types
        if train_filters:
            filtered = []
            for transfer in result:
                for filter_char in train_filters:
                    if filter_char in self.train_filters:
                        # Check if any train matches filter criteria
                        if any(
                            self.train_filters[filter_char](ticket.start_train_code)
                            for ticket in transfer.ticket_list
                        ):
                            filtered.append(transfer)
                            break
                    elif filter_char == "F":  # Fuxing
                        if any(
                            "Fuxing" in ticket.features
                            for ticket in transfer.ticket_list
                        ):
                            filtered.append(transfer)
                            break
                    elif filter_char == "S":  # Smart EMU
                        if any(
                            "Smart EMU" in ticket.features
                            for ticket in transfer.ticket_list
                        ):
                            filtered.append(transfer)
                            break
            result = filtered

        # Sort
        if sort_by == "start_time":
            result.sort(key=lambda t: (t.start_date, t.start_time))
        elif sort_by == "arrive_time":
            result.sort(key=lambda t: (t.arrive_date, t.arrive_time))
        elif sort_by == "duration":
            result.sort(key=lambda t: t.duration)

        if reverse:
            result.reverse()

        # Limit count
        if limit > 0:
            result = result[:limit]

        return result


# Global client instance
_client = None


async def get_railway_client() -> Railway12306Client:
    """
    Get railway client singleton.
    """
    global _client
    if _client is None:
        _client = Railway12306Client()
        await _client.initialize()
    return _client
