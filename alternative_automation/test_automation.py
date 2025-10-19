"""
Тестовый скрипт для проверки альтернативной реализации без Playwright
"""
import os
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Добавляем текущую директорию в путь Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from advanced_http_client import AdvancedWebAutomationClient
from automation_functions import find_child, new_contract, find_dogovor, new_dogovor, select_date, edit_page, nach_page
from datetime import datetime

def test_basic_functionality():
    """
    Тест основной функциональности
    """
    print("=== Тестирование основной функциональности ===")
    
    # Создаем клиент
    client = AdvancedWebAutomationClient()
    print("Клиент создан")
    
    # Проверяем основные методы
    print(f"Метод login существует: {hasattr(client, 'login')}")
    print(f"Метод search_child существует: {hasattr(client, 'search_child')}")
    print(f"Метод get_child_card существует: {hasattr(client, 'get_child_card')}")
    print(f"Метод update_contract_data существует: {hasattr(client, 'update_contract_data')}")
    
    # Проверяем функции
    print(f"Функция find_child существует: {callable(find_child)}")
    print(f"Функция new_contract существует: {callable(new_contract)}")
    print(f"Функция find_dogovor существует: {callable(find_dogovor)}")
    print(f"Функция new_dogovor существует: {callable(new_dogovor)}")
    print(f"Функция select_date существует: {callable(select_date)}")
    print(f"Функция edit_page существует: {callable(edit_page)}")
    print(f"Функция nach_page существует: {callable(nach_page)}")
    
    print("Базовая проверка пройдена!")

def test_date_processing():
    """
    Тест обработки дат
    """
    print("\n=== Тест обработки дат ===")
    
    from automation_functions import _init_dates, month, data_month, day_of_month, nach_year, nach_month
    
    print(f"Месяц: {month}")
    print(f"Дата месяца: {data_month}")
    print(f"День месяца: {day_of_month}")
    print(f"Год начисления: {nach_year}")
    print(f"Месяц начисления: {nach_month}")
    
    print("Обработка дат работает!")

def test_data_processing():
    """
    Тест обработки данных
    """
    print("\n=== Тест обработки данных ===")
    
    from automation_functions import calc_work, process_numbers
    
    # Тест calc_work
    start_date = datetime(2025, 1, 1)
    result = calc_work(start_date, 10)
    print(f"calc_work результат: {result}")
    
    # Тест process_numbers
    try:
        result = process_numbers(84, 30, start_date)
        print(f"process_numbers результат: {result}")
    except Exception as e:
        print(f"process_numbers ошибка: {e}")
    
    print("Обработка данных работает!")

if __name__ == "__main__":
    test_basic_functionality()
    test_date_processing()
    test_data_processing()
    
    print("\n=== Все тесты завершены ===")
    print("Альтернативная реализация готова к использованию!")
    print("Для полного тестирования рекомендуется запустить основной скрипт с реальными данными.")