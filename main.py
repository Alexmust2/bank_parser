from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
from pathlib import Path
from typing import Dict
import json
from parser import BankStatementParser
from datetime import datetime

app = FastAPI()

# Папка для временного хранения загруженных файлов
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.post("/parser/parse-bank-statement/")
async def parse_bank_statement(file: UploadFile = File(...)):
    try:
        # Проверяем, что файл является PDF
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")

        # Проверяем, что файл не пустой
        if file.size == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        # Логируем имя и размер файла для диагностики
        print(f"Получен файл: {file.filename}, размер: {file.size} байт")

        # Сохраняем файл во временную папку
        file_path = UPLOAD_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        print(f"Сохраняем файл в: {file_path}")
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Проверяем, что файл сохранен
        if not file_path.exists():
            raise HTTPException(status_code=500, detail="Failed to save the uploaded file")

        # Создаем парсер и обрабатываем файл
        parser = BankStatementParser(str(file_path))
        result = parser.parse()

        # Удаляем временный файл
        file_path.unlink()
        print(f"Временный файл {file_path} удален")

        # Возвращаем результат
        return JSONResponse(content={
            "status": "success",
            "data": result
        })

    except Exception as e:
        # Если произошла ошибка, удаляем файл (если он был создан)
        if 'file_path' in locals():
            file_path.unlink(missing_ok=True)
            print(f"Временный файл {file_path} удален из-за ошибки")
        
        print(f"Ошибка обработки файла: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/parser")
async def root():
    return {"message": "Bank Statement Parser API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9090)