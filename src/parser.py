import re
from bs4 import BeautifulSoup


class PowerScheduleParser:
    def parse_group_schedule(self, html: str, group: str) -> list:
        """Парсить графік для конкретної групи"""
        pattern = rf"Група {re.escape(group)}\.(.*?)(?=<p>|$)"
        match = re.search(pattern, html, re.DOTALL)
        
        if not match:
            return []
        
        text = match.group(1)
        
        if "Електроенергія є" in text or "Електроенергії є" in text:
            return []
        
        time_pattern = r"з (\d{2}:\d{2}) до (\d{2}:\d{2})"
        matches = re.findall(time_pattern, text)
        
        return [{"start": start, "end": end} for start, end in matches]
    
    def parse_all_groups(self, html: str) -> dict:
        """Парсить графіки для всіх груп"""
        groups = {}
        group_pattern = r"Група (\d+\.\d+)\."
        
        for match in re.finditer(group_pattern, html):
            group = match.group(1)
            groups[group] = self.parse_group_schedule(html, group)
        
        return groups
    
    def extract_date(self, html: str) -> str:
        """Витягує дату з HTML"""
        pattern = r"на (\d{2}\.\d{2}\.\d{4})"
        match = re.search(pattern, html)
        return match.group(1) if match else None
