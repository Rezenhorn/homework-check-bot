class NoMessageToTelegram(Exception):
    """Класс для исключения отправки сообщения в телеграм."""

    pass


class TelegramMessageError(NoMessageToTelegram):
    """Ошибка при отправке сообщения в телеграм."""

    pass


class JSONError(Exception):
    """Ошибка при декодировании сообщения JSON."""

    pass


class RequestAPIError(Exception):
    """Ошибка при запросе к API."""

    pass


class CurrentDateError(NoMessageToTelegram):
    """Ошибка при отсутствии current_date в ответе API."""

    pass
