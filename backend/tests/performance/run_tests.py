import subprocess
import time
import psutil
import logging
from typing import Dict
from config import PERFORMANCE_CONFIG

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('performance_tests.log'),
        logging.StreamHandler()
    ]
)

# Мониторинг использования ресурсов системы
def monitor_resources() -> Dict[str, float]:
    """
    Мониторинг использования ресурсов системы
    :return: Словарь с использованием ресурсов
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        'cpu': cpu_percent,
        'memory': memory.percent,
        'disk': disk.percent
    }

# Проверка превышения пороговых значений ресурсов
def check_resource_thresholds(metrics: Dict[str, float]) -> bool:
    """
    Проверка превышения пороговых значений ресурсов
    :param metrics: Словарь с использованием ресурсов
    :return: True, если пороговые значения не превышены, иначе False
    """
    thresholds = PERFORMANCE_CONFIG['monitoring']
    for resource, value in metrics.items():
        if value > thresholds[f'{resource}_threshold']:
            logging.warning(f"Превышен порог использования {resource}: {value}%")
            return False
    return True

# Запуск теста с помощью Locust
def run_locust_test(users: int, spawn_rate: int, duration: int):
    """
    Запуск теста с помощью Locust
    :param users: Количество пользователей
    :param spawn_rate: Скорость генерации пользователей
    :param duration: Длительность теста
    :return: True, если тест успешно завершен, иначе False
    """
    cmd = [
        'locust',
        '-f', 'locustfile.py',
        '--headless',
        '--users', str(users),
        '--spawn-rate', str(spawn_rate),
        '--run-time', f'{duration}s',
        '--host', 'http://127.0.0.1:8000'
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Мониторинг ресурсов во время теста
        while process.poll() is None:
            metrics = monitor_resources()
            if not check_resource_thresholds(metrics):
                process.terminate()
                logging.error("Тест остановлен из-за превышения пороговых значений ресурсов")
                return False
            
            time.sleep(5)
        
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            logging.error(f"Ошибка при выполнении теста: {stderr}")
            return False
            
        logging.info("Тест успешно завершен")
        return True
        
    except Exception as err:
        logging.error(f"Ошибка при запуске теста: {err}")
        return False

# Основная функция запуска тестов
def main():
    """
    Основная функция запуска тестов
    """
    config = PERFORMANCE_CONFIG

    print(config)
    
    # Запуск тестов с разным количеством пользователей
    for users in range(config['users']['min'], config['users']['max'] + 1, 10):
        logging.info(f"Запуск теста с {users} пользователями")
        
        # Короткий тест
        logging.info("Короткий тест (60 секунд)")
        if not run_locust_test(users, config['users']['spawn_rate'], config['duration']['short']):
            break
            
        # Средний тест
        logging.info("Средний тест (5 минут)")
        if not run_locust_test(users, config['users']['spawn_rate'], config['duration']['medium']):
            break
            
        # Длительный тест
        logging.info("Длительный тест (15 минут)")
        if not run_locust_test(users, config['users']['spawn_rate'], config['duration']['long']):
            break

if __name__ == "__main__":
    main() 