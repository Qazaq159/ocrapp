# OCR Document Processor

A Django web application for processing PDF documents using AI technologies to extract key information.

## Features

- Upload PDF documents
- Extract text using ChatPDF AI API or Tesseract OCR
- Automatically identify document information:
  - Document type (receipt, contract, statement)
  - Document ID
  - Date
  - Bank name
  - Client name
  - Account number
  - Amount and currency
- View processed documents and extracted information
- Multilingual support (English, Russian, Kazakh)

## Setup

### Prerequisites

- Python 3.8+
- Tesseract OCR installed on your system
- Poppler (for PDF processing)

### Installation

1. Clone the repository

2. Install system dependencies:

   **Ubuntu/Debian:**
   ```
   sudo apt-get update
   sudo apt-get install tesseract-ocr poppler-utils
   ```

   **macOS:**
   ```
   brew install tesseract poppler
   ```

   **Windows:**
   - Download and install [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
   - Download and install [Poppler](https://github.com/oschwartz10612/poppler-windows/releases)

3. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

5. Run migrations:
   ```
   python manage.py migrate
   ```

6. Create necessary directories:
   ```
   mkdir -p media/documents
   mkdir -p static
   ```

7. Run the development server:
   ```
   python manage.py runserver
   ```

8. Access the application at http://127.0.0.1:8000/

## Optional Configuration

### LLM Post-processing (OpenAI)

To use LLM post-processing for better OCR results:

1. Create a `.env` file in the project root with:
   ```
   LLM_API_KEY=your_openai_api_key
   LLM_API_URL=https://api.openai.com/v1/chat/completions
   ```

## License

MIT
