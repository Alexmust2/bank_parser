import re
from typing import List, Dict
from utils import parse_date, parse_amount, clean_description, classify_transaction

class RegexParser:
    def __init__(self, pdf_file: str):
        self.pdf_file = pdf_file
        self.full_text = ""
        self.rejected_rows = []  # Список для хранения отклоненных строк

    def extract_with_regex(self) -> List[Dict]:
        """Извлечение через регулярные выражения"""
        try:
            transactions = []
            if not self.full_text:
                from text_extractor import TextExtractor
                self.full_text = TextExtractor(self.pdf_file).extract_full_text()
            
            patterns = [
                r'(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})\s+(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})\s+([+-]?\d+[,.]?\d*)\s*₽?\s+([+-]?\d+[,.]?\d*)\s*₽?\s+(.+?)\s+(\d{4})',
                r'(\d{2}\.\d{2}\.\d{4})\s+.*?([+-]?\d+[,.]?\d*)\s*₽?\s+([+-]?\d+[,.]?\d*)\s*₽?\s+(.+?)\s+(\d{4})',
                r'(\d{2}\.\d{2}\.\d{4}).*?([+-]?\d+[,.]?\d*)\s*₽.*?(Операция|Платеж|Перевод|Зачисление|Внутрибанковский|Оплата).*?(\d{4})',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, self.full_text, re.MULTILINE | re.DOTALL)
                print(f"Регулярка нашла {len(matches)} совпадений")
                
                for match in matches:
                    try:
                        if len(match) >= 4:
                            if len(match) == 8:
                                date, time1, date2, time2, amount1, amount2, description, card = match
                                amount = amount1 if amount1 and amount1 != '0' else amount2
                            elif len(match) == 5:
                                date, amount1, amount2, description, card = match
                                amount = amount1 if amount1 and amount1 != '0' else amount2
                            else:
                                date = match[0]
                                amount = match[1]
                                description = ' '.join(match[2:-1])
                                card = match[-1]
                            
                            transaction = {
                                "date": parse_date(date),
                                "amount": parse_amount(amount),
                                "description": clean_description(description),
                                "type": classify_transaction(description),
                                "card": card if 'card' in locals() else None,
                                "method": "regex"
                            }
                            
                            if transaction["date"] and transaction["amount"] is not None:
                                transactions.append(transaction)
                            else:
                                self.rejected_rows.append({
                                    "source": "regex",
                                    "match": match,
                                    "reason": "Не удалось распарсить дату или сумму"
                                })
                    except Exception as e:
                        print(f"Ошибка парсинга строки: {e}")
                        self.rejected_rows.append({
                            "source": "regex",
                            "match": match,
                            "reason": f"Ошибка парсинга: {str(e)}"
                        })
                        continue
                
                if transactions:
                    print(f"Найдено {len(transactions)} транзакций через регулярки")
                    return transactions
            
            return transactions
        except Exception as e:
            print(f"Ошибка регулярных выражений: {e}")
            return []