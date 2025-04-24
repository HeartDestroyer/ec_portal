# Модуль с вспомогательными функциями для работы с данными

from dateutil import parser as date_parser
import phonenumbers
from phonenumbers import PhoneNumberFormat
from email_validator import validate_email, EmailNotValidError
from typing import Optional
import bleach

# Форматирование даты из формата 'YYYY-MM-DDTHH:MM:SS+TZ' в 'DD.MM.YYYY'
def format_date(date_str: str) -> Optional[str]:
    """
    Форматирование даты из формата 'YYYY-MM-DDTHH:MM:SS+TZ' в 'DD.MM.YYYY'
    :param date_str: Строка с датой в формате ISO
    :return: Отформатированная дата или None в случае ошибки
    """
    if not date_str:
        return None
        
    try:
        dt = date_parser.isoparse(date_str)
        return dt.strftime('%d.%m.%Y')
    except (ValueError, TypeError, AttributeError):
        return None

# Форматирование российского номера телефона в международный формат
def format_phone_number(phone_number: str) -> Optional[str]:
    """
    Форматирование номера телефона в международный формат
    :param phone_number: Номер телефона для форматирования
    :return: Отформатированный номер телефона или None в случае ошибки
    """
    try:
        parsed = phonenumbers.parse(phone_number, None)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
        else:
            return None
    except phonenumbers.NumberParseException:
        return None

# Валидация email адреса
def validate_email(email: str) -> bool:
    """
    Валидация email адреса
    :param email: Email адрес для проверки
    :return: True если email валиден иначе False
    """
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False

# Очистка входных данных от потенциально опасных символов
def sanitize_input(input_str: str, context: str = "html") -> str:
    """
    Очистка входных данных от потенциально опасных символов
    :param input_str: Строка для очистки
    :param context: Контекст, в котором используется строка
    :return: Очищенная строка
    """
    if not input_str:
        return ""
    if context == "html":
        return bleach.clean(input_str, tags=[], attributes={}, strip=True)
    elif context == "sql":
        return input_str.replace("'", "''")
    else:
        return input_str
