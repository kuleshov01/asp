from playwright.sync_api import sync_playwright

# Ваши учетные данные
LOGIN = "SAV"
PASSWORD = "08082022"
BASE = " Социальное обслуживание"

with sync_playwright() as p:
    # Запуск браузера
    browser = p.chromium.launch(headless=False)  # headless=False для видимого браузера
    page = browser.new_page()

    # Переход на страницу авторизации
    page.goto("http://localhost/aspnetkp/Login.aspx")  # Замените на URL страницы авторизации

    # Ожидание появления поля логина
    page.wait_for_selector('#tbUserName')

    # Заполнение логина
    page.fill('#tbUserName', LOGIN)

    # Заполнение пароля
    page.fill('#tbPassword', PASSWORD)

    # Нажатие на контейнер, чтобы открыть выпадающий список
    page.click('#baseListContainer')

    # Ожидание появления выпадающего списка
    page.wait_for_selector('.dropdown')  # Убедитесь, что это правильный селектор для выпадающего списка

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
    page.wait_for_selector('#ctl00_cph_rptRightMenu_ctl01_lbtnMenuItem')  # Замените на реальный селектор
    
    page.click('#ctl00_cph_rptRightMenu_ctl01_lbtnMenuItem')
    
    page.wait_for_selector('#ctl00_cph_grdList_ctl01_ctrlFastFind_tbFind')  # Замените на реальный селектор
    
    #Вводим ребенка и включаем поиск
    page.fill('#ctl00_cph_grdList_ctl01_ctrlFastFind_tbFind', 'Мамедрзаева Элиза')
    
    page.click('#ctl00_cph_grdList_ctl01_ctrlFastFind_lbtnFastFind')

    # Закрытие браузера
    #browser.close()