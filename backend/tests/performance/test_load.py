import pytest
from locust import HttpUser, task, between
import subprocess
import psutil
from typing import Dict
import os

def test_system_resources():
    metrics = {
        'cpu': psutil.cpu_percent(),
        'memory': psutil.virtual_memory().percent,
        'disk': psutil.disk_usage(os.getcwd()[0:3]).percent  # Используем текущий диск
    }
    assert isinstance(metrics['cpu'], (int, float))
    assert isinstance(metrics['memory'], (int, float))
    assert isinstance(metrics['disk'], (int, float))

def pytest_addoption(parser):
    parser.addoption("--run-load", action="store_true", default=False)

@pytest.mark.skipif(
    not pytest.mark.skip(reason="use --run-load to run"),
    reason="Нагрузочные тесты пропущены"
)
def test_load_test():
    """Запуск нагрузочного тестирования"""
    locustfile_path = os.path.join(os.path.dirname(__file__), 'locustfile.py')
    cmd = [
        'locust',
        '-f', locustfile_path,  # Используем полный путь
        '--headless',
        '--users', '10',
        '--spawn-rate', '1',
        '--run-time', '30s',
        '--host', 'http://127.0.0.1:8000'
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=os.path.dirname(__file__)  # Устанавливаем рабочую директорию
    )