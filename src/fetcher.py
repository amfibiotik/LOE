import requests


class PowerDataFetcher:
    API_URL = "https://api.loe.lviv.ua/api/menus?page=1&type=photo-grafic"
    
    def fetch_schedule(self) -> dict:
        """Отримує дані з API"""
        try:
            response = requests.get(self.API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "hydra:member" in data and len(data["hydra:member"]) > 0:
                items = data["hydra:member"][0].get("menuItems", [])
                if items:
                    return items[0]
            
            return None
        except Exception as e:
            print(f"Error fetching schedule: {e}")
            return None
    
    def get_latest_schedule(self) -> dict:
        """Отримує найсвіжіший графік"""
        try:
            response = requests.get(self.API_URL, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "hydra:member" in data and len(data["hydra:member"]) > 0:
                items = data["hydra:member"][0].get("menuItems", [])
                
                # Шукаємо елемент "Today" з HTML
                for item in items:
                    if item.get("name") == "Today" and item.get("rawHtml"):
                        return item
                
                # Якщо не знайшли Today, шукаємо будь-який з HTML
                for item in items:
                    if item.get("rawHtml"):
                        return item
            
            return None
        except Exception:
            return None
