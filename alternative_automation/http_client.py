import requests
import httpx
from urllib.parse import urljoin
import json
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

LOGIN = os.getenv("LOGIN")
PASSWORD = os.getenv("PASSWORD")

class WebAutomationClient:
    """
    Класс для автоматизации веб-задач без использования браузера
    """
    def __init__(self, base_url="http://localhost/aspnetkp/"):
        self.base_url = base_url
        self.session = requests.Session()
        self.csrf_token = None
        
    def login(self):
        """
        Авторизация на веб-сайте
        """
        # Сначала получаем страницу логина
        login_url = urljoin(self.base_url, "Account/Login.aspx")
        response = self.session.get(login_url)
        
        # Ищем возможные CSRF токены или скрытые поля формы
        # Это упрощенный пример - в реальности может потребоваться парсинг HTML
        
        # Отправляем данные авторизации
        login_data = {
            'tbUserName': LOGIN,
            'tbPassword': PASSWORD,
            # Дополнительные поля формы могут потребоваться
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': login_url,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Выполняем POST-запрос для входа
        login_post_url = urljoin(self.base_url, "Account/Login.aspx")
        response = self.session.post(login_post_url, data=login_data, headers=headers)
        
        # Проверяем успешность авторизации
        if response.status_code == 200:
            print("Успешная авторизация")
            return True
        else:
            print(f"Ошибка авторизации: {response.status_code}")
            return False
    
    def get_declaration_list(self, gsp=25):
        """
        Получение списка заявлений
        """
        url = urljoin(self.base_url, f"Common/ListDeclaration.aspx?GSP={gsp}")
        response = self.session.get(url)
        return response
    
    def search_child(self, child_name):
        """
        Поиск ребенка по ФИО
        """
        # URL для поиска в таблице
        search_url = urljoin(self.base_url, "Common/ListDeclaration.aspx?GSP=25")
        
        # Данные для поиска
        search_data = {
            'ctl00$cph$grdList$ctl01$ctrlFastFind$tbFind': child_name,
            'ctl00$cph$grdList$ctl01$ctrlFastFind$lbtnFastFind': 'Поиск'
        }
        
        response = self.session.post(search_url, data=search_data)
        return response
    
    def get_child_card(self, declaration_id):
        """
        Получение карточки ребенка по ID заявления
        """
        url = urljoin(self.base_url, f"Common/CardDeclaration.aspx?id={declaration_id}")
        response = self.session.get(url)
        return response
    
    def update_contract_data(self, form_data):
        """
        Обновление данных договора
        """
        url = urljoin(self.base_url, "Common/CardDeclaration.aspx")  # или другой URL в зависимости от контекста
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': url,
        }
        
        response = self.session.post(url, data=form_data, headers=headers)
        return response

# Пример использования
if __name__ == "__main__":
    client = WebAutomationClient()
    
    if client.login():
        print("Выполняем операции после авторизации...")
        # Примеры вызовов
        # response = client.get_declaration_list()
        # response = client.search_child("Иванов Иван")
        # response = client.get_child_card(123)
    else:
        print("Не удалось авторизоваться")