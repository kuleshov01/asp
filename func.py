from playwright.sync_api import Page # type: ignore
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re
import math
import pandas as pd
import time
import numpy as np
from workalendar.europe import Russia  # для учета российских праздников
import config, sys
import pdb


start_obsl = None
new_day_of_month = ''

expiration_date = None

class RussiaWithTransfers(Russia):
    """
    Российский календарь с учетом переносов выходных на 2025 год
    """
    extra_holidays = [
        datetime(2025, 5, 2),   # Перенос с 4 января
        datetime(2025, 5, 8),   # Перенос с 23 февраля
        datetime(2025, 6, 13),  # Перенос с 8 марта (ключевой для июня!)
        datetime(2025, 11, 3),  # Перенос с 1 ноября
        datetime(2025, 12, 31), # Перенос с 5 января
    ]

    def is_working_day(self, day):
        if day in self.extra_holidays:
            return False
        return super().is_working_day(day)

    def get_working_days_delta(self, start_date, end_date):
        """Исправленный расчет с включением end_date"""
        days = 0
        current = start_date
        
        while current <= end_date:  # Изменили на <= для включения последнего дня
            if self.is_working_day(current):
                days += 1
            current += timedelta(days=1)
        
        return days

def _init_dates():
    """Вычисляет все переменные дат на основе config.month."""
    if config.month is None:
        raise ValueError("config.month не установлен")

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

    # Определяем год и номер месяца
    year = datetime.now().year
    month_num = months_lower.get(config.month.lower())
    if month_num is None:
        raise ValueError(f"Неизвестный месяц: {config.month}")

    # Вычисляем даты
    start = datetime(year, month_num, 1)
    if month_num == 12:
        end = datetime(year + 1, 1) - timedelta(days=1)
    else:
        end = datetime(year, month_num + 1, 1) - timedelta(days=1)

    # Возвращаем результаты
    return {
        'month': f"{month_names[month_num]} {year}",
        'data_month': end.strftime("%d.%m.%Y"),
        'day_of_month': end.strftime("%d"),
        'nach_year': str(year),
        'nach_month': end.strftime("%m.%Y"),
        'start_month_datetime': start
    }

# Импортируем переменные из config
try:
    month = config.month_full
    data_month = config.data_month
    day_of_month = config.day_of_month
    nach_year = config.nach_year
    nach_month = config.nach_month
    start_month_datetime = config.start_month_datetime
except AttributeError:
    # Если переменные не определены в config, используем функцию _init_dates
    if config.month:
        dates = _init_dates()
        month = dates['month']
        data_month = dates['data_month']
        day_of_month = dates['day_of_month']
        nach_year = dates['nach_year']
        nach_month = dates['nach_month']
        start_month_datetime = dates['start_month_datetime']
    else:
        raise ValueError("Невозможно сформировать переменные для месяца")


def calc_work(start_date, rounded_plan):
    global start_month_datetime
    global expiration_date

    if start_date < start_month_datetime:
        start_date = start_month_datetime
    else: 
        start_date = start_date.to_pydatetime()

    # Создаем календарь для учета праздников
    cal = RussiaWithTransfers()

    # Определяем конец месяца
    if start_month_datetime.month == 12:
        end_month = datetime(start_month_datetime.year + 1, 1, 1)
    else:
        end_month = datetime(start_month_datetime.year, start_month_datetime.month + 1, 1)
    end_month -= timedelta(days=1)  # последний день месяца

    # Рассчитываем все рабочие дни месяца
    all_work_days = cal.get_working_days_delta(start_month_datetime, end_month)
    
    #проверка если месяц не полный
    if expiration_date is not None:
        end_month = datetime.strptime(expiration_date, '%d.%m.%Y') 

    # Рассчитываем рабочие дни с даты начала обслуживания
    actual_work_days = cal.get_working_days_delta(start_date, end_month)
    
    # Рассчитываем процент отработанных дней
    if all_work_days > 0:
        percentage = actual_work_days / all_work_days
    else:
        percentage = 1 # если месяц без рабочих дней (крайний случай)
    
    # Корректируем план и округляем вверх
    adjusted_plan = np.ceil(rounded_plan * percentage)

    if int(adjusted_plan) == 0:
        raise ValueError("Заполняемое число услуг не может быть равно нулю.")
    
    return int(adjusted_plan)

def process_numbers(plan, actual, date_start):

    if actual == 0:
        raise ValueError("Фактическое число ИП не может быть равно нулю.")

    if plan == 84: 
        return 28
    
    rounded_plan = math.ceil(plan / 3)

    if rounded_plan >= actual:
        return calc_work(date_start, actual)
    else:
        if start_obsl > 1:
            rounded_plan = rounded_plan - 1
        return calc_work(date_start, rounded_plan)

def find_child(page: Page, status, start_date):
    if page:
        page.wait_for_selector('#ctl00_cph_grdList > tbody > tr')
        print('Поиск необходимой карточки пользователя')
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
                #print(f"Колонки найдены: Поставщик - {column_indices['Поставщик']}, Дата - {column_indices['Дата']}")
                
                # Вывод всех строк не включая заголовки
                body_rows = grid_table.query_selector_all("tbody > tr[class]")
                
                target_row = None
                latest_date = None
                for row in body_rows:
                    supplier = row.query_selector(f"td:nth-of-type({column_indices['Поставщик']})")
                    date = row.query_selector(f"td:nth-of-type({column_indices['Дата']})")

                    date1 = start_date.strftime("%d.%m.%Y")

                    if supplier and date:
                        supplier_text = supplier.inner_text().strip()
                        date_text = date.inner_text().strip()

                        # Очистка строки от лишних символов
                        cleaned_data = date_text.replace('\xa0Р', '').strip()
                        try:
                            date = datetime.strptime(cleaned_data.split()[0], '%d.%m.%Y')  # Преобразование строки в объект datetime.
                        except ValueError:
                            continue  # Пропускаем, если формат даты не распознан
                        
                        #Если дата в строке совпала с датой заявления, значит это оно, можно не искать дальше
                        if ((supplier_text == '' or 'АНО "Раскрой свой мир"' in supplier_text)  and cleaned_data == date1):
                            target_row = row
                            print("Дата ИПР совпала с датой в exel. Пропускаем все и берем это заявление")
                            break
                    
                        img = page.locator('img[title*="Предоставление услуг"]')
                        # Поиск новых или старых в завимости их задачи
                        if (
                            #(supplier_text == '' and status == 'new' and page.is_visible('img[title="Составлена ИП"]')) or
                            ((supplier_text == '' or 'АНО "Раскрой свой мир"' in supplier_text) and status == 'new' and page.is_visible('img[title="Составлена ИП"]')) or
                            ('АНО "Раскрой свой мир"' in supplier_text and status == 'old') or
                            ('АНО "Раскрой свой мир"' in supplier_text and img.count() > 0) or
                            ('АНО "Раскрой свой мир"' in supplier_text and status == 'new' and (page.is_visible('img[title="Выбран поставщик"]') or page.is_visible('img[title="Заключен договор"]')))
                        ):
                            # Если это первая подходящая строка или дата более поздняя
                            if latest_date is None or date > latest_date:
                                latest_date = date
                                target_row = row

                # Ищем кнопку редактирования и переходим
                if target_row:
                    button = target_row.query_selector('a[title="Просмотр и редактирование"]')
                    if button:
                        id_value = button.get_attribute('id')
                        page.click(f'#{id_value}')
                        print(f"Переход на страницу ребенка #{id_value}")
                        return page
                else:
                    print("Не найдена подходящая карточка пользователя")
                    # Возвращаемся к списку заявлений
                    try:
                        page.goto("http://localhost/aspnetkp/Common/ListDeclaration.aspx?GSP=25")
                    except:
                        print("Не удалось вернуться к списку заявлений")
                    return page  # Возвращаем page, даже если карточка не найдена
        else:
            print("Таблица с классом RS_Grid2 не найдена")
            # Пытаемся вернуться к списку заявлений
            try:
                page.goto("http://localhost/aspnetkp/Common/ListDeclaration.aspx?GSP=25")
            except:
                print("Не удалось вернуться к списку заявлений")
            return page  # Возвращаем page, даже если таблица не найдена
    else:
        print("Объект page не определен")
        return None
                

def new_contract(page: Page):
    if page:
        page.wait_for_selector("#ctl00_cph_lbFIOZUsl")
        if not page.is_visible("#ctl00_cph_lbtnTabReshen"):
            page.click("#ctl00_cph_btnReshen")
            page.click("#ctl00_cph_pw_divReshen_divContent_rbl_Resh2_0")
            page.click("#ctl00_cph_pw_divReshen_ctl05_btnOk")

            page.click("#ctl00_cph_Chk27000010002000101")
            page.click("#ctl00_cph_Imagebutton_Exit")
            page.click("#ctl00_cph_Chk2000")
            page.click("#ctl00_cph_Imagebutton_Exit")

        return page
    
def find_dogovor(page: Page):

    if page:
        page.click("#ctl00_cph_lbtnTabReshen")

        #Если уже договор заполен, то сбрасываем
        element = page.query_selector("#ctl00_cph_grZayvView_ctl02_tr_Rekv > td > span")
        if element:
            number_dogovor = page.locator("#ctl00_cph_grZayvView_ctl02_ListDogovor > option:nth-child(1)").inner_text()
            extracted = number_dogovor.split("№")[1].split(" от ")[0] 
            return page, extracted
        else:
            return page, None
    
def new_dogovor(page: Page, take_serv, number_doc):
    global start_month_datetime

    if page:

        option_text = page.locator("#ctl00_cph_ListData > option").inner_text() #дата составления ИПР
        cleaned_data = option_text.split('*')[0].strip() 
        date1 = datetime.strptime(cleaned_data, '%d.%m.%Y')
        end_date = date1 + relativedelta(years=1) - relativedelta(days=1) ## ИПР +год -1 день
        end_date = end_date.strftime("%d.%m.%Y")

        take_serv_as_dt = take_serv.to_pydatetime()
        # Выбираем бóльшую дату между date1 и take_serv, но не меньше февраля 2025
        new_date_dt = max(date1, take_serv_as_dt)  # Сначала берем позднюю из двух
        new_date_dt = max(new_date_dt, start_month_datetime)   # Но не раньше февраля 2025

        new_date = new_date_dt.strftime("%d.%m.%Y")
        take_serv = take_serv_as_dt.strftime("%d.%m.%Y")

        page.fill("#igtxtctl00_cph_grZayvView_ctl02_wdtDatr", take_serv)
        page.fill("#igtxtctl00_cph_grZayvView_ctl02_wdDatBegin", new_date)
        page.fill("#igtxtctl00_cph_grZayvView_ctl02_wdDatEnd", end_date)

        page.click("#ctl00_cph_grZayvView_ctl02_lbtnEditSoglUsl > img")
        page.click("#ctl00_cph_UslSogl_mnuAddDog > li > div > img")
        page.fill("#igtxtctl00_cph_WDC_D_Date", new_date)
        page.fill("#ctl00_cph_TB_D_Nomer", number_doc)
        # Добавляем проверку, что номер договора заполнен правильно
        page.wait_for_timeout(500)  # Ждем 0.5 секунды, чтобы убедиться, что значение установлено
        filled_number = page.input_value("#ctl00_cph_TB_D_Nomer")
        if filled_number != number_doc:
            print(f"Предупреждение: номер договора не был установлен корректно. Ожидалось: {number_doc}, получено: {filled_number}")
            # Повторяем ввод, если значение не установлено корректно
            page.fill("#ctl00_cph_TB_D_Nomer", number_doc)
            page.wait_for_timeout(200)
            filled_number = page.input_value("#ctl00_cph_TB_D_Nomer")
            if filled_number != number_doc:
                print(f"Ошибка: не удалось установить номер договора. Ожидалось: {number_doc}, получено: {filled_number}")
            else:
                print(f"Номер договора: {number_doc}")
        
        #Почему-то с первого раза не сохраняется
        page.click("#ctl00_cph_LB_Save")
        page.wait_for_timeout(2000)
        page.click("#ctl00_cph_LB_Save")
        page.wait_for_timeout(2000)
        page.click("#ctl00_cph_LB_Save")
        
        # Проверяем наличие и кликаем по кнопке выхода с сохранением
        try:
            page.wait_for_selector("#ctl00_cph_LB_Exit_Save_No", timeout=5000)
            page.click("#ctl00_cph_LB_Exit_Save_No")
        except:
            print("Ошибка: элемент #ctl00_cph_LB_Exit_Save_No не найден или недоступен")
            raise Exception("Отсутствует кнопка выхода с сохранением")
        
        # Проверяем наличие и кликаем по кнопке добавления услуг ИП
        try:
            page.wait_for_selector("#ctl00_cph_UslSogl_btnAddUslIP", timeout=5000)
            page.click("#ctl00_cph_UslSogl_btnAddUslIP")
        except:
            print("Ошибка: элемент #ctl00_cph_UslSogl_btnAddUslIP не найден или недоступен")
            raise Exception("Отсутствует кнопка добавления услуг ИП")
        
        # Проверяем наличие и кликаем по кнопке сохранения и выхода
        try:
            page.wait_for_selector("#ctl00_cph_UslSogl_TopStr4_lbtnTopStr_SaveExit", timeout=5000)
            page.click("#ctl00_cph_UslSogl_TopStr4_lbtnTopStr_SaveExit")
        except:
            print("Ошибка: элемент #ctl00_cph_UslSogl_TopStr4_lbtnTopStr_SaveExit не найден или недоступен")
            raise Exception("Отсутствует кнопка сохранения и выхода")
        
        print(f"Договор {number_doc} был заполнен")
        
        # Ждем немного, чтобы убедиться, что страница корректно закрыта
        page.wait_for_timeout(100)
        
        return page

def comparing_dates(date1, date2):
        # Сравниваем месяцы и годы
    if date1.month == date2.month and date1.year == date2.year:
        result = 1  # Даты относятся к одному месяцу
    else:
        result = 2  # Даты относятся к разным месяцам
    return result

def select_date(page: Page): #Ввод даты и месяца
    if page:
        global start_obsl
        global data_month
        global day_of_month, new_day_of_month
        global month
        global expiration_date

        select_month = month.lower()
        select_data_month = data_month
        new_day_of_month = day_of_month

        #Ждем поля ввода даты
        page.click('a#ctl00_cph_lbtnTabReshen')
        page.wait_for_selector("#igtxtctl00_cph_grZayvView_ctl02_wdDatStart")

        #Выясняем первый или последующий сейчас месяц обслуживания.
        #Потом будем делать по другому
        date_text = page.get_attribute('#igtxtctl00_cph_grZayvView_ctl02_wdDatBegin','value')
        date1 = datetime.strptime(date_text, '%d.%m.%Y') 
        date2 = datetime.strptime(select_data_month, '%d.%m.%Y') 

        # Сравниваем месяцы и годы
        start_obsl = comparing_dates(date1,date2)
        #Если не полный месяц, меняем дату окончания
        element = page.query_selector('span#ctl00_cph_grZayvView_ctl02_lbPrekrInfo')
        if element:
            text = element.inner_text()
            # Регулярное выражение для поиска даты
            date_pattern = r'\b\d{2}\.\d{2}\.\d{4}\b'
            match = re.search(date_pattern, text)
            if match:
                date1 = datetime.strptime(match.group(0), '%d.%m.%Y')
                result = comparing_dates(date1,date2)
                if result == 1: 
                    select_data_month = match.group(0)
                    new_day_of_month = str(date1.day)
        
        # Ищем последнюю заполненую дату, если она равно дате конца, пропускаем
        span_element = page.wait_for_selector("#ctl00_cph_grZayvView_ctl02_divLastDatn")

        # Проверяем, есть ли содержимое внутри span
        if span_element.is_visible() and span_element.text_content().strip():
            full_text = span_element.text_content().strip().lower()
            
            # Ищем дату в формате DD.MM.YYYY (например, 31.01.2025)
            date_match = re.search(r':([а-я]+ \d{4})', full_text)
            
            if date_match:
                result = date_match.group(1)
                if result == select_month:
                    print("У заявления уже были начисления в этом месяце") 
                    return page, False

        print("Ввод месяца и даты")
        print(f"Указываем дату окончания как {select_data_month}")

        expiration_date = select_data_month
    
        page.fill('#igtxtctl00_cph_grZayvView_ctl02_wdDatStart', month)
        page.fill('#igtxtctl00_cph_grZayvView_ctl02_wdtDatn', select_data_month)
        page.click('#ctl00_cph_grZayvView_ctl02_lbtnEditFaktUsl')

        #если вдруг будет вспылвающее окно после нажатия на карандашик! Но не должно быть
        #found_windows = page.query_selector('#ctl00_mBody > div.ui-dialog.ui-corner-all.ui-widget.ui-widget-content.ui-front.ui-dialog-buttons.ui-draggable.ui-resizable')
        #if found_windows:
        #    page.click("#ctl00_mBody > div.ui-dialog.ui-corner-all.ui-widget.ui-widget-content.ui-front.ui-dialog-buttons.ui-draggable.ui-resizable > div.ui-dialog-buttonpane.ui-widget-content.ui-helper-clearfix > div > button")
        
        print("Переход на страницу с заполнением")
        
        # Проверяем, что страница не закрыта и элемент существует
        # Используем более надежный способ проверки наличия элемента
        try:
            # Ждем появления элемента с таймаутом 10 секунд
            page.wait_for_selector('#ctl00_cph_UF1_btnChangeGridToTabel', timeout=10000)
            
            # Получаем все строки, которые не являются заголовками
            print("Поиск таблицы")
            rows = page.query_selector_all('#ctl00_cph_UF1_pnlUslFakt > table > tbody > tr:not(.RS_GridHeader2)')
            if len(rows) > 0:
                print("Таблица найдена!")
            else:
                print("Таблица не найдена, заполняем")
                
                # Проверяем существование элемента перед кликом
                try:
                    page.wait_for_selector('#ctl00_cph_UF1_btnlbtnHeaderAddUsl', timeout=5000)
                    page.click('#ctl00_cph_UF1_btnlbtnHeaderAddUsl')
                except:
                    print("Элемент #ctl00_cph_UF1_btnlbtnHeaderAddUsl не найден или недоступен")
            
            # Нажимаем на кнопку
            page.click('#ctl00_cph_UF1_btnChangeGridToTabel')

            # Ожидаем появления кнопки "Ок" и нажимаем на неё, если она появилась

            # Ждём появления кнопки с таймаутом 5 секунд
            start_time = time.time()
            button = None
            
            while time.time() - start_time < 5:  # 5 секунд
                button = page.query_selector("#ctl00_mBody > div.ui-dialog.ui-corner-all.ui-widget.ui-widget-content.ui-front.ui-dialog-buttons.ui-draggable.ui-resizable > div.ui-dialog-buttonpane.ui-widget-content.ui-helper-clearfix > div > button")
                if button:#ctl00_mBody > div.ui-dialog.ui-corner-all.ui-widget.ui-widget-content.ui-front.ui-dialog-buttons.ui-draggable.ui-resizable > div.ui-dialog-buttonpane.ui-widget-content.ui-helper-clearfix > div > button
                    break
                time.sleep(0.5)  # Проверяем каждые 0.5 секунды

            if button:
                button.click()
                print("Кнопка 'Ок' появилась. Нажата.")
            else:
                print("Кнопка 'Ок' не появилась. Продолжаем выполнение.")
            
            # После клика по кнопке изменения таблицы нужно немного подождать, чтобы страница обновилась
            page.wait_for_timeout(2000)
        except:
            print("Элемент ctl00_cph_UF1_btnChangeGridToTabel для перехода на страницу с заполнением не найден. Пропускаем шаг.")
            return page, False


        #try:
        #    # Ждём появления кнопки с классом "ui-corner-all asp-button small"
        #    button = page.wait_for_selector("button.ui-corner-all.asp-button.small", timeout=5000)  # timeout в миллисекундах
        #    if button:
        #except:
        #    # Если кнопка не появилась, продолжаем выполнение
        #    print("Кнопка 'Ок' не появилась. Продолжаем выполнение.")

        return page, True

def edit_page(page: Page, start_date): #Редактирование таблицы фактическими услугами
    if page:
        global new_day_of_month, expiration_date

        # Процесс заполнения таблицы
        print("Началось заполнение страницы")

        # Нахождение таблицы с классом RS_Grid2
        page.wait_for_selector(".RS_Grid2")
        grid_table = page.query_selector_all(".RS_Grid2")

        if grid_table:
            # Нахождение всех строк в таблице
            table_rows = grid_table[0].query_selector_all("tbody > tr")

            # Словарь для хранения индексов колонок
            column_indices = {}

            # Первый проход по таблице для поиска заголовков
            first_row = table_rows[0]
            headers = first_row.query_selector_all("th.RS_GridHeader2")

            # Цикл для поиска колонок
            for idx, header in enumerate(headers):
                text = header.inner_text().strip().lower()  # Приводим текст к нижнему регистру
                if "социальные услуги" in text:
                    column_indices["социальные услуги"] = idx + 1
                elif new_day_of_month in text:
                    column_indices[new_day_of_month] = idx + 1
                elif "ип" in text:
                    column_indices["ип"] = idx + 1

            # Проверка, найдены ли обе колонки
            if "ип" in column_indices:
                    
                # Вывод всех строк не включая заголовки
                body_rows = grid_table[0].query_selector_all("tbody > tr[class]")
                    
                for row in body_rows:
                    soc = row.query_selector(f"td:nth-of-type({column_indices['социальные услуги']})")
                    input = row.query_selector(f"td:nth-of-type({column_indices[new_day_of_month]})")
                    ip = row.query_selector(f"td:nth-of-type({column_indices['ип']})")

                    # Поиск в услугах значений ИП
                    soc_text = soc.inner_text().strip()
                    match = re.search(r"\(ИП\)(\d+),", soc_text)
                    soc_number = int(match.group(1))  # Преобразуем в число

                    # Перевод значений ИП в число
                    ip_text = ip.inner_text().strip()
                    match2 = re.search(r"\d+", ip_text.replace(",", "."))

                    if ip_text == '': #Заполняем ИП если нету и перезапускаем
                        page.click("#ctl00_cph_UF1_TopStr5_lbtnTopStr_Exit")
                        page.click("#ctl00_cph_grZayvView_ctl02_lbtnEditSoglUsl")
                        page.click("#ctl00_cph_UslSogl_btnAddUslIP")

                        page.wait_for_selector("#ctl00_cph_UslSogl_grUslSoglView")
                        page.click("#ctl00_cph_UslSogl_TopStr4_lbtnTopStr_SaveExit")
                        return page, True

                    ip_number = int(match2.group(0))  # Преобразуем в число

                    # Вызов функции process_numbers
                    try:
                        result = process_numbers(soc_number, ip_number, start_date)
                            
                        # Ищем элемент <input type="text"> внутри переданного элемента
                        #text_input = input.query_selector("input[type='text']")
                        text_inputs = input.query_selector_all("input")
                        for text_input in text_inputs:
                            input_id = text_input.get_attribute("id")

                            # Вставляем переменные напрямую в JavaScript-код
                            js_code = f"""
                                const escapedId = CSS.escape("{input_id}");
                                const inputElement = document.querySelector(`#${{escapedId}}`);
                                inputElement.value = {result};
                            """

                            # Выполняем JavaScript на странице
                            page.evaluate(js_code)

                    except ValueError as e:
                        raise Exception(f"Ошибка: {e}")
                        
                print("Страница заполнена")

        else:
            print("Таблица для заполнения не найдена")

        # Временное сохранение страницы
        # Ждём появления кнопки с таймаутом 5 секунд
        start_time = time.time()
        save_button = None
        
        while time.time() - start_time < 5:  # 5 секунд
            save_button = page.query_selector("a#ctl00_cph_UF1_TopStr5_lbtnTopStr_Save")
            if save_button:
                break
            time.sleep(0.5)  # Проверяем каждые 0.5 секунды

        if save_button:
            save_button.click()
            print("Ждем кнопку сохранить")

            # Ожидаем появления всплывающего окна и нажимаем "ОК", если оно появилось
            #try:
            #    # Ждём появления кнопки "ОК" в течение 3 секунд
            #    button = page.wait_for_selector("button.ui-corner-all.asp-button.small", timeout=3000)
            #    if button:
            #        button.click()
            #        print("Нажимаем ОК на всплывающей странице")
            #except:
            #    # Если кнопка не появилась, продолжаем выполнение
            #    print("Всплывающее окно не появилось.")

            start_time = time.time()
            button = None
            
            while time.time() - start_time < 3:  # 3 секунд
                button = page.query_selector("button.ui-corner-all.asp-button.small")
                if button:
                    break
                time.sleep(0.5)  # Проверяем каждые 0.5 секунды

            if button:
                button.click()
                print("Кнопка 'Ок' появилась. Нажата.")
            else:
                print("Кнопка 'Ок' не появилась. Продолжаем выполнение.")
        else:
            print("Кнопка сохранения не появилась. Продолжаем выполнение.")

        # Сохранение и выход
        # Ждем появления элемента сохранения и кликаем по нему
        try:
            page.wait_for_selector("#ctl00_cph_UF1_TopStr5_lbtnTopStr_SaveExit", timeout=10000)
            page.click("#ctl00_cph_UF1_TopStr5_lbtnTopStr_SaveExit")
            print("Сохранение и выход")
        except:
            print("Элемент сохранения не найден, возможно страница уже изменилась")
        expiration_date = None #Сбрасываем дату окончания для след людей

        return page, None

def nach_page(page: Page):
    if page:
        global nach_year, nach_month
        page.click("td#ctl00_cph_tdTabNach")

        select_selector = '#ctl00_cph_ddlNachGod'
        page.select_option(select_selector, value=nach_year)
        print(f"Значение {nach_year} выбрано в разделе год")

        select_selector = '#ctl00_cph_ddlNach'
        page.select_option(select_selector, value=nach_month)
        print(f"Значение {nach_month} выбрано в разделе месяц")
        
        page.click("#ctl00_cph_lbAddNach442")
        print(f"Выбор процесса расчет активирован") 
        page.wait_for_selector('#ctl00_cph_pw_divNach > div.spPopup > table')
        page.click("#ctl00_cph_pw_divNach_ctl05_btnOk")
        print(f"Расчет запущен")

        # Проверяем, что страница не закрыта перед ожиданием элемента
        try:
            # Ждем появления таблицы расчета с таймаутом
            newtable = page.wait_for_selector('#ctl00_cph_USLRASH1_grRashView', timeout=30000)  # Увеличен таймаут до 30 секунд
            if newtable:
                print(f"Расчет окончен")
        
                # Ждем, пока элемент с суммой станет доступен
                element = page.wait_for_selector("#igtxtctl00_cph_USLRASH1_grRashView_ctl02_grRashView2_ctl02_wneSumTarIP3", timeout=10000)
                # Получаем значение атрибута title
                title_text = element.get_attribute("title")
                print(title_text)
        except:
            print("Элемент расчета не найден, возможно страница изменилась или закрылась")

        return page

def remove_middle_name(full_name):
    """
    Удаляет среднюю часть из 3-компонентного ФИО.
    """
    # Разбиваем строку на части
    parts = full_name.strip().split()
    
    # Если в ФИО 3 части, удаляем среднюю часть
    if len(parts) == 3:
        # Возвращаем фамилию и имя, удаляя отчество
        return f"{parts[0]} {parts[1]}"
    
    # Если это не 3-компонентное ФИО, возвращаем оригинальное имя
    return full_name
