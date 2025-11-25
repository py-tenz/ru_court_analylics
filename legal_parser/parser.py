from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from functools import lru_cache

@lru_cache()
def get_all_docs(driver):
    link_list = []
    while True:
        try:
            # Ждём появления списка <ul> и всех элементов <li>
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "ul"))
            )
            list_el = driver.find_element(By.TAG_NAME, "ul")
            listed_els = list_el.find_elements(By.TAG_NAME, "li")

            for li in listed_els:
                try:
                    a_tag = li.find_element(By.TAG_NAME, "a")  # Находим тег <a> внутри <li>
                    href = a_tag.get_attribute("href")         # Получаем значение href
                    if href:                                   # Проверяем, что ссылка существует
                        link_list.append(href)                 # Добавляем ссылку в список
                except:
                    continue  

            # Проверяем наличие кнопки "Вперёд" для перехода на следующую страницу
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-tid="Paging__forwardLink"]'))
            )
            if next_button:
                next_button.click()
                WebDriverWait(driver, 10).until(
                    EC.staleness_of(next_button)  # Ждём, пока старая кнопка станет неактивной
                )
            else:
                break  # Если кнопка отсутствует, завершаем цикл
        except:
            break  # Если возникла ошибка (например, кнопка не найдена), завершаем цикл

    return link_list

driver = webdriver.Chrome()

# driver.get("https://normativ.kontur.ru/?query=%D0%98%D0%BD%D1%82%D0%B5%D0%BB%D0%BB%D0%B5%D0%BA%D1%82%D1%83%D0%B0%D0%BB%D1%8C%D0%BD%D0%BE%D0%B5+%D0%BF%D1%80%D0%B0%D0%B2%D0%BE&searching=true&sortby=1&searchquerysource=2&from=Search")

# all_links = get_all_docs(driver)

# print(len(all_links), all_links[-1])

# with open(file="links.txt", mode="w", encoding="utf-8") as f:
#     for i in all_links:
#         f.write(i + "\n")
# driver.quit()

def read_links(file_name="links.txt"):
    with open(file=file_name, mode='r', encoding="utf-8") as f:
        list_links = f.readlines()
        helper_list = []
        for i in list_links:
            helper_list.append(i[:-2])
        return helper_list

def parse_docs(urls_list):
    for i in range(len(urls_list)):
        driver.get(urls_list[i])
        try:
            driver.find_element(By.CSS_SELECTOR, '[data-status="Cancelled"]')
            continue
        except:
            elements = driver.find_elements(By.CLASS_NAME, "dt-p") #Забираем текст документов
            topheader = driver.find_elements(By.CSS_SELECTOR, '[data-wi="10"]') #Забираем заголовки статьи

            with open(file=f"documents\\doc_{i}.txt", mode="a", encoding="utf-8") as f:
                f.write(" ".join([header.text for header in topheader]) + "\n")
                for e in elements:
                    f.write(e.text.strip() + "\n")
    driver.quit()

parse_docs(read_links())
