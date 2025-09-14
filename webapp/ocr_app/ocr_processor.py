import os
import re
import tempfile
import cv2
import numpy as np
import requests
from pdf2image import convert_from_path
import pytesseract

# Try to import dotenv for environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Try to import ChatPDF connector
try:
    from ocr_app.chatpdf_connector import ChatPDFConnector
    HAS_CHATPDF = True
except ImportError:
    HAS_CHATPDF = False

# Disable PaddleOCR due to dependency issues
USE_PADDLE_OCR = False

class OCRProcessor:
    def __init__(self, chatpdf_api_key=None):
        # PaddleOCR is currently disabled due to dependency issues
        self.use_paddle_ocr = USE_PADDLE_OCR
        # Set the OCR languages: English, Russian, and Kazakh
        self.languages = 'eng+rus+kaz'

        # Initialize ChatPDF if available
        self.chatpdf_api_key = chatpdf_api_key or os.getenv('CHATPDF_API_KEY')
        self.use_chatpdf = HAS_CHATPDF and self.chatpdf_api_key is not None
        self.chatpdf_connector = None

        if self.use_chatpdf:
            try:
                self.chatpdf_connector = ChatPDFConnector(self.chatpdf_api_key)
                print("ChatPDF connector initialized successfully")
            except Exception as e:
                print(f"Error initializing ChatPDF connector: {e}")
                self.use_chatpdf = False

    def process_pdf(self, pdf_path):
        """Process PDF file and extract data using ChatPDF API or OCR"""
        # Try ChatPDF first if available
        if self.use_chatpdf and self.chatpdf_connector:
            print("Attempting to extract data using ChatPDF API...")
            try:
                # Extract data using ChatPDF
                extracted_data = self.chatpdf_connector.extract_document_data(pdf_path)

                # Clean up the source after extraction
                if self.chatpdf_connector.source_id:
                    self.chatpdf_connector.delete_source()

                # Check if we got meaningful results
                if self._is_extraction_successful(extracted_data):
                    print("ChatPDF extraction successful")
                    return extracted_data
                else:
                    print("ChatPDF extraction incomplete, falling back to OCR...")
            except Exception as e:
                print(f"Error using ChatPDF: {e}")
                print("Falling back to OCR processing...")
        else:
            if not self.use_chatpdf:
                print("ChatPDF not available, using OCR processing...")
            else:
                print("ChatPDF connector not initialized, using OCR processing...")

        # Convert PDF to images for OCR processing
        try:
            images = convert_from_path(pdf_path)
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            # Return empty data if conversion fails
            return self._get_empty_data()

        # Process each image
        all_text = []
        for img in images:
            # Process with Tesseract OCR
            try:
                # Enhanced preprocessing for better multilingual OCR results
                img_np = np.array(img)
                # Convert to grayscale
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)

                # Apply noise reduction
                denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

                # Apply adaptive thresholding for better text extraction
                binary = cv2.adaptiveThreshold(
                    denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, 11, 2
                )

                # Apply morphological operations to clean up the image
                kernel = np.ones((1, 1), np.uint8)
                binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

                # Convert back to PIL image for Tesseract
                from PIL import Image
                binary_img = Image.fromarray(binary)

                # Extract text with Tesseract using multiple languages and optimized settings
                custom_config = r'--oem 3 --psm 6 -l ' + self.languages + ' --dpi 300'
                tesseract_text = pytesseract.image_to_string(
                    binary_img,
                    config=custom_config
                )
                print(f"Extracted text sample: {tesseract_text[:100]}...")
                all_text.append(tesseract_text)
            except Exception as e:
                print(f"Error with Tesseract OCR: {e}")

        # Combine all text
        combined_text = ' '.join(all_text)

        # Extract key values
        extracted_data = self._extract_key_values(combined_text)

        # If LLM API key is available, post-process with LLM
        if os.getenv('LLM_API_KEY'):
            extracted_data = self._post_process_with_llm(combined_text, extracted_data)

        # Check if we have good extraction results
        if not self._is_extraction_successful(extracted_data):
            print("Initial extraction incomplete, trying vertical split layout...")
            # Try vertical split processing (side-by-side languages)
            for i, img in enumerate(images):
                try:
                    # Convert to numpy array if needed
                    img_np = np.array(img)
                    height, width = img_np.shape[:2]

                    # Split image vertically in half
                    left_half = img_np[:, :width//2]
                    right_half = img_np[:, width//2:]

                    print(f"Processing page {i+1} with vertical split layout")
                    # Process each half separately
                    left_text = self._process_image_section(left_half)
                    right_text = self._process_image_section(right_half)

                    # Extract data from each half
                    left_data = self._extract_key_values(left_text)
                    right_data = self._extract_key_values(right_text)

                    # Merge the results, prioritizing non-empty values
                    extracted_data = self._merge_extraction_results(extracted_data, left_data)
                    extracted_data = self._merge_extraction_results(extracted_data, right_data)

                    # If we got good results, stop processing
                    if self._is_extraction_successful(extracted_data):
                        print("Successfully extracted data from vertical split layout")
                        break

                except Exception as e:
                    print(f"Error processing vertical split layout: {e}")

        return extracted_data

    def _get_empty_data(self):
        """Return empty data structure"""
        return {
            'document_type': '',
            'document_id': '',
            'date': '',
            'entity1_name': '',
            'entity1_type': '',
            'entity1_id': '',
            'entity2_name': '',
            'entity2_type': '',
            'entity2_id': '',
            'amount_value': '',
            'amount_currency': ''
        }

    def _extract_paddle_text(self, result):
        """Extract text from PaddleOCR result - kept for compatibility"""
        return ""

    def _extract_key_values(self, text):
        """Extract key values from text with multilingual support"""
        data = {
            'document_type': '',
            'document_id': '',
            'date': '',
            'entity1_name': '',
            'entity1_type': '',
            'entity1_id': '',
            'entity2_name': '',
            'entity2_type': '',
            'entity2_id': '',
            'amount_value': '',
            'amount_currency': ''
        }

        # Document type detection with Russian and Kazakh keywords
        if re.search(r'receipt|invoice|payment|чек|счет|платеж|төлем|чек|квитанция', text, re.IGNORECASE):
            data['document_type'] = 'receipt'
        elif re.search(r'contract|agreement|договор|соглашение|келісім|шарт', text, re.IGNORECASE):
            data['document_type'] = 'contract'
        elif re.search(r'statement|account statement|bank statement|выписка|банковская выписка|банк шоты', text, re.IGNORECASE):
            data['document_type'] = 'statement'

        # Document ID detection with multilingual support
        doc_id_patterns = [
            r'(?:invoice|receipt|document|statement|счет|чек|документ|выписка)\s*(?:no|number|#|id|номер|№)[.:\s]*([\w\d-]+)',
            r'(?:№|#)\s*([\w\d-]+)',
        ]

        for pattern in doc_id_patterns:
            doc_id_match = re.search(pattern, text, re.IGNORECASE)
            if doc_id_match:
                data['document_id'] = doc_id_match.group(1)
                break

        # Date detection with multilingual support
        date_patterns = [
            r'(?:date|issued|дата|выдан|күні|берілген)[.:\s]*(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',
            r'(\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4})',  # Just find any date format
            r'(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|янв|фев|мар|апр|май|июн|июл|авг|сен|окт|ноя|дек)[a-zа-я]*\s+\d{2,4})',
        ]

        for pattern in date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                data['date'] = date_match.group(1)
                break

        # Entity detection (banks, companies, persons)
        # First look for banks
        bank_patterns = [
            r'(?:bank|банк|financial institution|issuer)[.:\s]*([A-Za-zА-Яа-я\s&]+(?:Bank|банк|Credit Union|Financial|N\.A\.|National|Trust))',
            r'(Казкоммерцбанк|Халык банк|Народный банк|Сбербанк|Альфа-банк|ВТБ|Банк ЦентрКредит|Евразийский банк|Kaspi|Каспи)',
        ]

        # Look for companies
        company_patterns = [
            r'(?:company|компания|корпорация|корпорация|organization|организация|ТОО|ООО|АО|LLP|LLC)[.:\s]*"?([A-Za-zА-Яа-я\s&«»"\-\.,]+?)"?(?:[,\.;]|$)',
            r'(?:ТОО|ООО|АО|ИП|ЖК|LLP|LLC|JSC|ТОВ)\s+"?([A-Za-zА-Яа-я\s&«»"\-\.,]+?)"?(?:[,\.;]|$)',
            r'(?:БИН|ИИН|BIN|IIN)\s*([\d\s]+)[\s\n]+([A-Za-zА-Яа-я\s&«»"\-\.,]+?)(?:[,\.;]|$)',
            r'(?:компания|фирма|предприятие|company)\s+"?([A-Za-zА-Яа-я\s&«»"\-\.,]+?)"?(?:[,\.;]|$)',
        ]

        # Look for persons
        person_patterns = [
            r'(?:customer|client|name|to|клиент|имя|получатель|тұтынушы|аты|ФИО)[.:\s]*([A-Za-zА-Яа-я\s]+)',
            r'(?:Господин|Госпожа|Г-н|Г-жа|Mr\.|Mrs\.|Ms\.|Miss)[.:\s]*([A-Za-zА-Яа-я\s]+)',
            r'([A-ZА-Я][a-zа-я]+\s+[A-ZА-Я][a-zа-я]+\s+[A-ZА-Я][a-zа-я]+)',  # Full name pattern
            r'([A-ZА-Я][a-zа-я]+\s+[A-ZА-Я]\.\s*[A-ZА-Я]\.)',  # Name with initials
            r'(?:от кого|from|от|кому|to)[.:\s]*([A-ZА-Я][a-zа-я]+\s+[A-ZА-Я][a-zа-я]+(?:\s+[A-ZА-Я][a-zа-я]+)?)'  # Names in sender/recipient contexts
        ]

        # Identifier patterns
        id_patterns = [
            r'(?:account|acct|a/c|счет|счёт|шот)[.:\s#]*([\d\s*-]+)',
            r'(?:IBAN|SWIFT)[.:\s#]*([A-Z\d\s*-]+)',
            r'(?:БИК|БИН|ИИН)[.:\s#]*([\d\s*-]+)',
        ]

        # Extract entity 1
        entity1_extracted = False

        # Try to find a bank first
        for pattern in bank_patterns:
            entity_match = re.search(pattern, text, re.IGNORECASE)
            if entity_match and len(entity_match.group(1).strip()) > 3:
                data['entity1_name'] = entity_match.group(1).strip()
                data['entity1_type'] = 'bank'
                entity1_extracted = True

                # Remove the matched text to avoid duplicate detection
                text = text.replace(entity_match.group(0), '', 1)
                break

        # If no bank found, try company
        if not entity1_extracted:
            for pattern in company_patterns:
                entity_match = re.search(pattern, text, re.IGNORECASE)
                if entity_match and len(entity_match.group(1).strip()) > 3:
                    data['entity1_name'] = entity_match.group(1).strip()
                    data['entity1_type'] = 'company'
                    entity1_extracted = True

                    # Remove the matched text to avoid duplicate detection
                    text = text.replace(entity_match.group(0), '', 1)
                    break

        # If no company found, try person
        if not entity1_extracted:
            for pattern in person_patterns:
                entity_match = re.search(pattern, text, re.IGNORECASE)
                if entity_match and len(entity_match.group(1).strip()) > 3:
                    data['entity1_name'] = entity_match.group(1).strip()
                    data['entity1_type'] = 'person'
                    entity1_extracted = True

                    # Remove the matched text to avoid duplicate detection
                    text = text.replace(entity_match.group(0), '', 1)
                    break

        # Try to find an ID for entity 1
        if entity1_extracted:
            for pattern in id_patterns:
                id_match = re.search(pattern, text, re.IGNORECASE)
                if id_match:
                    data['entity1_id'] = id_match.group(1).strip()

                    # Remove the matched text to avoid duplicate detection
                    text = text.replace(id_match.group(0), '', 1)
                    break

        # Extract entity 2
        entity2_extracted = False

        # Try to find a bank first
        for pattern in bank_patterns:
            entity_match = re.search(pattern, text, re.IGNORECASE)
            if entity_match and len(entity_match.group(1).strip()) > 3:
                data['entity2_name'] = entity_match.group(1).strip()
                data['entity2_type'] = 'bank'
                entity2_extracted = True
                break

        # If no bank found, try company
        if not entity2_extracted:
            for pattern in company_patterns:
                entity_match = re.search(pattern, text, re.IGNORECASE)
                if entity_match and len(entity_match.group(1).strip()) > 3:
                    data['entity2_name'] = entity_match.group(1).strip()
                    data['entity2_type'] = 'company'
                    entity2_extracted = True
                    break

        # If no company found, try person
        if not entity2_extracted:
            for pattern in person_patterns:
                entity_match = re.search(pattern, text, re.IGNORECASE)
                if entity_match and len(entity_match.group(1).strip()) > 3:
                    data['entity2_name'] = entity_match.group(1).strip()
                    data['entity2_type'] = 'person'
                    entity2_extracted = True
                    break

        # Try to find an ID for entity 2
        if entity2_extracted:
            for pattern in id_patterns:
                id_match = re.search(pattern, text, re.IGNORECASE)
                if id_match:
                    data['entity2_id'] = id_match.group(1).strip()
                    break

        # Amount detection with multilingual support
        amount_patterns = [
            r'(?:amount|total|sum|payment|сумма|итого|всего|төлем)[.:\s]*(?:USD|EUR|KZT|RUB|\$|€|₸|₽)?\s*(\d+(?:[.,]\d+)?)\s*(?:(USD|EUR|KZT|RUB|тенге|тг|руб|\$|€|₸|₽|[A-Za-z]{3}))?',
            r'(\d+(?:[.,]\d+)?)\s*(USD|EUR|KZT|RUB|тенге|тг|руб|\$|€|₸|₽|[A-Za-z]{3})',
        ]

        for pattern in amount_patterns:
            amount_match = re.search(pattern, text, re.IGNORECASE)
            if amount_match:
                data['amount_value'] = amount_match.group(1)
                if len(amount_match.groups()) > 1 and amount_match.group(2):
                    currency = amount_match.group(2)
                    # Normalize currency codes
                    if currency.lower() in ['тенге', 'тг', '₸']:
                        currency = 'KZT'
                    elif currency.lower() in ['руб', '₽']:
                        currency = 'RUB'
                    data['amount_currency'] = currency
                break

        return data

    def _post_process_with_llm(self, text, extracted_data):
        """Post-process extracted data with LLM API"""
        api_key = os.getenv('LLM_API_KEY')
        api_url = os.getenv('LLM_API_URL', 'https://api.openai.com/v1/chat/completions')

        print(f"LLM API key configured: {'Yes' if api_key else 'No'}")
        if not api_key:
            print("LLM post-processing skipped - no API key found")
            return extracted_data

        prompt = f"""I extracted the following information from a document using OCR, but there might be errors. The document may contain text in English, Russian, and/or Kazakh languages. The document involves two entities (organizations, banks, or persons). Please correct any mistakes:

        Original OCR text: {text[:2000]}...

        Extracted information:
        Document Type: {extracted_data['document_type']}
        Document ID: {extracted_data['document_id']}
        Date: {extracted_data['date']}

        Entity 1 Name: {extracted_data['entity1_name']}
        Entity 1 Type: {extracted_data['entity1_type']}
        Entity 1 ID: {extracted_data['entity1_id']}

        Entity 2 Name: {extracted_data['entity2_name']}
        Entity 2 Type: {extracted_data['entity2_type']}
        Entity 2 ID: {extracted_data['entity2_id']}

        Amount Value: {extracted_data['amount_value']}
        Amount Currency: {extracted_data['amount_currency']}

        Please return the corrected information in a structured format. If you can identify which entity is a bank and which is a client/company, please do so."""

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': 'gpt-4',
            'messages': [
                {'role': 'system', 'content': 'You are an assistant that helps correct OCR extraction errors from documents in English, Russian, and Kazakh languages.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.3
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload)
            if response.status_code == 200:
                result = response.json()
                assistant_response = result['choices'][0]['message']['content']

                # Extract structured data from the response
                improved_data = self._parse_llm_response(assistant_response, extracted_data)
                return improved_data
            else:
                return extracted_data  # Return original data if API call fails
        except Exception as e:
            print(f"Error calling LLM API: {e}")
            return extracted_data

    def _parse_llm_response(self, response, original_data):
        """Parse LLM response to extract structured data"""
        improved_data = original_data.copy()

        # Try to find key-value pairs in the response
        for key in original_data.keys():
            key_pattern = f"{key.replace('_', ' ').title()}:\s*([^\n]+)"  # Convert key_name to Key Name:
            match = re.search(key_pattern, response, re.IGNORECASE)
            if match and match.group(1).strip() and match.group(1).strip().lower() != 'none':
                improved_data[key] = match.group(1).strip()

        return improved_data

    def _is_extraction_successful(self, data):
        """Check if we have extracted the essential entity information"""
        # Consider extraction successful if we have found at least one entity name and type
        has_entity1 = bool(data.get('entity1_name') and data.get('entity1_type'))
        has_entity2 = bool(data.get('entity2_name') and data.get('entity2_type'))

        # Need at least one complete entity and some other identifying information
        return (has_entity1 or has_entity2) and bool(data.get('document_type') or data.get('document_id'))

    def _process_image_section(self, img_section):
        """Process a section of an image with OCR"""
        try:
            # Convert to grayscale if needed
            if len(img_section.shape) == 3:  # Color image
                gray = cv2.cvtColor(img_section, cv2.COLOR_BGR2GRAY)
            else:  # Already grayscale
                gray = img_section

            # Apply noise reduction
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

            # Apply adaptive thresholding
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2
            )

            # Apply morphological operations to clean up the image
            kernel = np.ones((1, 1), np.uint8)
            binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

            # Convert to PIL image for Tesseract
            from PIL import Image
            binary_img = Image.fromarray(binary)

            # Extract text with Tesseract using multiple languages
            custom_config = r'--oem 3 --psm 6 -l ' + self.languages + ' --dpi 300'
            text = pytesseract.image_to_string(binary_img, config=custom_config)

            print(f"Extracted section text sample: {text[:50]}...")
            return text
        except Exception as e:
            print(f"Error processing image section: {e}")
            return ""

    def _merge_extraction_results(self, primary_data, secondary_data):
        """Merge extraction results, prioritizing non-empty values"""
        merged = primary_data.copy()

        # For each field, use secondary data if primary is empty
        for key, value in secondary_data.items():
            if value and not merged.get(key):
                merged[key] = value
                print(f"Found value for {key} in alternative processing: {value}")

        return merged
