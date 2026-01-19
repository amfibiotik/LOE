from datetime import datetime, time


class WorkScheduler:
    def is_power_available(self, outages: list, check_time: str) -> bool:
        """Перевіряє чи є світло в конкретний час"""
        check = datetime.strptime(check_time, "%H:%M").time()
        
        for outage in outages:
            start_str = outage["start"]
            end_str = outage["end"]
            
            if end_str == "24:00":
                end_str = "23:59"
            
            start = datetime.strptime(start_str, "%H:%M").time()
            end = datetime.strptime(end_str, "%H:%M").time()
            
            if start <= check < end:
                return False
        
        return True
    
    def calculate_available_hours(self, outages: list, work_start: str, work_end: str) -> float:
        """Підраховує скільки годин буде світло в робочий час"""
        start = datetime.strptime(work_start, "%H:%M")
        end = datetime.strptime(work_end, "%H:%M")
        
        total_minutes = (end - start).seconds // 60
        outage_minutes = 0
        
        for outage in outages:
            out_start_str = outage["start"]
            out_end_str = outage["end"]
            
            # 24:00 = 23:59
            if out_end_str == "24:00":
                out_end_str = "23:59"
            
            out_start = datetime.strptime(out_start_str, "%H:%M")
            out_end = datetime.strptime(out_end_str, "%H:%M")
            
            overlap_start = max(start, out_start)
            overlap_end = min(end, out_end)
            
            if overlap_start < overlap_end:
                outage_minutes += (overlap_end - overlap_start).seconds // 60
        
        return (total_minutes - outage_minutes) / 60
    
    def recommend(self, group1: str, group2: str, schedule: dict, current_time: str) -> dict:
        """Рекомендує де краще працювати"""
        outages1 = schedule.get(group1, [])
        outages2 = schedule.get(group2, [])
        
        has_power1 = self.is_power_available(outages1, current_time)
        has_power2 = self.is_power_available(outages2, current_time)
        
        if has_power1 and has_power2:
            return {
                "location": group1,
                "reason": f"Світло в обох групах"
            }
        
        if not has_power1 and has_power2:
            return {
                "location": group2,
                "reason": f"Група {group1} без світла, {group2} зі світлом"
            }
        
        if has_power1 and not has_power2:
            return {
                "location": group1,
                "reason": f"Група {group1} зі світлом"
            }
        
        # Обидві без світла - вибираємо де швидше з'явиться
        hours1 = self.calculate_available_hours(outages1, "09:00", "18:00")
        hours2 = self.calculate_available_hours(outages2, "09:00", "18:00")
        
        if hours1 >= hours2:
            return {
                "location": group1,
                "reason": f"Група {group1} матиме більше світла ({hours1:.1f}h vs {hours2:.1f}h)"
            }
        else:
            return {
                "location": group2,
                "reason": f"Група {group2} матиме більше світла ({hours2:.1f}h vs {hours1:.1f}h)"
            }
