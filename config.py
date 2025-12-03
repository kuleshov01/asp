# Указываем месяц и год вручную
month = 'декабрь'
year = 2025  # Можно изменить на нужный год

# Опциональная дата окончания для услуг (если не указана, используется последний день месяца)
# Например, для использования 5 декабря: custom_expiration_date = '05.12.2025'
custom_expiration_date = '05.12.2025'  # Установите значение в формате 'DD.MM.YYYY' для использования пользовательской даты

from datetime import datetime
from dateutil.relativedelta import relativedelta

# Словари для преобразования месяца
months_lower = {
    'январь': 1, 'февраль': 2, 'март': 3, 'апрель': 4,
    'май': 5, 'июнь': 6, 'июль': 7, 'август': 8,
    'сентябрь': 9, 'октябрь': 10, 'ноябрь': 11, 'декабрь': 12
}
month_names = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
    5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
    9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}


# Автоматический пересчет дат при изменении месяца
def _init_dates():
    """Вычисляет все переменные дат на основе config.month и config.year."""
    if month is None:
        raise ValueError("config.month не установлен")
    if year is None:
        raise ValueError("config.year не установлен")

    # Определяем номер месяца
    month_num = months_lower.get(month.lower())
    if month_num is None:
        raise ValueError(f"Неизвестный месяц: {month}")

    # Вычисляем даты
    start = datetime(year, month_num, 1)
    if month_num == 12:
        end = datetime(year + 1, 1, 1) - relativedelta(days=1)
    else:
        end = datetime(year, month_num + 1, 1) - relativedelta(days=1)

    # Проверяем, установлена ли пользовательская дата окончания
    if 'custom_expiration_date' in globals() and custom_expiration_date is not None:
        try:
            # Если установлена пользовательская дата, используем её для day_of_month
            custom_date_obj = datetime.strptime(custom_expiration_date, '%d.%m.%Y')
            day = custom_date_obj.day
            data_month = custom_date_obj.strftime("%d.%m.%Y")
        except ValueError:
            # Если формат даты неправильный, используем стандартные значения
            day = end.strftime("%d")
            data_month = end.strftime("%d.%m.%Y")
    else:
        # Используем стандартные значения
        day = end.strftime("%d")
        data_month = end.strftime("%d.%m.%Y")

    # Возвращаем результаты
    return {
        'month_full': f"{month_names[month_num]} {year}",
        'data_month': data_month,
        'day_of_month': str(day),
        'nach_year': str(year),
        'nach_month': end.strftime("%m.%Y"),
        'start_month_datetime': start
    }

# Инициализация переменных при импорте
if month and year:
    dates = _init_dates()
    month_full = dates['month_full']
    data_month = dates['data_month']
    day_of_month = dates['day_of_month']
    nach_year = dates['nach_year']
    nach_month = dates['nach_month']
    start_month_datetime = dates['start_month_datetime']
else:
    raise ValueError("Невозможно сформировать переменные для месяца")