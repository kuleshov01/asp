from playwright.sync_api import sync_playwright
from datetime import datetime
import os, sys

# Ваши учетные данные
LOGIN = "SAV"
PASSWORD = "08082022"
BASE = "Социальное обслуживание"

# Получаем путь к текущей папке, где выполняется скрипт
current_directory = os.path.dirname(os.path.abspath(__file__))

# Формируем полный путь к файлу
file_path = os.path.join(current_directory, "site/1234.mhtml")

with sync_playwright() as p:
    # Запуск браузера
    browser = p.chromium.launch(headless=False)  # headless=False для видимого браузера
    page = browser.new_page()

    # Переход на страницу авторизации
    page.goto(f"file://{file_path}")  # Используем полный путь к файлу

    # Нахождение таблицы с классом RS_Grid2
    grid_table = page.query_selector(".RS_Grid2")

    if grid_table:
        # Нахождение всех строк в таблице
        table_rows = grid_table.query_selector_all("tbody > tr")

        # Словарь для хранения индексов колонок
        column_indices = {}

        # Первый проход по таблице для поиска заголовков
        first_row = table_rows[0]
        headers = first_row.query_selector_all("td.RS_GridHeader2")

        # Цикл для поиска колонок "Поставщик" и "Дата"
        for idx, header in enumerate(headers):
            text = header.inner_text().strip().lower()  # Приводим текст к нижнему регистру
            if "поставщик" in text:
                column_indices["Поставщик"] = idx + 1
            elif "дата" in text:
                column_indices["Дата"] = idx + 1

        # Проверка, найдены ли обе колонки
        if "Поставщик" in column_indices and "Дата" in column_indices:
            print(f"Колонки найдены: Поставщик - {column_indices['Поставщик']}, Дата - {column_indices['Дата']}")
            
            # Вывод всех строк не включая заголовки
            body_rows = grid_table.query_selector_all("tbody > tr[class]")
            
            target_row = None
            latest_date = None
            
            for row in body_rows:
                supplier = row.query_selector(f"td:nth-of-type({column_indices['Поставщик']})")
                date = row.query_selector(f"td:nth-of-type({column_indices['Дата']})")
                
                if supplier and date:
                    supplier_text = supplier.inner_text().strip()
                    date_text = date.inner_text().strip()
                    # Очистка строки от лишних символов
                    cleaned_data = date_text.replace('\xa0Р', '').strip()
                    date = datetime.strptime(cleaned_data, '%d.%m.%Y')  # Преобразование строки в объект datetime.
                    
                    print(f"Поставщик: {supplier_text}, Дата: {date_text}")
                    
                    # Проверка, если поставщик равен "Раскрой свzzzой мир"
                    if 'АНО "Раскрой свой мир"' in supplier_text:
                        print("Найден поставщик 'Раскрой свой мир'. Продолжаем обработку...")
                        # Если это первая подходящая строка или дата более поздняя
                        if latest_date is None or date > latest_date:
                            latest_date = date
                            target_row = row
                    else:
                        print("Не найден поставщик 'Раскрой свой мир'.")
    #Ищем кнопку редактирования и переходим
    button = target_row.query_selector('a[title="Просмотр и редактирование"]')
    id_value = button.get_attribute('id')
    page.click(f'#{id_value}')  
          
    # Закрытие браузера
    browser.close()