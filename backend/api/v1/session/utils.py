# backend/api/v1/session/utils.py - Получение информации о браузере, устройстве и геолокации

from typing import  Optional
from fastapi import Request
import aiohttp

from api.v1.session.schemas import UserAgentInfo
from core.extensions.logger import logger

class SessionUtils:
    """
    Класс для работы с сессиями пользователей

    Методы:
        - `parse_user_agent` - Метод для парсинга `User-Agent` для получения информации о браузере и устройстве (без поля location, ip_address)
        - `get_client_ip` - Метод для получения IP-адреса клиента
        - `get_location_by_ip` - Метод для получения геолокации по IP-адресу
        - `user_agent_info` - Метод для парсинга User-Agent для получения информации о браузере, устройстве и геолокации
    """

    def __init__(self):
        self.browser_map = {
            "Firefox": "Mozilla Firefox",
            "YaBrowser": "Yandex",
            "Chrome": "Google Chrome",
            "Safari": "Safari",
            "Edge": "Microsoft Edge",
            "Opera": "Opera",
            "MSIE": "Internet Explorer",
            "Trident": "Internet Explorer"
        }

        self.os_map = {
            "Windows": "Windows",
            "Mac OS": "MacOS",
            "Linux": "Linux",
            "Android": "Android",
            "iOS": "iOS"
        }

        self.platform_map = {
            "Mobile": "Мобильный",
            "Tablet": "Планшет",
            "iPad":   "Планшет",
        }

        self.device_map = {
            "iPhone":    "iPhone",
            "iPad":      "iPad",
            "SM-":       "Samsung Galaxy",
            "Pixel":     "Google Pixel",
            "OnePlus":   "OnePlus",
            "Macintosh": "Mac",
        }

        self.geo_api_url = "http://ip-api.com/json/{ip}?lang=ru"
        self.geo_request_timeout = 2

    def parse_user_agent(self, user_agent: str) -> UserAgentInfo:
        """
        Парсинг User-Agent для получения информации о браузере и устройстве\n
        `user_agent` - `User-Agent` строка\n
        Возвращает информацию о браузере, устройстве, платформе и устройстве (без поля location, ip_address) в виде UserAgentInfo
        """

        browser = next((v for k, v in self.browser_map.items() if k in user_agent), "Нет данных")
        os = next((v for k, v in self.os_map.items() if k in user_agent), "Нет данных")
        platform = next((v for k, v in self.platform_map.items() if k in user_agent), "Десктоп")
        device = next((v for k, v in self.device_map.items() if k in user_agent), platform.capitalize())

        return UserAgentInfo(browser=browser, os=os, platform=platform, device=device, location="", ip_address="")

    def get_client_ip(self, request: Request) -> Optional[str]:
        """
        Читает заголовки X-Forwarded-For/X-Real-IP или берет request.client.host\n
        Возвращает IP-адрес клиента или None
        """
        # X-Forwarded-For
        xff = request.headers.get("X-Forwarded-For", "")
        if xff:
            for ip in [ip.strip() for ip in xff.split(",")]:
                if ip:
                    return ip

        # X-Real-IP
        xrip = request.headers.get("X-Real-IP", "")
        if xrip:
            return xrip.strip()
        
        client = request.client
        if client and client.host:
            return client.host

        return None
    
    async def get_location_by_ip(self, ip_address: str) -> str:
        """
        Получение геолокации по IP-адресу, делает запрос на внешний API\n
        `ip_address` - IP-адрес\n
        Возвращает строку с информацией о местоположении
        """
        if not ip_address or ip_address in ("127.0.0.1", "::1", "localhost"):
            return "Локальная сеть"

        url = self.geo_api_url.format(ip=ip_address)
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.geo_request_timeout)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        location_parts = [
                            data.get("city", ""),
                            data.get("regionName", ""),
                            data.get("country", "")
                        ]
                        location_parts = [part for part in location_parts if part and part != location_parts[0]]
                        return ", ".join(location_parts) if location_parts else "Неизвестное местоположение"
                    return "Неизвестное местоположение"
                
        except Exception as err:
            logger.error(f"Ошибка при получении геолокации: {err}")
        return "Неизвестное местоположение"

    async def user_agent_info(self, request: Request) -> UserAgentInfo:
        """
        Парсинг User-Agent для получения информации о браузере, устройстве и геолокации\n
        Собирает все данные о клиенте в одну модель и возвращает данные в виде UserAgentInfo
        """
        user_agent = request.headers.get("User-Agent", "")
        user_agent_info = self.parse_user_agent(user_agent)
        
        ip_address = self.get_client_ip(request)
        location = await self.get_location_by_ip(ip_address) if ip_address else "Локальная сеть"

        user_agent_info.location = location
        user_agent_info.ip_address = ip_address
        return user_agent_info

session_utils = SessionUtils()
