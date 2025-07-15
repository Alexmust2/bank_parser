import json
from datetime import datetime
from typing import Dict, List
from text_extractor import TextExtractor
from table_parser import TableParser
from regex_parser import RegexParser

class BankStatementParser:
    def __init__(self, pdf_file: str):
        self.pdf_file = pdf_file
        self.text_extractor = TextExtractor(pdf_file)
        self.table_parser = TableParser(pdf_file)
        self.regex_parser = RegexParser(pdf_file)
        self.rejected_rows = []  # Список для хранения отклоненных строк

    def parse(self) -> Dict:
        """Основной метод парсинга"""
        print(f"Начинаем парсинг файла: {self.pdf_file}")
        
        bank_name = self.text_extractor.detect_bank()
        account_info = self.text_extractor.extract_account_info()
        
        # Получаем транзакции
        transactions = self.table_parser.extract_tables_universal()
        if not transactions:
            transactions = self.regex_parser.extract_with_regex()
        
        # Собираем отклоненные строки из TableParser и RegexParser
        self.rejected_rows.extend(self.table_parser.rejected_rows)
        self.rejected_rows.extend(self.regex_parser.rejected_rows)
        
        # Удаляем дубликаты транзакций
        unique_transactions = []
        seen = set()
        for transaction in transactions:
            key = (transaction.get('date'), transaction.get('amount'), transaction.get('description', '')[:50])
            if key not in seen:
                seen.add(key)
                unique_transactions.append(transaction)
        
        unique_transactions.sort(key=lambda x: x.get('date', ''))
        
        result = {
            "bank_name": bank_name,
            "account_info": account_info,
            "transactions_count": len(unique_transactions),
            "transactions": unique_transactions,
            "rejected_rows_count": len(self.rejected_rows),
            "rejected_rows": self.rejected_rows,
            "extraction_timestamp": datetime.now().isoformat()
        }
        
        return result