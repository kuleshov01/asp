from playwright.sync_api import sync_playwright
from datetime import datetime
import os, sys
import re
import math

# Ваши учетные данные
LOGIN = "SAV"
PASSWORD = "08082022"
BASE = "Социальное обслуживание"

# Получаем путь к текущей папке, где выполняется скрипт
current_directory = os.path.dirname(os.path.abspath(__file__))

# Формируем полный путь к файлу
file_path = os.path.join(current_directory, "site/edit_page.mhtml")

def process_numbers(plan, actual):
    if actual == 0:
        raise ValueError("Фактическое число не может быть равно нулю.")

    rounded_plan = math.ceil(plan / 3)

    if rounded_plan > actual:
        return actual
    else:
        return rounded_plan

with sync_playwright() as p:
    # Запуск браузера
    browser = p.chromium.launch(headless=False)  # headless=False для видимого браузера
    page = browser.new_page()

    # Переход на страницу авторизации
    page.goto(f"file://{file_path}")  # Используем полный путь к файлу
    
    page.wait_for_selector('#ctl00_cph_UF1_pgrTabel__wibNextPage')
    page.click("#ctl00_cph_UF1_pgrTabel__wibNextPage")

    # JavaScript-код для нажатия на кнопку
    js_code = """
    const button = document.querySelector('#ctl00_cph_UF1_pgrTabel__wibNextPage');
    button.click();
    """
    
    # Выполняем JavaScript на странице
    page.evaluate(js_code)
          

    page.wait_for_timeout(50000)

    # Закрытие браузера
    browser.close()