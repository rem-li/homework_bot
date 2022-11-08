import logging
import os
import time
import json
from logging.handlers import RotatingFileHandler
import requests
from telegram import Bot

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s- %(lineno)d - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    filename='main.log',
    filemode='w'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    backupCount=5
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(message)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.info('message was sent')
    except Exception as error:
        logger.error('message sending was failed:', error)


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            logger.error('API HTTPStatus not 200')
            raise Exception('Ошибка при запросе к апи')
    except json.JSONDecodeError:
        logger.error('not a valid JSON document')
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        logger.error('bad responce from api')
        raise TypeError('Пришел не словарь')
    if 'homeworks' not in response:
        logger.error('key "homeworks" is not in response')
        raise KeyError('В словаре нет ключа с домашками')
    homework = response['homeworks']
    if not isinstance(homework, list):
        logger.error('api responce is not list')
        raise Exception(
            'под ключом `homeworks` домашки приходят не в виде списка'
        )
    return homework


def parse_status(homework):
    """Извлекает статус домашки."""
    if len(homework) == 0:
        logger.error('no homework to check')
        return 'Нет домашки для проверки'
    if 'homework_name' not in homework:
        logger.error('homework name is incorrect')
        raise KeyError('Неправильное название дз')
    homework_name = homework['homework_name']
    if homework['status'] not in HOMEWORK_STATUSES:
        logger.error('homework status is incorrect')
        raise Exception('Неправильный статус дз')
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('tokens is missing')
    else:
        bot = Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
        last_status = ''
        while True:
            try:
                response = get_api_answer(current_timestamp)
                check = check_response(response)
                status = parse_status(check)
                if last_status != status:
                    last_status = status
                    send_message(bot, last_status)
                    time.sleep(RETRY_TIME)
                else:
                    logger.debug('no new status')
            except Exception as error:
                message = f'Ошибка: {error}'
                send_message(bot, message)
                time.sleep(RETRY_TIME)
            else:
                time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
