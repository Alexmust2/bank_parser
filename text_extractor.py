import pdfplumber
import re
from typing import Dict

class TextExtractor:
    def __init__(self, pdf_file: str):
        self.pdf_file = pdf_file
        self.full_text = ""

    def extract_full_text(self) -> str:
        """Извлечение полного текста из PDF"""
        try:
            with pdfplumber.open(self.pdf_file) as pdf:
                full_text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
                self.full_text = full_text
                return full_text
        except Exception as e:
            print(f"Ошибка при извлечении текста: {e}")
            return ""

    def detect_bank(self) -> str:
        """Определение банка по тексту документа"""
        if not self.full_text:
            self.extract_full_text()
        
        text = self.full_text.lower()
        
        bank_patterns = {
            'ТБанк': [
                r'тбанк',
                r't-bank',
                r'тинькофф',
                r'tinkoff',
                r'акционерное общество.*тбанк',
                r'справка о движении средств.*тбанк'
            ],
            'Яндекс Банк': [
                r'яндекс\.банк',
                r'yandex\.bank',
                r'яндекс банк',
                r'ао.*яндекс банк'
            ],
            'Сбербанк': [
                r'сбербанк',
                r'сберегательный банк',
                r'пао сбербанк'
            ],
            'ВТБ': [
                r'втб',
                r'банк втб',
                r'пао.*втб'
            ],
            'Альфа-Банк': [
                r'альфа.банк',
                r'alfa.bank'
            ]
        }
        
        for bank_name, patterns in bank_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return bank_name
        
        generic_patterns = [
            r'ао\s+«([^»]+банк[^»]*)»',
            r'пао\s+«([^»]+банк[^»]*)»',
            r'ооо\s+«([^»]+банк[^»]*)»',
            r'акционерное общество\s+([^,\n]+банк[^,\n]*)',
            r'([А-Я][а-я]+\s+[Бб]анк)',
        ]
        
        for pattern in generic_patterns:
            match = re.search(pattern, self.full_text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Неизвестный банк"

    def extract_account_info(self) -> Dict:
        """Извлечение информации о счете и периоде"""
        if not self.full_text:
            self.extract_full_text()
        
        account_info = {}
        
        period_patterns = [
            r'за период\s+с\s+(\d{2}\.\d{2}\.\d{4})\s+по\s+(\d{2}\.\d{2}\.\d{4})',
            r'период\s+с\s+(\d{2}\.\d{2}\.\d{4})\s+по\s+(\d{2}\.\d{2}\.\d{4})',
            r'с\s+(\d{2}\.\d{2}\.\d{4})\s+по\s+(\d{2}\.\d{2}\.\d{4})',
            r'движение.*с\s+(\d{2}\.\d{2}\.\d{4})\s+по\s+(\d{2}\.\d{2}\.\d{4})',
        ]
        
        for pattern in period_patterns:
            match = re.search(pattern, self.full_text, re.IGNORECASE)
            if match:
                account_info["period_start"] = match.group(1)
                account_info["period_end"] = match.group(2)
                break
        
        contract_patterns = [
            r'договор[а-я]*\s*№?\s*([A-Z0-9\-]+)',
            r'номер договора:?\s*([A-Z0-9\-]+)',
            r'лицевой счет:?\s*([A-Z0-9\-]+)',
            r'счет:?\s*([A-Z0-9\-]+)',
        ]
        
        for pattern in contract_patterns:
            match = re.search(pattern, self.full_text, re.IGNORECASE)
            if match:
                account_info["contract_number"] = match.group(1)
                break
        
        return account_info