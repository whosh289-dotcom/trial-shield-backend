import csv
import re
from collections import defaultdict
from datetime import datetime
from database import get_connection

def parse_date(date_str):
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    return None

def clean_description(desc):
    # Remove dates, IDs, random alphanumeric strings common in bank statements
    desc = re.sub(r'[0-9]{4,}', '', desc)
    desc = re.sub(r'[\*\#\-\_]', ' ', desc)
    desc = re.sub(r'(?i)(recurring|payment|card|purchase|debit|ach|auth|web|online|subscription)', '', desc)
    return ' '.join(desc.split()).upper()

def detect_recurring_charges(transactions):
    """
    transactions: list of dicts {'date': 'YYYY-MM-DD', 'description': '...', 'amount': float}
    Returns a list of detected recurring subscriptions.
    """
    grouped = defaultdict(list)
    
    # Group by normalized description and exact/similar amount
    for t in transactions:
        desc = clean_description(t['description'])
        if not desc: continue
        amt = abs(float(t['amount']))
        
        # We group by description prefix and amount (rounded to avoid floating issues)
        key = (desc[:15], round(amt, 2))
        dt = parse_date(t['date'])
        if dt:
            grouped[key].append({'date': dt, 'original_desc': t['description'], 'amount': amt})

    detected = []
    
    for (desc, amount), records in grouped.items():
        if len(records) >= 2:
            # Sort by date
            records.sort(key=lambda x: x['date'])
            
            # Check intervals
            intervals = []
            for i in range(1, len(records)):
                delta = (records[i]['date'] - records[i-1]['date']).days
                intervals.append(delta)
                
            # If intervals average around 30 days (monthly) or 365 (yearly) or 7 (weekly)
            avg_interval = sum(intervals) / len(intervals)
            is_recurring = False
            interval_type = "Unknown"
            
            if 25 <= avg_interval <= 35:
                is_recurring = True
                interval_type = "Monthly"
            elif 350 <= avg_interval <= 380:
                is_recurring = True
                interval_type = "Yearly"
            elif 6 <= avg_interval <= 8:
                is_recurring = True
                interval_type = "Weekly"
                
            if is_recurring:
                detected.append({
                    "service_name": desc.title(),
                    "cost": amount,
                    "interval": interval_type,
                    "last_charge_date": records[-1]['date'].strftime("%Y-%m-%d"),
                    "frequency_days": round(avg_interval),
                    "confidence": "High" if len(records) > 2 else "Medium"
                })
                
    return detected
