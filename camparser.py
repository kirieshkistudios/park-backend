from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import os
import time


def save_camera_frame(camera_id: str, url: str):
    # Настройка браузера
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--autoplay-policy=no-user-gesture-required")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        driver.get(url)

        # Ожидаем появление видео элемента
        video_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "video"))
        )

        # Пытаемся запустить видео через JavaScript
        driver.execute_script("""
            const video = arguments[0];
            video.muted = true;  // Отключаем звук для автовоспроизведения
            video.play().catch(() => {
                video.setAttribute('controls', '');
                video.play();
            });
        """, video_element)

        # Ждем когда видео начнет воспроизводиться (currentTime > 0)
        WebDriverWait(driver, 20).until(
            lambda d: d.execute_script("return arguments[0].currentTime > 0", video_element)
        )

        # Дополнительная задержка для стабилизации изображения
        time.sleep(1)

        # Создаем папку для снимков
        os.makedirs("camera_snapshots", exist_ok=True)
        screenshot_path = os.path.join("camera_snapshots", f"{camera_id}.png")

        # Делаем скриншот элемента
        video_element.screenshot(screenshot_path)
        print(f"Снимок сохранен: {screenshot_path}")
        return True

    except Exception as e:
        print(f"Ошибка для камеры {camera_id}: {str(e)}")
        return False

    finally:
        driver.quit()
        