import re
from typing import Optional

def parse_date(date_str: str) -> Optional[str]:
    """Парсинг даты"""
    if not date_str:
        return None
    
    date_patterns = [
        r'(\d{2})\.(\d{2})\.(\d{4})',
        r'(\d{4})-(\d{2})-(\d{2})',
        r'(\d{2})/(\d{2})/(\d{4})',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, str(date_str))
        if match:
            groups = match.groups()
            if len(groups) == 3:
                if len(groups[0]) == 4:
                    return f"{groups[0]}-{groups[1]}-{groups[2]}"
                else:
                    return f"{groups[2]}-{groups[1]}-{groups[0]}"
    
    return None

def parse_amount(amount_str: str) -> Optional[float]:
    """Парсинг суммы"""
    if not amount_str:
        return None

    amount_str = str(amount_str).strip()

    if re.match(r'\d{2}\.\d{2}\.\d{4}', amount_str) or \
       re.match(r'\d{2}:\d{2}', amount_str) or \
       re.match(r'^\d{4}$', amount_str):
        return None

    amount_str = re.sub(r'[₽$€£¥]', '', amount_str).strip()
    amount_str = re.sub(r'\s+', '', amount_str)
    amount_str = amount_str.replace(',', '.')
    amount_str = amount_str.replace('–', '-')

    sign = '-' if '-' in amount_str else ('+' if '+' in amount_str else '')
    amount_str = amount_str.lstrip('+-')

    try:
        return float(sign + amount_str) if sign else float(amount_str)
    except ValueError:
        return None

def clean_description(description: str) -> str:
    """Очистка описания"""
    if not description:
        return ""
    
    description = re.sub(r'\s+', ' ', str(description).strip())
    description = re.sub(r'[^\w\s\-.,():/№]', '', description)
    return description[:300]

def classify_transaction(description: str) -> str:
    """Классификация транзакции"""
    if not description:
        return "unknown"
    
    desc_lower = description.lower()
    
    if any(word in desc_lower for word in ['входящий', 'поступление', 'зачисление', 'перевод на счет']):
        return "income"
    elif any(word in desc_lower for word in ['платеж', 'оплата', 'списание', 'покупка']):
        return "payment"
    elif any(word in desc_lower for word in ['перевод', 'перечисление', 'внутрибанковский']):
        return "transfer"
    elif any(word in desc_lower for word in ['снятие', 'выдача', 'банкомат']):
        return "withdrawal"
    elif any(word in desc_lower for word in ['комиссия', 'плата за']):
        return "fee"
    else:
        return "other"