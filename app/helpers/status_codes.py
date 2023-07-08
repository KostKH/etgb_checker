import enum


class StatusCode(enum.Enum):
    """Класс со стандартными кодами ответов, которые возвращаются
    данным API."""

    PROCESSING = 2001
    DONE = 2002
    OZON_URL_IS_NOT_REACHED = 4001
    OZON_ERROR_STATUS_CODE = 4002
    OZON_NO_JSON = 4003
    RES_PARSE_ERROR = 4004
    SAVE_TO_DB_ERROR = 4005
    OTHER_ERROR = 4006

    def __str__(self):
        return str(self.name)
