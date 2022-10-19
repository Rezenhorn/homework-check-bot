import logging
import os
import time
from sys import exit, stdout

from dotenv import load_dotenv
from http import HTTPStatus
from json.decoder import JSONDecodeError
import requests
from telegram import Bot, TelegramError

from exceptions import (
    CurrentDateError, JSONError, NoMessageToTelegram, RequestAPIError,
    TelegramMessageError
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

TOKENS = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
}

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] func %(funcName)s(%(lineno)d): %(message)s'
)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stdout)
handler.setFormatter(formatter)
logger.addHandler(handler)


def send_message(bot: Bot, message: str):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except TelegramError as error:
        raise TelegramMessageError(f'Ошибка при отправке сообщения: {error}')
    else:
        logger.info('Сообщение успешно отправлено в телеграм')


def get_api_answer(current_timestamp: int) -> dict:
    """Возвращает ответ API, преобразованный к типам данных Python."""
    arguments = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': current_timestamp},
    }
    try:
        homework_statuses = requests.get(**arguments)
        if homework_statuses.status_code != HTTPStatus.OK:
            message = (f'Эндпоинт {ENDPOINT} недоступен.'
                       f'Код ответа: {homework_statuses.status_code}')
            raise requests.HTTPError(message)
        return homework_statuses.json()
    except requests.exceptions.RequestException as error:
        raise RequestAPIError(f'Ошибка при запросе к основному API: {error}')
    except JSONDecodeError as error:
        raise JSONError(f'Ошибка при декодировании JSON: {error}')


def check_response(response: dict) -> list:
    """Проверяет ответ API на корректность.
    Если ответ API соответствует ожиданиям,
    то функция возвращает список домашних работ.
    """
    if not isinstance(response, dict):
        raise TypeError(f'Ответ API возвращает {type(response)} вместо dict')
    if response.get('current_date') is None:
        raise CurrentDateError('В ответе API отсутствует ключ current_date')
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError('В ответе API отсутствует ключ homework')
    if not isinstance(homeworks, list):
        raise TypeError(
            f'В ответе API homework является {type(homeworks)} вместо list'
        )
    return homeworks


def parse_status(homework: dict) -> str:
    """Извлекает статус конкретной домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise KeyError('В ответе API отсутствует ключ homework_name')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError(f'Статус {homework_status} не найден')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    return PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        for token_name, token_value in TOKENS.items():
            if not token_value:
                logger.critical(
                    f'Отсутствует переменная окружения {token_name}'
                )
        exit('Отсутствуют необходимые переменные окружения')
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    last_error = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date', int(time.time()))
            homeworks = check_response(response)
            if len(homeworks) > 0:
                send_message(bot, parse_status(homeworks[0]))
        except NoMessageToTelegram as error:
            logger.error(f'Сбой в работе программы: {error}', exc_info=True)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            if last_error != error:
                send_message(bot, message)
                last_error = error
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
