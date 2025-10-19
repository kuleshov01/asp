import requests
from urllib.parse import urljoin, urlparse
import re
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

LOGIN = os.getenv("LOGIN")
PASSWORD = os.getenv("PASSWORD")

class AdvancedWebAutomationClient:
    """
    Расширенный класс для автоматизации веб-задач без использования браузера
    Учитывает особенности ASP.NET WebForms (ViewState, EventValidation и т.д.)
    """
    def __init__(self, base_url="http://localhost/aspnetkp/"):
        self.base_url = base_url
        self.session = requests.Session()
        self.last_response = None
        
        # Устанавливаем User-Agent для имитации реального браузера
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def _extract_hidden_fields(self, html_content):
        """
        Извлечение скрытых полей формы (ViewState, EventValidation и др.)
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        hidden_fields = {}
        
        for input_tag in soup.find_all('input', type='hidden'):
            name = input_tag.get('name')
            value = input_tag.get('value', '')
            if name:
                hidden_fields[name] = value
                
        return hidden_fields
    
    def login(self):
        """
        Авторизация на веб-сайте с учетом ASP.NET WebForms особенностей
        """
        login_url = urljoin(self.base_url, "Account/Login.aspx")
        
        # Получаем начальную страницу для извлечения скрытых полей
        response = self.session.get(login_url)
        self.last_response = response
        
        # Извлекаем скрытые поля формы
        hidden_fields = self._extract_hidden_fields(response.text)
        
        # Подготовляем данные для авторизации (заполняем логин и пароль)
        # В оригинальном коде сначала заполняются поля, затем кликается контейнер выбора базы,
        # потом выбирается "Социальное обслуживание" и наконец нажимается кнопка входа
        login_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            'tbUserName': LOGIN,
            'tbPassword': PASSWORD,
        }
        
        # Добавляем все скрытые поля к данным формы
        login_data.update(hidden_fields)
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': login_url,
        }
        
        # Отправляем данные для заполнения логина и пароля
        response = self.session.post(login_url, data=login_data, headers=headers)
        self.last_response = response
        
        # Извлекаем обновленные скрытые поля после заполнения логина/пароля
        hidden_fields = self._extract_hidden_fields(response.text)
        
        # Теперь симулируем клик по контейнеру выбора базы (baseListContainer)
        # В ASP.NET WebForms клики по элементам с определенными ID генерируют __EVENTTARGET
        base_container_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': 'baseListContainer',
            '__EVENTARGUMENT': '',
            'tbUserName': LOGIN,
            'tbPassword': PASSWORD,
        }
        base_container_data.update(hidden_fields)
        
        response = self.session.post(login_url, data=base_container_data, headers=headers)
        self.last_response = response
        
        # Извлекаем обновленные скрытые поля
        hidden_fields = self._extract_hidden_fields(response.text)
        
        # Теперь нужно выбрать "Социальное обслуживание" из выпадающего списка
        # В оригинальном коде используется XPath для поиска строки с текстом "Социальное обслуживание"
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем таблицу gvBases, в которой должны быть варианты баз
        bases_table = soup.find('table', id='gvBases')
        if bases_table:
            # Ищем строку, содержащую "Социальное обслуживание"
            soc_obsl_row = None
            for row in bases_table.find_all('tr'):
                if 'Социальное обслуживание' in row.get_text():
                    soc_obsl_row = row
                    break
            
            if soc_obsl_row:
                # В строке находим элемент, который нужно кликнуть
                # Обычно это ячейка или ссылка
                click_element = soc_obsl_row.find('td')
                if click_element:
                    # В реальных ASP.NET WebForms приложениях клик по строке таблицы
                    # может генерировать событие с определенным __EVENTTARGET
                    # Попробуем использовать общий подход
                    select_base_data = {
                        '__LASTFOCUS': '',
                        '__EVENTTARGET': 'gvBases',  # или может потребоваться конкретный ID элемента
                        '__EVENTARGUMENT': '',
                        'tbUserName': LOGIN,
                        'tbPassword': PASSWORD,
                    }
                    select_base_data.update(hidden_fields)
                    
                    response = self.session.post(login_url, data=select_base_data, headers=headers)
                    self.last_response = response
        
        # Извлекаем обновленные скрытые поля после выбора базы
        hidden_fields = self._extract_hidden_fields(response.text)
        
        # Наконец, нажимаем кнопку входа (lbtnLogin)
        login_button_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': 'lbtnLogin',
            '__EVENTARGUMENT': '',
            'tbUserName': LOGIN,
            'tbPassword': PASSWORD,
        }
        login_button_data.update(hidden_fields)
        
        response = self.session.post(login_url, data=login_button_data, headers=headers)
        self.last_response = response
        
        # Проверяем успешность авторизации
        if response.status_code != 200:
            print(f"Ошибка подключения: {response.status_code}")
            return False
        elif "Социальное обслуживание" in response.text or response.url.endswith("Default.aspx"):
            print("Успешная авторизация")
            return True
        else:
            print(f"Ошибка авторизации: Страница авторизации все еще отображается")
            return False
    
    def get_declaration_list(self, gsp=25):
        """
        Получение списка заявлений
        """
        url = urljoin(self.base_url, f"Common/ListDeclaration.aspx?GSP={gsp}")
        response = self.session.get(url)
        self.last_response = response
        return response
    
    def search_child(self, child_name):
        """
        Поиск ребенка по ФИО с учетом скрытых полей формы
        """
        search_url = urljoin(self.base_url, "Common/ListDeclaration.aspx?GSP=25")
        
        # Получаем текущую страницу для извлечения скрытых полей
        response = self.session.get(search_url)
        self.last_response = response
        hidden_fields = self._extract_hidden_fields(response.text)
        
        # Подготовляем данные для поиска
        search_data = {
            '__LASTFOCUS': '',
            '__EVENTTARGET': 'ctl00$cph$grdList$ctl01$ctrlFastFind$lbtnFastFind',
            '__EVENTARGUMENT': '',
            'ctl00$cph$grdList$ctl01$ctrlFastFind$tbFind': child_name,
        }
        
        # Добавляем все скрытые поля к данным формы
        search_data.update(hidden_fields)
        
        response = self.session.post(search_url, data=search_data)
        self.last_response = response
        return response
    
    def get_child_card(self, card_url):
        """
        Получение карточки ребенка по URL
        """
        response = self.session.get(card_url)
        self.last_response = response
        return response
    
    def update_contract_data(self, url, form_data):
        """
        Обновление данных договора с учетом скрытых полей
        """
        # Получаем текущую страницу для извлечения скрытых полей
        response = self.session.get(url)
        self.last_response = response
        hidden_fields = self._extract_hidden_fields(response.text)
        
        # Обновляем данные формы, добавляя скрытые поля
        form_data.update(hidden_fields)
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': url,
        }
        
        response = self.session.post(url, data=form_data, headers=headers)
        self.last_response = response
        return response

# Пример использования
if __name__ == "__main__":
    client = AdvancedWebAutomationClient()
    
    if client.login():
        print("Выполняем операции после авторизации...")
        # Примеры вызовов
        # response = client.get_declaration_list()
        # response = client.search_child("Иванов Иван")
        # response = client.get_child_card("Common/CardDeclaration.aspx?id=123")
    else:
        print("Не удалось авторизоваться")