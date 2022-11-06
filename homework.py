import logging
import os
import time
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

PRACTICUM_TOKEN = os.getenv('praktikum_token')
TELEGRAM_TOKEN = os.getenv('bot_token')
TELEGRAM_CHAT_ID = os.getenv('chat_id')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат"""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
        )
        logger.info('message sent')
    except Exception as error:
        logger.error('send message fails:', error)


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API-сервиса"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        logger.error('API HTTPStatus not 200')
        raise Exception('Ошибка при запросе к апи')
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность"""
    if len(response) == 0:
        logger.error('bad responce from api')
        raise Exception('Пустой словарь')
    homework = response['homeworks']
    if type(homework) != list:
        logger.error('api responce is not list')
        raise Exception(
            'под ключом `homeworks` домашки приходят не в виде списка'
        )
    return homework


def parse_status(homework):
    """Извлекает из информации о конкретной домашней
    работе статус этой работы"""
    if len(homework) == 0:
        logger.error('no homework to check')
        raise Exception('Нет домашки для проверки')
    homework_name = homework['homework_name']
    if homework['status'] not in HOMEWORK_STATUSES:
        logger.error('homework status is incorrect')
        raise Exception('Неправильный статус дз')
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения, которые необходимы для
    работы программы"""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    logger.critical('check tokens fails')
    return False


def main():
    """Основная логика работы бота."""
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
