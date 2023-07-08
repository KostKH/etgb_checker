import datetime as dt
from dataclasses import dataclass


@dataclass
class Queries():
    """Модель запроса"""
    id: str
    status_code: int = 1001
    status_text: str = 'PROCESSING'
    ozone_response_code: int = 0
    etgb_found_total: int = 0
    etgb_saved_new: int = 0


@dataclass(frozen=True)
class Results():
    """Модель полученных от Озона данных."""
    posting_number: str
    etgb_number: str
    etgb_date: dt.date
    etgb_url: str
