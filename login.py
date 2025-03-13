from playwright.sync_api import sync_playwright
import os
import json

# Ваши учетные данные
LOGIN = "SAV"
PASSWORD = "08082022"

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
        context.add_cookies(cookies)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()

    # Загрузим сессию, если она существует
    load_session(context)

    page = context.new_page()

    # Переход на страницу авторизации
    page.goto("http://localhost/aspnetkp/Login.aspx")

    # Проверим, авторизовались ли мы автоматически благодаря загруженным cookies
    if not page.url == "http://localhost/aspnetkp/default.aspx":
        # Если не авторизованы, выполняем процесс авторизации вручную
        # Ожидание появления поля логина
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
        page.wait_for_selector('#ctl00_cph_rptRightMenu_ctl01_lbtnMenuItem')

        # Сохраняем сессию после успешной авторизации
        save_session(page)

    # Продолжаем работу на сайте
    page.click('#ctl00_cph_rptRightMenu_ctl01_lbtnMenuItem')
    
    page.wait_for_selector('#ctl00_cph_grdList_ctl01_ctrlFastFind_tbFind')
    
    #Вводим ребенка и включаем поиск
    page.fill('#ctl00_cph_grdList_ctl01_ctrlFastFind_tbFind', 'Мамедрзаева Элиза')
    
    page.click('#ctl00_cph_grdList_ctl01_ctrlFastFind_lbtnFastFind')

    # Закрытие браузера
    #browser.close()