from playwright.sync_api import sync_playwright
import os
import json

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
    #context = browser.new_context()

    # Загрузим сессию, если она существует
    #if os.path.exists("session.json"):
    #    context = load_session(context)

    if os.path.exists(SESSION_FILE):
        # Если сессия сохранена, загружаем её
        context = browser.new_context(storage_state=SESSION_FILE)
        print("Используем сохраненную сессию.")
    else:
        # Если сессия не сохранена, создаем новый контекст
        context = browser.new_context()
        print("Создаем новую сессию.")

    page = context.new_page()

    # Переход на целевую страницу
    page.goto("http://localhost/aspnetkp/Common/ListDeclaration.aspx?GSP=25")

    try:
        # Попытаемся дождаться появления элемента на целевой странице
        page.wait_for_selector('#ctl00_cph_grdList_ctl01_ctrlFastFind_tbFind', timeout=3000)
    except Exception as e:
        # Если элемент не появился, возможно, нас перенаправило на страницу авторизации
        print("Не удалось найти элемент на целевой странице, вероятно, произошла переадресация на страницу авторизации.")
        try_authorization(page)

    # Продолжаем работу на целевой странице
    page.fill('#ctl00_cph_grdList_ctl01_ctrlFastFind_tbFind', 'Мамедрзаева Элиза')
    page.click('#ctl00_cph_grdList_ctl01_ctrlFastFind_lbtnFastFind')

    # Закрытие браузера
    #browser.close()