import camelot
import pdfplumber
import pandas as pd
import re
from typing import List, Dict, Optional
from utils import parse_date, parse_amount, clean_description, classify_transaction

class TableParser:
    def __init__(self, pdf_file: str):
        self.pdf_file = pdf_file
        self.rejected_rows = []  # Список для хранения отклоненных строк

    def find_transaction_pages(self) -> List[int]:
        """Поиск страниц с транзакциями"""
        transaction_pages = []
        try:
            with pdfplumber.open(self.pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        transaction_indicators = [
                            r'дата.*операции',
                            r'дата.*списания',
                            r'дата.*зачисления',
                            r'сумма.*операции',
                            r'описание.*операции',
                            r'получатель.*плательщик',
                            r'\d{2}\.\d{2}\.\d{4}.*\d{2}\.\d{2}\.\d{4}.*[+-]?\d+.*₽',
                            r'внутрибанковский.*перевод',
                            r'операция.*bitkoi',
                            r'перевод.*договор',
                            r'зачисление.*средств'
                        ]
                        if any(re.search(pattern, page_text, re.IGNORECASE) for pattern in transaction_indicators):
                            transaction_pages.append(page_num)
        except Exception as e:
            print(f"Ошибка при поиске страниц с транзакциями: {e}")
        return transaction_pages

    def extract_tables_universal(self) -> List[Dict]:
        """Универсальное извлечение таблиц"""
        transactions = []
        transaction_pages = self.find_transaction_pages()
        
        if not transaction_pages:
            print("Страницы с транзакциями не найдены, пробуем все страницы")
            transaction_pages = list(range(1, 100))
        
        transactions.extend(self._extract_with_camelot(transaction_pages))
        if not transactions:
            transactions.extend(self._extract_with_pdfplumber(transaction_pages))
        
        return transactions

    def _extract_with_camelot(self, pages: List[int] = None) -> List[Dict]:
        """Извлечение через Camelot"""
        try:
            transactions = []
            if pages:
                pages_str = ','.join(map(str, pages))
            else:
                pages_str = "all"
            
            camelot_configs = [
                {"flavor": "stream", "row_tol": 15, "edge_tol": 500},
                {"flavor": "lattice"},
                {"flavor": "stream", "row_tol": 10, "edge_tol": 300},
                {"flavor": "stream", "row_tol": 20, "edge_tol": 200},
            ]
            
            for config in camelot_configs:
                try:
                    tables = camelot.read_pdf(self.pdf_file, pages=pages_str, **config)
                    print(f"Camelot ({config['flavor']}): найдено {len(tables)} таблиц на страницах {pages_str}")
                    
                    for i, table in enumerate(tables):
                        df = table.df
                        header_row = self._find_header_row(df)
                        if header_row >= 0:
                            headers = [re.sub(r'\n|\s+', ' ', str(h).strip().lower()) for h in df.iloc[header_row].tolist()]
                            for idx in range(header_row + 1, len(df)):
                                row = df.iloc[idx].tolist()
                                if self._is_transaction_row(row):
                                    transaction = self._parse_table_row(headers, row)
                                    if transaction:
                                        transactions.append(transaction)
                                    else:
                                        self.rejected_rows.append({
                                            "source": "camelot",
                                            "page": table.page,
                                            "reason": "Не удалось распарсить строку в транзакцию",
                                            "headers": headers
                                        })
                    if transactions:
                        print(f"Найдено {len(transactions)} транзакций через Camelot")
                        return transactions
                except Exception as e:
                    print(f"Ошибка с конфигурацией {config}: {e}")
                    continue
            return transactions
        except Exception as e:
            print(f"Ошибка Camelot: {e}")
            return []

    def _extract_with_pdfplumber(self, pages: List[int] = None) -> List[Dict]:
        """Извлечение через pdfplumber"""
        try:
            transactions = []
            with pdfplumber.open(self.pdf_file) as pdf:
                pages_to_process = pages if pages else range(len(pdf.pages))
                for page_num in pages_to_process:
                    if page_num > len(pdf.pages):
                        break
                    page = pdf.pages[page_num - 1]
                    tables = page.extract_tables()
                    if tables:
                        print(f"Найдено {len(tables)} таблиц на странице {page_num}")
                        for table in tables:
                            if not table or len(table) < 2:
                                continue
                            header_row_idx = -1
                            for i, row in enumerate(table):
                                if row:
                                    header_text = ' '.join(str(cell).lower() for cell in row if cell)
                                    if any(word in header_text for word in ['дата', 'сумма', 'описание', 'операция']):
                                        header_row_idx = i
                                        break
                            if header_row_idx >= 0:
                                headers = table[header_row_idx]
                                print(f"Заголовки на странице {page_num}: {headers}")
                                for row in table[header_row_idx + 1:]:
                                    if row and any(cell for cell in row if cell):
                                        transaction = self._parse_table_row(headers, row)
                                        if transaction:
                                            transactions.append(transaction)
                                        else:
                                            self.rejected_rows.append({
                                                "source": "pdfplumber",
                                                "page": page_num,
                                                "reason": "Не удалось распарсить строку в транзакцию"
                                            })
            print(f"Найдено {len(transactions)} транзакций через pdfplumber")
            return transactions
        except Exception as e:
            print(f"Ошибка pdfplumber: {e}")
            return []

    def _find_header_row(self, df: pd.DataFrame) -> int:
        """Поиск строки с заголовками"""
        header_indicators = [
            'дата', 'сумма', 'описание', 'операция', 'получатель',
            'отправитель', 'назначение', 'валюта', 'карта', 'зачисления',
            'списания', 'плательщик', 'перевод'
        ]
        for idx, row in df.iterrows():
            row_text = ' '.join(str(cell).lower() for cell in row if pd.notna(cell))
            matches = sum(1 for indicator in header_indicators if indicator in row_text)
            if matches >= 2:
                return idx
        return -1

    def _is_transaction_row(self, row: List) -> bool:
        """Проверка, является ли строка транзакцией"""
        if not row or all(pd.isna(cell) or str(cell).strip() == '' for cell in row):
            return False
        date_found = False
        amount_found = False
        for cell in row:
            if pd.notna(cell):
                cell_str = str(cell).strip()
                if re.match(r'\d{2}\.\d{2}\.\d{4}', cell_str):
                    date_found = True
                if re.search(r'[+-]?\d+[,.]?\d*', cell_str) and ('₽' in cell_str or len(cell_str) < 20):
                    amount_found = True
        return date_found and amount_found

    def _parse_table_row(self, headers: List, row: List) -> Optional[Dict]:
        """Парсинг строки таблицы"""
        try:
            date_field = None
            amount_field = None
            description_field = None
            
            # Создаем временный словарь только для парсинга
            temp_dict = {}
            for i, header in enumerate(headers):
                if i < len(row) and row[i] is not None:
                    temp_dict[str(header)] = str(row[i])
            
            amount_priority = [
                'сумма в валюте операции',
                'сумма операции в валюте карты',
                'сумма в валюте эсп',
                'сумма операции',
                'сумма',
                'amount'
            ]
            non_amount_keys = [
                'дата',
                'время',
                'date',
                'time',
                'карта',
                'номер карты',
                'card',
                'описание',
                'description'
            ]
            
            for priority_key in amount_priority:
                for key, value in temp_dict.items():
                    key_lower = key.lower()
                    if priority_key in key_lower:
                        parsed_amount = parse_amount(value)
                        if parsed_amount is not None:
                            amount_field = value
                            break
                if amount_field:
                    break
            
            if not amount_field:
                for key, value in temp_dict.items():
                    key_lower = key.lower()
                    if any(non_key in key_lower for non_key in non_amount_keys):
                        continue
                    parsed_amount = parse_amount(value)
                    if parsed_amount is not None:
                        amount_field = value
                        break
            
            date_priority = [
                'дата и время операции',
                'дата операции',
                'дата списания',
                'дата зачисления',
                'дата обработки',
                'дата',
                'date'
            ]
            
            for priority_key in date_priority:
                for key, value in temp_dict.items():
                    key_lower = key.lower()
                    if priority_key in key_lower:
                        parsed_date = parse_date(value)
                        if parsed_date:
                            date_field = value
                            break
                if date_field:
                    break
            
            if not date_field:
                for value in temp_dict.values():
                    if parse_date(value):
                        date_field = value
                        break
            
            description_priority = [
                'описание операции',
                'описание',
                'назначение платежа',
                'назначение',
                'получатель',
                'плательщик',
                'операция',
                'description'
            ]
            
            for priority_key in description_priority:
                for key, value in temp_dict.items():
                    key_lower = key.lower()
                    if priority_key in key_lower:
                        description_field = value
                        break
                if description_field:
                    break
            
            if not description_field:
                candidates = []
                for key, value in temp_dict.items():
                    if (len(value) > 10 and 
                        not parse_date(value) and 
                        parse_amount(value) is None and
                        not re.match(r'^\d{4}$', value)):
                        candidates.append((key, value))
                if candidates:
                    description_field = max(candidates, key=lambda x: len(x[1]))[1]
            
            if date_field and amount_field and description_field:
                return {
                    "date": parse_date(date_field),
                    "amount": parse_amount(amount_field),
                    "description": clean_description(description_field),
                    "type": classify_transaction(description_field),
                    "method": "table"
                }
            else:
                reason = []
                if not date_field:
                    reason.append("Отсутствует дата")
                if not amount_field:
                    reason.append("Отсутствует сумма")
                if not description_field:
                    reason.append("Отсутствует описание")
                self.rejected_rows.append({
                    "source": "table",
                    "reason": "; ".join(reason)
                })
                return None
        except Exception as e:
            print(f"Ошибка парсинга строки таблицы: {e}")
            self.rejected_rows.append({
                "source": "table",
                "reason": f"Ошибка парсинга: {str(e)}"
            })
            return None