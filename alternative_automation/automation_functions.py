from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re
import math
import pandas as pd
import time
import numpy as np
from workalendar.europe import Russia # для учета российских праздников
import config
from advanced_http_client import AdvancedWebAutomationClient

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

def find_child(client: AdvancedWebAutomationClient, child_name, status, start_date):
    """
    Поиск ребенка с использованием HTTP-клиента
    """
    # Выполняем поиск по ФИО
    response = client.search_child(child_name)
    
    # Анализируем HTML-ответ для нахождения карточки ребенка
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Найдем таблицу с классом RS_Grid2
    grid_table = soup.find("table", class_="RS_Grid2")
    
    if grid_table:
        # Нахождение всех строк в таблице
        table_rows = grid_table.find_all("tr")
        
        # Словарь для хранения индексов колонок
        column_indices = {}
        
        # Первый проход по таблице для поиска заголовков
        first_row = table_rows[0] if table_rows else None
        if first_row:
            headers = first_row.find_all("td", class_="RS_GridHeader2")
            
            # Цикл для поиска колонок "Поставщик" и "Дата"
            for idx, header in enumerate(headers):
                text = header.get_text().strip().lower()  # Приводим текст к нижнему регистру
                if "поставщик" in text:
                    column_indices["Поставщик"] = idx + 1
                elif "дата" in text:
                    column_indices["Дата"] = idx + 1
            
            # Проверка, найдены ли обе колонки
            if "Поставщик" in column_indices and "Дата" in column_indices:
                # Вывод всех строк не включая заголовки
                body_rows = grid_table.find_all("tr", class_=True)
                
                target_row = None
                latest_date = None
                for row in body_rows:
                    supplier_td = row.find("td", {"class": f"RS_GridCell2:nth-of-type({column_indices['Поставщик']})"})
                    date_td = row.find("td", {"class": f"RS_GridCell2:nth-of-type({column_indices['Дата']})"})
                    
                    # Если точное совпадение по классу не найдено, пробуем общий подход
                    all_tds = row.find_all("td")
                    if len(all_tds) >= max(column_indices.values()):
                        supplier_td = all_tds[column_indices["Поставщик"] - 1] if column_indices["Поставщик"] <= len(all_tds) else None
                        date_td = all_tds[column_indices["Дата"] - 1] if column_indices["Дата"] <= len(all_tds) else None
                    
                    date1 = start_date.strftime("%d.%m.%Y")
                    
                    if supplier_td and date_td:
                        supplier_text = supplier_td.get_text().strip()
                        date_text = date_td.get_text().strip()
                        
                        # Очистка строки от лишних символов
                        cleaned_data = date_text.replace('\xa0Р', '').strip()
                        try:
                            date_obj = datetime.strptime(cleaned_data.split()[0], '%d.%m.%Y')  # Преобразование строки в объект datetime.
                        except ValueError:
                            continue  # Пропускаем, если формат даты не распознан
                        
                        # Если дата в строке совпала с датой заявления, значит это оно, можно не искать дальше
                        if ((supplier_text == '' or 'АНО "Раскрой свой мир"' in supplier_text) and cleaned_data == date1):
                            target_row = row
                            print("Дата ИПР совпала с датой в exel. Пропускаем все и берем это заявление")
                            break
                    
                        # Поиск новых или старых в завимости их задачи
                        # Здесь мы не можем напрямую проверить видимость элементов как в Playwright,
                        # поэтому пропускаем эти проверки или заменяем на другие критерии
                        if (
                            ((supplier_text == '' or 'АНО "Раскрой свой мир"' in supplier_text) and status == 'new') or
                            ('АНО "Раскрой свой мир"' in supplier_text and status == 'old')
                        ):
                            # Если это первая подходящая строка или дата более поздняя
                            if latest_date is None or date_obj > latest_date:
                                latest_date = date_obj
                                target_row = row
                
                # Ищем ссылку редактирования и извлекаем URL
                if target_row:
                    edit_link = target_row.find('a', title="Просмотр и редактирование")
                    if edit_link:
                        id_value = edit_link.get('id')
                        card_url = f"{client.base_url}Common/CardDeclaration.aspx?id={id_value.split('_')[-1]}"
                        print(f"Найдена карточка ребенка: {card_url}")
                        return card_url
    
    print("Не найдена подходящая карточка пользователя")
    return None

def new_contract(client: AdvancedWebAutomationClient, card_url):
    """
    Создание нового договора
    """
    # Получаем страницу карточки
    response = client.get_child_card(card_url)
    
    # Извлекаем скрытые поля формы
    hidden_fields = client._extract_hidden_fields(response.text)
    
    # Подготовляем данные для формы
    form_data = {
        '__LASTFOCUS': '',
        '__EVENTTARGET': 'ctl00$cph$btnReshen',
        '__EVENTARGUMENT': '',
    }
    
    # Добавляем скрытые поля
    form_data.update(hidden_fields)
    
    # Обновляем данные на странице
    response = client.update_contract_data(card_url, form_data)
    
    # Теперь нужно выбрать нужные опции и сохранить
    response = client.get_child_card(card_url)
    hidden_fields = client._extract_hidden_fields(response.text)
    
    form_data = {
        '__LASTFOCUS': '',
        '__EVENTTARGET': 'ctl00$cph$pw_divReshen$ctl05$btnOk',
        '__EVENTARGUMENT': '',
        'ctl00$cph$pw_divReshen$divContent$rbl_Resh2': 'ctl00_cph_pw_divReshen_divContent_rbl_Resh2_0',  # Выбираем первый элемент
    }
    form_data.update(hidden_fields)
    
    response = client.update_contract_data(card_url, form_data)
    
    # Активируем чекбоксы
    response = client.get_child_card(card_url)
    hidden_fields = client._extract_hidden_fields(response.text)
    
    form_data = {
        '__LASTFOCUS': '',
        '__EVENTTARGET': 'ctl00$cph$Chk27000010002000101',
        '__EVENTARGUMENT': '',
        'ctl00$cph$Chk270001000200101': 'on',
    }
    form_data.update(hidden_fields)
    
    response = client.update_contract_data(card_url, form_data)
    
    # Клик по кнопке выхода
    response = client.get_child_card(card_url)
    hidden_fields = client._extract_hidden_fields(response.text)
    
    form_data = {
        '__LASTFOCUS': '',
        '__EVENTTARGET': 'ctl00$cph$Imagebutton_Exit',
        '__EVENTARGUMENT': '',
    }
    form_data.update(hidden_fields)
    
    response = client.update_contract_data(card_url, form_data)
    
    # Активируем второй чекбокс
    response = client.get_child_card(card_url)
    hidden_fields = client._extract_hidden_fields(response.text)
    
    form_data = {
        '__LASTFOCUS': '',
        '__EVENTTARGET': 'ctl00$cph$Chk2000',
        '__EVENTARGUMENT': '',
        'ctl00$cph$Chk2000': 'on',
    }
    form_data.update(hidden_fields)
    
    response = client.update_contract_data(card_url, form_data)
    
    # Клик по кнопке выхода
    response = client.get_child_card(card_url)
    hidden_fields = client._extract_hidden_fields(response.text)
    
    form_data = {
        '__LASTFOCUS': '',
        '__EVENTTARGET': 'ctl00$cph$Imagebutton_Exit',
        '__EVENTARGUMENT': '',
    }
    form_data.update(hidden_fields)
    
    response = client.update_contract_data(card_url, form_data)
    
    return client

def find_dogovor(client: AdvancedWebAutomationClient, card_url):
    """
    Поиск существующего договора
    """
    # Получаем страницу карточки
    response = client.get_child_card(card_url)
    
    # Анализируем HTML для поиска информации о договоре
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Ищем элемент, который указывает на наличие договора
    element = soup.find("span", {"id": "ctl00_cph_grZayvView_ctl02_tr_Rekv"})
    
    if element:
        # Ищем номер договора в выпадающем списке
        option_element = soup.find("option")
        if option_element:
            number_dogovor = option_element.get_text()
            # Извлекаем номер из строки вида "Описание №1234 от 01.01.2025"
            import re
            match = re.search(r'№([^" от]+)', number_dogovor)
            if match:
                extracted = match.group(1)
                return client, extracted
    
    return client, None

def new_dogovor(client: AdvancedWebAutomationClient, card_url, take_serv, number_doc):
    """
    Создание нового договора с заполнением данных
    """
    global start_month_datetime
    
    # Получаем текущую страницу для извлечения скрытых полей
    response = client.get_child_card(card_url)
    hidden_fields = client._extract_hidden_fields(response.text)
    
    # Преобразуем даты
    option_element = BeautifulSoup(response.text, 'html.parser').find("option")
    if option_element:
        option_text = option_element.get_text()
        cleaned_data = option_text.split('*')[0].strip()
        date1 = datetime.strptime(cleaned_data, '%d.%m.%Y')
        end_date = date1 + relativedelta(years=1) - relativedelta(days=1) # ИПР +год -1 день
        end_date = end_date.strftime("%d.%m.%Y")
        
        take_serv_as_dt = take_serv.to_pydatetime()
        # Выбираем бóльшую дату между date1 и take_serv, но не меньше февраля 2025
        new_date_dt = max(date1, take_serv_as_dt)  # Сначала берем позднюю из двух
        new_date_dt = max(new_date_dt, start_month_datetime)   # Но не раньше февраля 2025
        
        new_date = new_date_dt.strftime("%d.%m.%Y")
        take_serv_str = take_serv_as_dt.strftime("%d.%m.%Y")
        
        # Подготовка данных для формы
        form_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            'ctl00$cph$grZayvView$ctl02$wdtDatr': take_serv_str,
            'ctl00$cph$grZayvView$ctl02$wdDatBegin': new_date,
            'ctl00$cph$grZayvView$ctl02$wdDatEnd': end_date,
        }
        
        # Добавляем скрытые поля
        form_data.update(hidden_fields)
        
        # Обновляем данные на странице
        response = client.update_contract_data(card_url, form_data)
        
        # Далее нужно выполнить действия для добавления соглашения об услугах
        response = client.get_child_card(card_url)
        hidden_fields = client._extract_hidden_fields(response.text)
        
        form_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': 'ctl00$cph$grZayvView$ctl02$lbtnEditSoglUsl',
            '__EVENTARGUMENT': '',
        }
        form_data.update(hidden_fields)
        
        response = client.update_contract_data(card_url, form_data)
        
        # Добавляем новый договор
        response = client.get_child_card(card_url)
        hidden_fields = client._extract_hidden_fields(response.text)
        
        form_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': 'ctl00$cph$UslSogl$mnuAddDog',
            '__EVENTARGUMENT': '',
            'ctl00$cph$WDC_D_Date': new_date,
            'ctl00$cph$TB_D_Nomer': number_doc,
        }
        form_data.update(hidden_fields)
        
        response = client.update_contract_data(card_url, form_data)
        
        # Сохраняем
        response = client.get_child_card(card_url)
        hidden_fields = client._extract_hidden_fields(response.text)
        
        form_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': 'ctl00$cph$LB_Save',
            '__EVENTARGUMENT': '',
        }
        form_data.update(hidden_fields)
        
        response = client.update_contract_data(card_url, form_data)
        
        # Еще одно сохранение
        response = client.get_child_card(card_url)
        hidden_fields = client._extract_hidden_fields(response.text)
        
        form_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': 'ctl00$cph$LB_Save',
            '__EVENTARGUMENT': '',
        }
        form_data.update(hidden_fields)
        
        response = client.update_contract_data(card_url, form_data)
        
        # Выход с сохранением
        response = client.get_child_card(card_url)
        hidden_fields = client._extract_hidden_fields(response.text)
        
        form_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': 'ctl00$cph$LB_Exit_Save_No',
            '__EVENTARGUMENT': '',
        }
        form_data.update(hidden_fields)
        
        response = client.update_contract_data(card_url, form_data)
        
        # Добавляем услуги ИП
        response = client.get_child_card(card_url)
        hidden_fields = client._extract_hidden_fields(response.text)
        
        form_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': 'ctl00$cph$UslSogl$btnAddUslIP',
            '__EVENTARGUMENT': '',
        }
        form_data.update(hidden_fields)
        
        response = client.update_contract_data(card_url, form_data)
        
        # Сохраняем и выходим
        response = client.get_child_card(card_url)
        hidden_fields = client._extract_hidden_fields(response.text)
        
        form_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': 'ctl00$cph$UslSogl$TopStr4$lbtnTopStr_SaveExit',
            '__EVENTARGUMENT': '',
        }
        form_data.update(hidden_fields)
        
        response = client.update_contract_data(card_url, form_data)
        
        print(f"Договор {number_doc} был заполнен")
        return client

def comparing_dates(date1, date2):
    # Сравниваем месяцы и годы
    if date1.month == date2.month and date1.year == date2.year:
        result = 1  # Даты относятся к одному месяцу
    else:
        result = 2  # Даты относятся к разным месяцам
    return result

def select_date(client: AdvancedWebAutomationClient, card_url):
    """
    Выбор даты и месяца на странице
    """
    global start_obsl
    global data_month
    global day_of_month, new_day_of_month
    global month
    global expiration_date

    select_month = month.lower()
    select_data_month = data_month
    new_day_of_month = day_of_month

    # Получаем страницу карточки
    response = client.get_child_card(card_url)
    
    # Извлекаем скрытые поля формы
    hidden_fields = client._extract_hidden_fields(response.text)
    
    # Подготовка данных для формы
    form_data = {
        '__LASTFOCUS': '',
        '__EVENTTARGET': 'ctl00$cph$lbtnTabReshen',
        '__EVENTARGUMENT': '',
    }
    form_data.update(hidden_fields)
    
    # Обновляем данные на странице
    response = client.update_contract_data(card_url, form_data)
    
    # Теперь получаем текущее значение даты начала
    response = client.get_child_card(card_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    date_input = soup.find("input", {"id": "igtxtctl00_cph_grZayvView_ctl02_wdDatBegin"})
    if date_input:
        date_text = date_input.get("value", "")
        date1 = datetime.strptime(date_text, '%d.%m.%Y')
        date2 = datetime.strptime(select_data_month, '%d.%m.%Y')

        # Сравниваем месяцы и годы
        start_obsl = comparing_dates(date1, date2)
        
        # Проверяем, есть ли элемент с информацией о прекращении
        element = soup.find("span", {"id": "ctl00_cph_grZayvView_ctl02_lbPrekrInfo"})
        if element:
            text = element.get_text()
            # Регулярное выражение для поиска даты
            date_pattern = r'\b\d{2}\.\d{2}\.\d{4}\b'
            match = re.search(date_pattern, text)
            if match:
                date1 = datetime.strptime(match.group(0), '%d.%m.%Y')
                result = comparing_dates(date1, date2)
                if result == 1:
                    select_data_month = match.group(0)
                    new_day_of_month = str(date1.day)
        
        # Ищем последнюю заполненую дату
        last_date_element = soup.find("span", {"id": "ctl00_cph_grZayvView_ctl02_divLastDatn"})
        if last_date_element:
            full_text = last_date_element.get_text().strip().lower()
            
            # Ищем дату в формате DD.MM.YYYY (например, 31.01.2025)
            date_match = re.search(r':([а-я]+ \d{4})', full_text)
            
            if date_match:
                result = date_match.group(1)
                if result == select_month:
                    print("У заявления уже были начисления в этом месяце")
                    return client, False

        print("Ввод месяца и даты")
        print(f"Указываем дату окончания как {select_data_month}")

        expiration_date = select_data_month
        
        # Подготовка данных для заполнения дат
        hidden_fields = client._extract_hidden_fields(response.text)
        form_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            'ctl00$cph$grZayvView$ctl02$wdDatStart': month,
            'ctl00$cph$grZayvView$ctl02$wdtDatn': select_data_month,
        }
        form_data.update(hidden_fields)
        
        # Обновляем данные на странице
        response = client.update_contract_data(card_url, form_data)
        
        # Клик по кнопке редактирования
        hidden_fields = client._extract_hidden_fields(response.text)
        form_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': 'ctl00$cph$grZayvView$ctl02$lbtnEditFaktUsl',
            '__EVENTARGUMENT': '',
        }
        form_data.update(hidden_fields)
        
        response = client.update_contract_data(card_url, form_data)
        
        # Проверяем наличие таблицы
        response = client.get_child_card(card_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.find("table", {"id": "ctl00_cph_UF1_pnlUslFakt"})
        if not table:
            # Добавляем услуги если таблицы нет
            hidden_fields = client._extract_hidden_fields(response.text)
            form_data = {
                '__LASTFOCUS': '',
                '__EVENTTARGET': 'ctl00$cph$UF1$btnlbtnHeaderAddUsl',
                '__EVENTARGUMENT': '',
            }
            form_data.update(hidden_fields)
            
            response = client.update_contract_data(card_url, form_data)
        
        # Изменяем таблицу на табель
        hidden_fields = client._extract_hidden_fields(response.text)
        form_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': 'ctl00$cph$UF1$btnChangeGridToTabel',
            '__EVENTARGUMENT': '',
        }
        form_data.update(hidden_fields)
        
        response = client.update_contract_data(card_url, form_data)
        
        print("Переход на страницу с заполнением")
        
        return client, True
    
    return client, False

def edit_page(client: AdvancedWebAutomationClient, card_url, start_date):
    """
    Редактирование страницы с услугами
    """
    global new_day_of_month, expiration_date
    
    # Процесс заполнения таблицы
    print("Началось заполнение страницы")
    
    # Получаем страницу карточки
    response = client.get_child_card(card_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Нахождение таблицы с классом RS_Grid2
    grid_table = soup.find("table", class_="RS_Grid2")
    
    if grid_table:
        # Нахождение всех строк в таблице
        table_rows = grid_table.find_all("tr")
        
        # Словарь для хранения индексов колонок
        column_indices = {}
        
        # Первый проход по таблице для поиска заголовков
        first_row = table_rows[0] if table_rows else None
        if first_row:
            headers = first_row.find_all("th", class_="RS_GridHeader2")
            
            # Цикл для поиска колонок
            for idx, header in enumerate(headers):
                text = header.get_text().strip().lower()  # Приводим текст к нижнему регистру
                if "социальные услуги" in text:
                    column_indices["социальные услуги"] = idx + 1
                elif new_day_of_month in text:
                    column_indices[new_day_of_month] = idx + 1
                elif "ип" in text:
                    column_indices["ип"] = idx + 1
        
        # Проверка, найдены ли колонки
        if "ип" in column_indices:
            # Вывод всех строк не включая заголовки
            body_rows = grid_table.find_all("tr", class_=True)
            
            for row in body_rows:
                # Находим ячейки по индексам
                soc_index = column_indices.get("социальные услуги")
                day_index = column_indices.get(new_day_of_month)
                ip_index = column_indices.get("ип")
                
                all_tds = row.find_all("td")
                if len(all_tds) >= max(soc_index or 0, day_index or 0, ip_index or 0):
                    soc = all_tds[soc_index - 1] if soc_index and soc_index <= len(all_tds) else None
                    input_cell = all_tds[day_index - 1] if day_index and day_index <= len(all_tds) else None
                    ip = all_tds[ip_index - 1] if ip_index and ip_index <= len(all_tds) else None
                    
                    # Поиск в услугах значений ИП
                    if soc:
                        soc_text = soc.get_text().strip()
                        match = re.search(r"\(ИП\)(\d+),", soc_text)
                        if match:
                            soc_number = int(match.group(1))  # Преобразуем в число
                        else:
                            continue  # Пропускаем, если не найдено значение ИП в строке

                        # Перевод значений ИП в число
                        ip_text = ip.get_text().strip() if ip else ''
                        match2 = re.search(r"\d+", ip_text.replace(",", "."))
                        
                        if ip_text == '':  # Заполняем ИП если нету и перезапускаем
                            hidden_fields = client._extract_hidden_fields(response.text)
                            form_data = {
                                '__LASTFOCUS': '',
                                '__EVENTTARGET': 'ctl00$cph$UF1$TopStr5$lbtnTopStr_Exit',
                                '__EVENTARGUMENT': '',
                            }
                            form_data.update(hidden_fields)
                            
                            response = client.update_contract_data(card_url, form_data)
                            
                            hidden_fields = client._extract_hidden_fields(response.text)
                            form_data = {
                                '__LASTFOCUS': '',
                                '__EVENTTARGET': 'ctl00$cph$grZayvView$ctl02$lbtnEditSoglUsl',
                                '__EVENTARGUMENT': '',
                            }
                            form_data.update(hidden_fields)
                            
                            response = client.update_contract_data(card_url, form_data)
                            
                            hidden_fields = client._extract_hidden_fields(response.text)
                            form_data = {
                                '__LASTFOCUS': '',
                                '__EVENTTARGET': 'ctl00$cph$UslSogl$btnAddUslIP',
                                '__EVENTARGUMENT': '',
                            }
                            form_data.update(hidden_fields)
                            
                            response = client.update_contract_data(card_url, form_data)
                            
                            hidden_fields = client._extract_hidden_fields(response.text)
                            form_data = {
                                '__LASTFOCUS': '',
                                '__EVENTTARGET': 'ctl00$cph$UslSogl$TopStr4$lbtnTopStr_SaveExit',
                                '__EVENTARGUMENT': '',
                            }
                            form_data.update(hidden_fields)
                            
                            response = client.update_contract_data(card_url, form_data)
                            
                            return client, True
                        
                        if match2:
                            ip_number = int(match2.group(0))  # Преобразуем в число
                            
                            # Вызов функции process_numbers
                            try:
                                result = process_numbers(soc_number, ip_number, start_date)
                                
                                # Находим элемент input внутри ячейки
                                if input_cell:
                                    text_input = input_cell.find("input", type="text")
                                    if text_input:
                                        input_id = text_input.get("id")
                                        
                                        # Подготовим данные для обновления формы
                                        hidden_fields = client._extract_hidden_fields(response.text)
                                        form_data = {
                                            '__LASTFOCUS': '',
                                            '__EVENTTARGET': '',
                                            '__EVENTARGUMENT': '',
                                            input_id: result, # Используем ID элемента как ключ
                                        }
                                        form_data.update(hidden_fields)
                                        
                                        # Обновляем данные на странице
                                        response = client.update_contract_data(card_url, form_data)
                                        
                            except ValueError as e:
                                raise Exception(f"Ошибка: {e}")
                        
            print("Страница заполнена")
    else:
        print("Таблица для заполнения не найдена")
    
    # Временное сохранение страницы
    hidden_fields = client._extract_hidden_fields(response.text)
    form_data = {
        '__LASTFOCUS': '',
        '__EVENTTARGET': 'ctl00$cph$UF1$TopStr5$lbtnTopStr_Save',
        '__EVENTARGUMENT': '',
    }
    form_data.update(hidden_fields)
    
    response = client.update_contract_data(card_url, form_data)
    
    print("Ждем кнопку сохранить")
    
    # Сохранение и выход
    hidden_fields = client._extract_hidden_fields(response.text)
    form_data = {
        '__LASTFOCUS': '',
        '__EVENTTARGET': 'ctl00$cph$UF1$TopStr5$lbtnTopStr_SaveExit',
        '__EVENTARGUMENT': '',
    }
    form_data.update(hidden_fields)
    
    response = client.update_contract_data(card_url, form_data)
    print("Сохранение и выход")
    
    expiration_date = None  # Сбрасываем дату окончания для следующих людей
    
    return client, None

def nach_page(client: AdvancedWebAutomationClient, card_url):
    """
    Страница начислений
    """
    global nach_year, nach_month
    
    # Кликаем на вкладку начислений
    hidden_fields = client._extract_hidden_fields(client.get_child_card(card_url).text)
    form_data = {
        '__LASTFOCUS': '',
        '__EVENTTARGET': 'ctl00$cph$tdTabNach',
        '__EVENTARGUMENT': '',
    }
    form_data.update(hidden_fields)
    
    response = client.update_contract_data(card_url, form_data)
    
    # Выбираем год
    response = client.get_child_card(card_url)
    hidden_fields = client._extract_hidden_fields(response.text)
    form_data = {
        '__LASTFOCUS': '',
        '__EVENTTARGET': 'ctl00$cph$ddlNachGod',
        '__EVENTARGUMENT': '',
        'ctl00$cph$ddlNachGod': nach_year,
    }
    form_data.update(hidden_fields)
    
    response = client.update_contract_data(card_url, form_data)
    
    # Выбираем месяц
    response = client.get_child_card(card_url)
    hidden_fields = client._extract_hidden_fields(response.text)
    form_data = {
        '__LASTFOCUS': '',
        '__EVENTTARGET': 'ctl00$cph$ddlNach',
        '__EVENTARGUMENT': '',
        'ctl00$cph$ddlNach': nach_month,
    }
    form_data.update(hidden_fields)
    
    response = client.update_contract_data(card_url, form_data)
    
    # Активируем процесс расчета
    response = client.get_child_card(card_url)
    hidden_fields = client._extract_hidden_fields(response.text)
    form_data = {
        '__LASTFOCUS': '',
        '__EVENTTARGET': 'ctl00$cph$lbAddNach442',
        '__EVENTARGUMENT': '',
    }
    form_data.update(hidden_fields)
    
    response = client.update_contract_data(card_url, form_data)
    
    # Подтверждаем расчет
    response = client.get_child_card(card_url)
    hidden_fields = client._extract_hidden_fields(response.text)
    form_data = {
        '__LASTFOCUS': '',
        '__EVENTTARGET': 'ctl00$cph$pw_divNach_ctl05_btnOk',
        '__EVENTARGUMENT': '',
    }
    form_data.update(hidden_fields)
    
    response = client.update_contract_data(card_url, form_data)
    
    print(f"Расчет запущен")
    
    # Ждем завершения расчета и выводим результат
    response = client.get_child_card(card_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Находим элемент с суммой
    sum_element = soup.find("input", {"id": "igtxtctl00_cph_USLRASH1_grRashView_ctl02_grRashView2_ctl02_wneSumTarIP3"})
    if sum_element:
        title_text = sum_element.get("title")
        print(title_text)
    
    print(f"Расчет окончен")
    
    return client

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