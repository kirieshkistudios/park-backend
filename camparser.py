from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

# Настройки
URL = "https://sochi.camera/vse-kamery/dorogi/"
SAVE_INTERVAL = 5  # Интервал в секундах
OUTPUT_DIR = "z"

# Создаем папку для сохранения кадров
os.makedirs(OUTPUT_DIR, exist_ok=True)


def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-infobars")
    options.add_argument("--mute-audio")  # Отключаем звук
    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1280, 720)  # Опционально: задаем размер окна
    return driver


def capture_video_frames():
    driver = setup_driver()
    try:
        driver.get(URL)

        # Ждем, пока видео загрузится
        video_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "video"))
        )

        # Запускаем видео (если оно не autoplay)
        driver.execute_script("arguments[0].play();", video_element)

        frame_count = 0
        while True:
            # Делаем скриншот элемента <video>
            screenshot = video_element.screenshot_as_png

            # Сохраняем кадр
            timestamp = int(time.time())
            filename = os.path.join(OUTPUT_DIR, f"frame_{timestamp}.png")
            with open(filename, "wb") as f:
                f.write(screenshot)
            print(f"Кадр сохранен: {filename}")

            # Ждем указанный интервал
            time.sleep(SAVE_INTERVAL)

    except Exception as e:
        print(f"Ошибка: {str(e)}")
    finally:
        driver.quit()


if __name__ == "__main__":
    capture_video_frames()