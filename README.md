# Document OCR Processor

A web application that allows users to upload PDF documents (receipts, contracts, statements) and extract key information using OCR technology.

## Features

- Upload PDF files through a beautiful web interface
- Process documents using multiple OCR engines (PaddleOCR, Tesseract, TrOCR)
- Extract key information such as:
  - Document type (receipt, contract, statement)
  - Document ID
  - Date
  - Bank name
  - Client name
  - Account number
  - Amount value and currency
- Post-process OCR results with LLM API for improved accuracy
- View and manage processed documents

## Requirements

- Python 3.8+
- Django 4.2+
- PaddleOCR
- Tesseract OCR
- pdf2image
- poppler-utils

## Installation

1. Clone the repository

```
git clone <repository-url>
cd document-ocr-processor
```

2. Create a virtual environment and activate it

```
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies

```
pip install -r requirements.txt
```

4. Install system dependencies

- Poppler (for pdf2image)
  - On Ubuntu: `apt-get install poppler-utils`
  - On macOS: `brew install poppler`
  - On Windows: Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases)

- Tesseract OCR
  - On Ubuntu: `apt-get install tesseract-ocr`
  - On macOS: `brew install tesseract`
  - On Windows: Download installer from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)

5. Set up environment variables (optional)

Copy the `.env.example` file to `.env` and fill in the values:

```
cp .env.example .env
```

6. Run migrations

```
python manage.py migrate
```

7. Create a superuser (optional)

```
python manage.py createsuperuser
```

8. Run the development server

```
python manage.py runserver
```

9. Visit http://127.0.0.1:8000/ in your browser

## Usage

1. Upload a PDF document through the web interface
2. The system will process the document and extract information
3. Review the extracted information on the results page
4. Access all processed documents through the Documents list

## License

MIT
