from playwright.sync_api import Page # type: ignore
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re
import math
import pandas as pd
import time

start_obsl = None
month = 'Февраль 2025'
data_month = '28.02.2025'
day_of_month = '28'
nach_year = "2025"
nach_month = "02.2025"

#month = 'Январь 2025'
#data_month = '31.01.2025'
#day_of_month = '31'
#nach_year = "2025"
#nach_month = "01.2025"

def process_numbers(plan, actual):
    if actual == 0:
        raise ValueError("Фактическое число не может быть равно нулю.")

    if plan == 84: 
        return 28
    
    rounded_plan = math.ceil(plan / 3)

    if rounded_plan >= actual:
        return actual
    else:
        if start_obsl > 1:
            rounded_plan = rounded_plan - 1
        return rounded_plan

def find_child(page: Page, status, start_obsl):
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

                    date1 = start_obsl.strftime("%d.%m.%Y")

                    if supplier and date:
                        supplier_text = supplier.inner_text().strip()
                        date_text = date.inner_text().strip()

                        # Очистка строки от лишних символов
                        cleaned_data = date_text.replace('\xa0Р', '').strip()
                        date = datetime.strptime(cleaned_data.split()[0], '%d.%m.%Y')  # Преобразование строки в объект datetime.
                        
                        #Если дата в строке совпала с датой заявления, значит это оно, можно не искать дальше
                        if ((supplier_text == '' or 'АНО "Раскрой свой мир"' in supplier_text)  and cleaned_data == date1):
                            target_row = row
                            break
                    
                        # Поиск новых или старых в завимости их задачи
                        if (
                            #(supplier_text == '' and status == 'new' and page.is_visible('img[title="Составлена ИП"]')) or
                            ((supplier_text == '' or 'АНО "Раскрой свой мир"' in supplier_text) and status == 'new' and page.is_visible('img[title="Составлена ИП"]')) or
                            ('АНО "Раскрой свой мир"' in supplier_text and status == 'old') or
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
    
def new_dogovor(page: Page, date2, number_doc):
    if page:

        page.click("#ctl00_cph_lbtnTabReshen")

        #Если уже договор заполен, то сбрасываем
        element = page.query_selector("#ctl00_cph_grZayvView_ctl02_tr_Rekv > td > span")
        if not element:

            option_text = page.locator("#ctl00_cph_ListData > option").inner_text() ###??? не помню что это и если его нет
            cleaned_data = option_text.split('*')[0].strip() 
            date1 = datetime.strptime(cleaned_data, '%d.%m.%Y')
            end_date = date1 + relativedelta(years=1) - relativedelta(days=1)
            end_date = end_date.strftime("%d.%m.%Y")

            if date1 < date2:
                new_date = date2.strftime("%d.%m.%Y")
            else: new_date = date1.strftime("%d.%m.%Y")

            page.fill("#igtxtctl00_cph_grZayvView_ctl02_wdtDatr", new_date)
            page.fill("#igtxtctl00_cph_grZayvView_ctl02_wdDatBegin", new_date)
            page.fill("#igtxtctl00_cph_grZayvView_ctl02_wdDatEnd", end_date)

            page.click("#ctl00_cph_grZayvView_ctl02_lbtnEditSoglUsl > img")
            page.click("#ctl00_cph_UslSogl_mnuAddDog > li > div > img")

            page.fill("#igtxtctl00_cph_WDC_D_Date", new_date)
            page.fill("#ctl00_cph_TB_D_Nomer", number_doc)
            page.click("#ctl00_cph_LB_Save")
            page.click("#ctl00_cph_LB_Exit_Save_No")
            page.click("#ctl00_cph_UslSogl_btnAddUslIP")
            page.click("#ctl00_cph_UslSogl_TopStr4_lbtnTopStr_SaveExit")
            return page, None
        else:
            number_dogovor = page.locator("#ctl00_cph_grZayvView_ctl02_ListDogovor > option").inner_text()
            extracted = number_dogovor.split("№")[1].split(" от ")[0] 
            return page, extracted


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
        global day_of_month
        global month

        select_month = month.lower()
        select_data_month = data_month

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
                    day_of_month = str(date1.day)
        
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
                    print("Заявление уже было заполнено") 
                    return page, False

        print("Ввод месяца и даты")
        print(f"Указываем дату окончания как {select_data_month}")
    
        page.fill('#igtxtctl00_cph_grZayvView_ctl02_wdDatStart', month)
        page.fill('#igtxtctl00_cph_grZayvView_ctl02_wdtDatn', select_data_month)
        page.click('#ctl00_cph_grZayvView_ctl02_lbtnEditFaktUsl')

        #если вдруг будет вспылвающее окно после нажатия на карандашик! Но не должно быть
        #found_windows = page.query_selector('#ctl00_mBody > div.ui-dialog.ui-corner-all.ui-widget.ui-widget-content.ui-front.ui-dialog-buttons.ui-draggable.ui-resizable')
        #if found_windows:
        #    page.click("#ctl00_mBody > div.ui-dialog.ui-corner-all.ui-widget.ui-widget-content.ui-front.ui-dialog-buttons.ui-draggable.ui-resizable > div.ui-dialog-buttonpane.ui-widget-content.ui-helper-clearfix > div > button")
        
        print("Переход на страницу с заполнением")
        page.wait_for_selector('#ctl00_cph_UF1_btnChangeGridToTabel')
        # Получаем все строки, которые не являются заголовками

        print("Поиск таблицы")
        rows = page.query_selector_all('#ctl00_cph_UF1_pnlUslFakt > table > tbody > tr:not(.RS_GridHeader2)')
        if len(rows) > 0:
            print("Таблица найдена!")
        else:
            print("Таблица не найдена, заполняем")
            
            # Пытаемся дождаться элемента и кликнуть по нему
            page.wait_for_selector('#ctl00_cph_UF1_btnlbtnHeaderAddUsl')
            page.click('#ctl00_cph_UF1_btnlbtnHeaderAddUsl')
        
        # Нажимаем на кнопку
        page.click('#ctl00_cph_UF1_btnChangeGridToTabel')

        # Ожидаем появления кнопки "Ок" и нажимаем на неё, если она появилась

        # Ждём появления кнопки с таймаутом 5 секунд
        start_time = time.time()
        button = None
        
        while time.time() - start_time < 5:  # 5 секунд
            button = page.query_selector("button.ui-corner-all.asp-button.small")
            if button:
                break
            time.sleep(0.5)  # Проверяем каждые 0.5 секунды

        if button:
            button.click()
            print("Кнопка 'Ок' появилась. Нажата.")
        else:
            print("Кнопка 'Ок' не появилась. Продолжаем выполнение.")


        #try:
        #    # Ждём появления кнопки с классом "ui-corner-all asp-button small"
        #    button = page.wait_for_selector("button.ui-corner-all.asp-button.small", timeout=5000)  # timeout в миллисекундах
        #    if button:
        #except:
        #    # Если кнопка не появилась, продолжаем выполнение
        #    print("Кнопка 'Ок' не появилась. Продолжаем выполнение.")

        return page, True

def edit_page(page: Page): #Редактирование таблицы фактическими услугами
    if page:
        global day_of_month

        for i in range(2):
            # Если открылся со 2 страницы, возвращаем обратно
            prev_page = page.query_selector('a[title="Перейти на предыдущую страницу"]')
            if prev_page and i == 0:
                id_value = prev_page.get_attribute('id')
                disabled = prev_page.get_attribute('disabled')
                if disabled is None:
                    page.click(f'#{id_value}')
                    print("Откатились на первую страницу")

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
                    elif day_of_month in text:
                        column_indices[day_of_month] = idx + 1
                    elif "ип" in text:
                        column_indices["ип"] = idx + 1

                # Проверка, найдены ли обе колонки
                if "ип" in column_indices:
                        
                    # Вывод всех строк не включая заголовки
                    body_rows = grid_table[0].query_selector_all("tbody > tr[class]")
                        
                    for row in body_rows:
                        soc = row.query_selector(f"td:nth-of-type({column_indices['социальные услуги']})")
                        input = row.query_selector(f"td:nth-of-type({column_indices[day_of_month]})")
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
                            result = process_numbers(soc_number, ip_number)
                                
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
                            print(f"Ошибка: {e}")
                            
                    print("Страница заполнена")

            else:
                print("Таблица для заполнения не найдена")

            # Временное сохранение страницы
            page.click("a#ctl00_cph_UF1_TopStr5_lbtnTopStr_Save")
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

            # Переходим на следующую страницу
            next_page = page.query_selector('a[title="Перейти на следующую страницу"]')
            if next_page and i == 0:
                id_value = next_page.get_attribute('id')
                page.click(f'#{id_value}')
                print(f"Переход на следующую страницу")

            #page.wait_for_timeout(3000)

        # Сохранение и выход
        page.click("#ctl00_cph_UF1_TopStr5_lbtnTopStr_SaveExit")
        print("Сохранение и выход")

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

        newtable = page.wait_for_selector('#ctl00_cph_USLRASH1_grRashView', timeout=3000)
        if newtable:
            print(f"Расчет окончен") 

            # Получаем сумму оказаных услуг
            element = page.locator("#igtxtctl00_cph_USLRASH1_grRashView_ctl02_grRashView2_ctl02_wneSumTarIP3")
            # Получаем значение атрибута title
            title_text = element.get_attribute("title")
            print(title_text)

        return page

