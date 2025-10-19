import os
from dotenv import load_dotenv
from automation_functions import select_date, edit_page, nach_page, find_child, new_contract, new_dogovor, find_dogovor, remove_middle_name
from excel_handler import df_load, df_filter, df_replace, df_save, df_find
import sys
import traceback
import math
import config
from advanced_http_client import AdvancedWebAutomationClient

month = config.month

# Выводим рассчитанные параметры
print("Рассчитанные параметры:")
print(f"  month_full: {config.month_full}")
print(f"  data_month: {config.data_month}")
print(f"  day_of_month: {config.day_of_month}")
print(f" nach_year: {config.nach_year}")
print(f" nach_month: {config.nach_month}")
print(f" start_month_datetime: {config.start_month_datetime}")
print()

df = None
# Ваши учетные данные

# Загружаем переменные окружения из файла .env
load_dotenv()

def increment_prefix(original: str) -> str:
    try:
        num, year = original.split('/')
        return f"{int(num) + 1}/{year}"
    except (ValueError, AttributeError):
        return "error"  # или можно выбросить исключение

def main():
    client = AdvancedWebAutomationClient()
    
    if not client.login():
        print("Не удалось авторизоваться")
        return

    df, orig_df, sheet = df_load()
    records = df_filter(df, month)

    # records = [entry for entry in records if 'Бадыкшанова Анна' in entry['фио ']] #DEBUG#

    if records:
        # Пример вывода одного элемента
        for i, record in enumerate(records):  # Идем с конца массива, чтобы избежать проблем с индексацией при удалении элементов
            try:
                if record[month] != '!':
                    # Применяем функцию для удаления отчества из корейских имен
                    processed_fio = remove_middle_name(record['фио '])
                    
                    print(f"\nПоиск заявлениий ребенка {record['фио ']} [{i+1}/{len(records)}]")

                    # Проверка на наличие договора в заявлении
                    is_new = (not record['номер договора']) or str(record['номер договора']).strip().lower() in ('nan', 'none', '')

                    # Используем наши HTTP-функции для поиска карточки
                    card_url = find_child(client, processed_fio, 'new' if is_new else 'old', record['дата ипр'])
                    
                    # Проверяем, что card_url не является None
                    if card_url is None:
                        print(f"Не удалось найти карточку пользователя для {record['фио ']}, пропускаем запись.")
                        continue

                    if is_new:
                        client = new_contract(client, card_url)
                        client, number_doc = find_dogovor(client, card_url)
                        
                        if number_doc:
                            print(f"У заявителя уже имеется заполненый договор {number_doc}")
                        else:
                            number_doc = increment_prefix(df_find(df))
                            client = new_dogovor(client, card_url, record['взяли на обслуживание '], number_doc)
                            print("Договор заявителя заполен")
                        
                        record['номер договора'] = number_doc
                        # Обновляем датафрейм
                        df = df_replace(df, record)
                    else:
                        print("У заявителя уже имеется заполненый договор")
                    
                    not_end = False
                    try:
                        while True:
                            
                            client, not_end = select_date(client, card_url)
                            if not_end: #Если заявления уже заполнено, то событие завершается
                                client, error = edit_page(client, card_url, record['взяли на обслуживание '])
                                
                                # Если edit_page выполнена успешно, выходим из цикла while
                                if error is None:
                                    break

                                print(f"Перезапуск процесса для записи {record['фио ']}")

                            break
                        if not_end:
                            client = nach_page(client, card_url)
                    except Exception as e:
                        print(f"Ошибка при обработке заявления {record['фио ']}: {e}")
                        # Возвращаемся к списку заявлений и продолжаем следующей записи
                        continue

                    record[month] = '!'
                    # Ждем появления элемента сохранения и кликаем по нему
                    # В реальности здесь нужно будет отправить запрос на сохранение
                    
                    df = df_replace(df, record)
            except Exception as e:
                print(f"Ошибка при обработке записи {record['фио ']}: {e}")
                # traceback.print_exc()  # Печатает полный traceback
                continue
            
            df_save(df, sheet)

    else:
        print("Заявлений больше нет")

if __name__ == "__main__":
    from datetime import datetime
    main()
    print("Скрипт завершается...")
    sys.exit(0)