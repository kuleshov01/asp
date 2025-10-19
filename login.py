from playwright.sync_api import sync_playwright # type: ignore
import os
import json
from func import select_date, edit_page, nach_page, find_child, new_contract, new_dogovor, find_dogovor
from exel import df_load, df_filter, df_replace, df_save, df_find
import sys
import traceback
import math
import config


month = config.month

# Выводим рассчитанные параметры
print("Рассчитанные параметры:")
print(f"  month_full: {config.month_full}")
print(f"  data_month: {config.data_month}")
print(f"  day_of_month: {config.day_of_month}")
print(f"  nach_year: {config.nach_year}")
print(f"  nach_month: {config.nach_month}")
print(f" start_month_datetime: {config.start_month_datetime}")
print()


df = None
# Ваши учетные данные
LOGIN = "SAV"
PASSWORD = "08082022"
SESSION_FILE = "session_data.json"

def save_session(page):
    """Сохраняет cookies в файл."""
    cookies = page.context.cookies()
    with open("session.json", "w") as file:
        json.dump(cookies, file)

def load_session(context):
    """Загружает cookies из файла."""
    if os.path.exists("session.json"):
        with open("session.json", "r") as file:
            cookies = json.load(file)
            print(cookies)
        context.add_cookies(cookies)

def increment_prefix(original: str) -> str:
    try:
        num, year = original.split('/')
        return f"{int(num) + 1}/{year}"
    except (ValueError, AttributeError):
        return "error"  # или можно выбросить исключение


def try_authorization(page):
    """
    Попытка авторизации, если пользователь был перенаправлен на страницу авторизации.
    """
    # Ожидаем появления поля логина
    page.wait_for_selector('#tbUserName')

    # Заполнение логина
    page.fill('#tbUserName', LOGIN)

    # Заполнение пароля
    page.fill('#tbPassword', PASSWORD)

    # Нажатие на контейнер, чтобы открыть выпадающий список
    page.click('#baseListContainer')

    # Ожидание появления выпадающего списка
    page.wait_for_selector('.dropdown')

    # Поиск строки с текстом "Социальное обслуживание" в таблице
    row = page.query_selector('xpath=//table[@id="gvBases"]//tr[contains(., "Социальное обслуживание")]')

    if row:
        # Клик на найденную строку
        row.click()
        print("Пункт 'Социальное обслуживание' выбран.")
    else:
        print("Пункт 'Социальное обслуживание' не найден.")

    # Нажатие кнопки "Войти"
    page.click('#lbtnLogin')

    # Ожидание завершения авторизации (например, появления элемента на следующей странице)
    page.wait_for_selector('#ctl00_cph_TopStr_NastrMenuTop')

    # Сохраняем сессию после успешной авторизации
    #save_session(page)
    context.storage_state(path=SESSION_FILE)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)

    if os.path.exists(SESSION_FILE):
        # Если сессия сохранена, загружаем её
        context = browser.new_context(storage_state=SESSION_FILE)
        print("Используем сохраненную сессию.")
    else:
        # Если сессия не сохранена, создаем новый контекст
        context = browser.new_context()
        print("Создаем новую сессию.")

    page = context.new_page()

    try:

        # Переход на целевую страницу
        page.goto(
        "http://localhost/aspnetkp/Common/ListDeclaration.aspx?GSP=25",
        timeout=60000,  # 60 секунд вместо 30
        wait_until="domcontentloaded"  # Ждём только загрузку DOM, а не всех ресурсов
        )


        # Попытаемся дождаться появления элемента на целевой странице
        start = page.query_selector('#ctl00_cph_grdList_ctl01_ctrlFastFind_tbFind')
        if start is None:
            print("Элемент не найден, вероятно, произошла переадресация на страницу авторизации.")
            try_authorization(page)

        df, orig_df, sheet = df_load()
        records = df_filter(df, month)

        #records = [entry for entry in records if 'Бадыкшанова Анна' in entry['фио ']] #DEBUG#  

        if records:
            # Пример вывода одного элемента
            for i, record in enumerate(records):  # Идем с конца массива, чтобы избежать проблем с индексацией при удалении элементов
                try:
                    if record[month] != '!':
                        page.fill('#ctl00_cph_grdList_ctl01_ctrlFastFind_tbFind', record['фио '])
                        page.click('#ctl00_cph_grdList_ctl01_ctrlFastFind_lbtnFastFind')
                        print(f"\nПоиск заявлениий ребенка {record['фио ']} [{i+1}/{len(records)}]")

                        #Проверка на наличие договора в заявлении
                        is_new = (not record['номер договора']) or str(record['номер договора']).strip().lower() in ('nan', 'none', '')

                        #Проверка на наличие договора
                        page = find_child(page, 'new' if is_new else 'old', record['дата ипр'])
                        
                        # Проверяем, что page не является None
                        if page is None:
                            print(f"Не удалось найти карточку пользователя для {record['фио ']}, пропускаем запись.")
                            continue

                        # Проверяем, находимся ли мы на странице просмотра заявления
                        # Если элемент с ФИО не найден, значит карточка не была найдена
                        try:
                            page.wait_for_selector("#ctl00_cph_lbFIOZUsl", timeout=5000)
                        except:
                            print(f"Карточка пользователя для {record['фио ']} не найдена, пропускаем запись.")
                            continue

                        #Обновляем значение, если внутри договора нет, а мы думаем что есть
                        element = page.query_selector("#ctl00_cph_grZayvView_ctl02_tr_Rekv > td > span")
                        if not element:
                            is_new = True

                        if is_new:
                            page = new_contract(page)
                            #!!!нужно как-то проверять, сначала на странице есть ли договор
                            #!!!обновлять df и уже искать последний средни них, если надо
                            page, number_doc = find_dogovor(page)
                            


                            

                            if number_doc:
                                print(f"У заявителя уже имеется заполненый договор {number_doc}")
                            else:  

                                number_doc = increment_prefix(df_find(df))
                                page = new_dogovor(page, record['взяли на обслуживание '], number_doc)
                                print("Договор заявителя заполен")

                            
                            record['номер договора'] = number_doc
                            #Обновляем датафрейм
                            df = df_replace(df, record)
                        else:
                            print("У заявителя уже имеется заполненый договор")
                        not_end = False
                        try:
                            while True:
                                
                                page, not_end = select_date(page)
                                if not_end: #Если заявления уже заполнено, то событие завершается
                                    page, error = edit_page(page, record['взяли на обслуживание '])

                                    # Если edit_page выполнена успешно, выходим из цикла while
                                    if error is None:
                                        break

                                    print(f"Перезапуск процесса для записи {record['фио ']}")

                                break
                            if not_end:
                                page = nach_page(page)
                        except Exception as e:
                            print(f"Ошибка при обработке заявления {record['фио ']}: {e}")
                            # Возвращаемся к списку заявлений и продолжаем следующей записи
                            try:
                                page.goto("http://localhost/aspnetkp/Common/ListDeclaration.aspx?GSP=25")
                            except:
                                print("Не удалось вернуться к списку заявлений")
                            continue

                        record[month] = '!'
                        # Ждем появления элемента сохранения и кликаем по нему
                        try:
                            page.wait_for_selector("#ctl00_cph_TopStr1_lbtnTopStr_SaveExit", timeout=10000)
                            page.click("#ctl00_cph_TopStr1_lbtnTopStr_SaveExit")
                            print(f"Выход из страницы заявления")
                        except:
                            print("Элемент сохранения не найден, возможно страница уже изменилась")
                        df = df_replace(df, record)
                except Exception as e:
                    print(f"Ошибка при обработке записи {record['фио ']}: {e}")
                    #traceback.print_exc()  # Печатает полный traceback
                    if page is not None:
                        page.goto("http://localhost/aspnetkp/Common/ListDeclaration.aspx?GSP=25")
                    else:
                        print("Объект page равен None, невозможно выполнить переход на страницу.")
                        # Повторно создаем page объект
                        page = context.new_page()
                        page.goto("http://localhost/aspnetkp/Common/ListDeclaration.aspx?GSP=25")
                
                df_save(df, sheet)

        else:
            print("Заявлений больше нет")
        

    except Exception as e:
        print(f"Ошибка при обработке: {e}")
        traceback.print_exc()  # Печатает полный traceback
        if page is not None:
            page.goto("http://localhost/aspnetkp/Common/ListDeclaration.aspx?GSP=25")
        else:
            print("Объект page равен None, невозможно выполнить переход на страницу.")


    finally:
        # Закрытие браузера
        browser.close()
        print("Скрипт завершается...")
        sys.exit(0)