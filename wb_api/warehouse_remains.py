"""
Модуль для работы с API остатков товаров Wildberries
Адаптировано из Google Colab для работы в Cursor
"""

import requests
import time
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Импортируем все переменные из api-keys (динамический абсолютный путь)
BASE_DIR = Path(__file__).resolve().parents[1]
api_keys_path = BASE_DIR / 'api_keys.py'
import importlib.util
spec = importlib.util.spec_from_file_location("api_keys", str(api_keys_path))
api_keys_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_keys_module)
API_KEY = api_keys_module.WB_API_TOKEN


class WildberriesWarehouseAPI:
    """Класс для работы с API остатков товаров Wildberries"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://seller-analytics-api.wildberries.ru/api/v1/warehouse_remains"
        self.headers = {"Authorization": api_key}
        self.locale = "ru"
    
    def create_report(self) -> Optional[str]:
        """
        Создает отчет об остатках товаров
        
        Returns:
            str: Task ID для отслеживания статуса отчета или None в случае ошибки
        """
        print("🔄 Создаем отчет об остатках товаров...")
        
        # Параметры отчета
        params = {
            "locale": self.locale,
            "groupByBrand": False,
            "groupBySubject": False,
            "groupBySa": True,       # включаем артикул продавца (vendorCode)
            "groupByNm": True,       # разбиение по артикулам WB
            "groupByBarcode": True,  # включаем штрихкоды
            "groupBySize": False,
            "filterPics": 0,
            "filterVolume": 0
        }
        
        try:
            response = requests.get(self.base_url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                task_id = data.get("data", {}).get("taskId")
                
                if task_id:
                    print(f"✅ Отчёт создан! Task ID: {task_id}")
                    print("Теперь можно проверять статус и получать отчёт по этому Task ID.")
                    return task_id
                else:
                    print("❌ Не удалось получить Task ID.")
                    return None
            else:
                print(f"❌ Ошибка {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка при создании отчета: {e}")
            return None
    
    def check_report_status(self, task_id: str) -> str:
        """
        Проверяет статус отчета
        
        Args:
            task_id: ID задачи для проверки
            
        Returns:
            str: Статус отчета
        """
        status_url = f"{self.base_url}/tasks/{task_id}/status"
        
        try:
            response = requests.get(status_url, headers=self.headers)
            
            if response.status_code != 200:
                raise Exception(f"Ошибка при проверке статуса: {response.status_code} - {response.text}")
            
            status_data = response.json().get("data", {})
            status = status_data.get("status")
            
            print(f"📊 Статус отчета: {status}")
            return status
            
        except Exception as e:
            print(f"❌ Ошибка при проверке статуса: {e}")
            return "error"
    
    def wait_for_report(self, task_id: str, max_wait_time: int = 300) -> bool:
        """
        Ожидает готовности отчета
        
        Args:
            task_id: ID задачи
            max_wait_time: Максимальное время ожидания в секундах
            
        Returns:
            bool: True если отчет готов, False если время истекло
        """
        print(f"⏳ Ожидаем готовности отчета (максимум {max_wait_time} сек)...")
        
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status = self.check_report_status(task_id)
            
            if status == "done":
                print("✅ Отчёт готов!")
                return True
            elif status == "error":
                print("❌ Ошибка при создании отчета")
                return False
            else:
                print(f"⚠️ Отчёт еще не готов. Текущий статус: '{status}'")
                print("⏳ Ждем 10 секунд...")
                time.sleep(10)
        
        print(f"⏰ Время ожидания истекло ({max_wait_time} сек)")
        return False
    
    def download_report(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Скачивает готовый отчет
        
        Args:
            task_id: ID задачи
            
        Returns:
            Dict: Данные отчета или None в случае ошибки
        """
        print("📥 Скачиваем отчет...")
        
        download_url = f"{self.base_url}/tasks/{task_id}/download"
        
        try:
            response = requests.get(download_url, headers=self.headers)
            
            if response.status_code == 200:
                report_data = response.json()
                print("✅ Отчёт успешно получен!")
                return report_data
            else:
                print(f"❌ Ошибка при скачивании отчёта: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Ошибка при скачивании отчета: {e}")
            return None
    
    def get_warehouse_remains(self, wait_for_completion: bool = True) -> Optional[Dict[str, Any]]:
        """
        Полный цикл: создание отчета, ожидание и скачивание
        
        Args:
            wait_for_completion: Ждать ли завершения отчета
            
        Returns:
            Dict: Данные отчета или None в случае ошибки
        """
        # 1. Создаем отчет
        task_id = self.create_report()
        if not task_id:
            return None
        
        if not wait_for_completion:
            print("⚠️ Отчет создан, но не ждем его завершения")
            return None
        
        # 2. Ждем готовности
        if not self.wait_for_report(task_id):
            return None
        
        # 3. Скачиваем отчет
        return self.download_report(task_id)


def main():
    """Основная функция для тестирования API"""
    print("🚀 Запуск тестирования API остатков Wildberries")
    print("=" * 50)
    
    # Создаем экземпляр API
    api = WildberriesWarehouseAPI(API_KEY)
    
    # Получаем данные об остатках
    report_data = api.get_warehouse_remains()
    
    if report_data:
        print("\n📊 Полученные данные:")
        print("=" * 30)
        
        # Выводим структуру данных
        if isinstance(report_data, dict):
            print(f"Ключи в данных: {list(report_data.keys())}")
            
            # Если есть данные об остатках
            if 'data' in report_data:
                data = report_data['data']
                print(f"Количество записей: {len(data) if isinstance(data, list) else 'N/A'}")
                
                # Показываем первые несколько записей
                if isinstance(data, list) and len(data) > 0:
                    print("\nПервая запись:")
                    for key, value in data[0].items():
                        print(f"  {key}: {value}")
        else:
            print(f"Тип данных: {type(report_data)}")
            print(f"Данные: {report_data}")
    else:
        print("❌ Не удалось получить данные об остатках")


if __name__ == "__main__":
    main()
