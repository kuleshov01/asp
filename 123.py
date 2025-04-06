import pandas as pd
from datetime import datetime, timedelta
import numpy as np
from workalendar.europe import Russia  # для учета российских праздников

def calculate_adjusted_services(start_month_datetime, start_obsl, rounded_plan):
    # Создаем календарь для учета праздников
    cal = Russia()
    
    # Определяем конец месяца
    if start_month_datetime.month == 12:
        end_month = datetime(start_month_datetime.year + 1, 1, 1)
    else:
        end_month = datetime(start_month_datetime.year, start_month_datetime.month + 1, 1)
    end_month -= timedelta(days=1)  # последний день месяца
    
    # Рассчитываем все рабочие дни месяца
    all_work_days = cal.get_working_days_delta(start_month_datetime, end_month)
    
    # Рассчитываем рабочие дни с даты начала обслуживания
    actual_work_days = cal.get_working_days_delta(start_obsl.to_pydatetime(), end_month)
    
    # Рассчитываем процент отработанных дней
    if all_work_days > 0:
        percentage = actual_work_days / all_work_days
    else:
        percentage = 1  # если месяц без рабочих дней (крайний случай)
    
    # Корректируем план и округляем вверх
    adjusted_plan = np.ceil(rounded_plan * percentage)
    
    return int(adjusted_plan)

# Пример использования:
start_month_datetime = datetime(2025, 3, 1)
start_obsl = pd.Timestamp('2025-02-01 00:00:00')
rounded_plan = 20  # пример значения

adjusted = calculate_adjusted_services(start_month_datetime, start_obsl, rounded_plan)
print(f"Скорректированный план: {adjusted}")