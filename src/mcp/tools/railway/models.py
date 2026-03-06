"""
12306 data model definitions.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class StationInfo:
    """
    Station information.
    """

    station_id: str
    station_name: str
    station_code: str  # 3-letter code
    station_pinyin: str
    station_short: str
    city: str
    code: str


@dataclass
class SeatPrice:
    """
    Seat price information.
    """

    seat_name: str  # Seat name
    short: str  # Short name
    seat_type_code: str  # Seat type code
    num: str  # Remaining ticket count
    price: float  # Price
    discount: Optional[float] = None  # Discount


@dataclass
class TrainTicket:
    """
    Train ticket information.
    """

    train_no: str  # Train number
    start_train_code: str  # Train code
    start_date: str  # Departure date
    start_time: str  # Departure time
    arrive_date: str  # Arrival date
    arrive_time: str  # Arrival time
    duration: str  # Duration
    from_station: str  # Departure station
    to_station: str  # Arrival station
    from_station_code: str  # Departure station code
    to_station_code: str  # Arrival station code
    prices: List[SeatPrice]  # Seat price list
    features: List[str]  # Feature flags (Fuxing, Smart EMU, etc.)


@dataclass
class TransferTicket:
    """
    Transfer ticket information.
    """

    duration: str  # Total duration
    start_time: str  # Departure time
    start_date: str  # Departure date
    middle_date: str  # Transfer date
    arrive_date: str  # Arrival date
    arrive_time: str  # Arrival time
    from_station_code: str  # Departure station code
    from_station_name: str  # Departure station name
    middle_station_code: str  # Transfer station code
    middle_station_name: str  # Transfer station name
    end_station_code: str  # Arrival station code
    end_station_name: str  # Arrival station name
    start_train_code: str  # First train code
    first_train_no: str  # First leg train number
    second_train_no: str  # Second leg train number
    train_count: int  # Number of trains
    ticket_list: List[TrainTicket]  # Ticket list
    same_station: bool  # Whether transferring at the same station
    same_train: bool  # Whether transferring on the same train
    wait_time: str  # Waiting time


@dataclass
class RouteStation:
    """
    Route station information.
    """

    arrive_time: str  # Arrival time
    station_name: str  # Station name
    stopover_time: str  # Stop duration
    station_no: int  # Station sequence number
