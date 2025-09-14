import os
import json
import requests
from typing import Dict, Any, Optional


class ChatPDFConnector:
    """Connector for ChatPDF API to process and extract data from PDF documents"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize ChatPDF connector

        Args:
            api_key: ChatPDF API key. If not provided, will try to get from environment
        """
        self.api_key = api_key or os.getenv('CHATPDF_API_KEY')
        if not self.api_key:
            raise ValueError("ChatPDF API key is required. Set CHATPDF_API_KEY environment variable or pass it directly.")

        self.base_url = 'https://api.chatpdf.com/v1'
        self.headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
        self.source_id = None

    def upload_file(self, file_path: str) -> str:
        """
        Upload PDF file to ChatPDF and get source ID

        Args:
            file_path: Path to the PDF file

        Returns:
            Source ID for the uploaded file

        Raises:
            Exception: If upload fails
        """
        try:
            # For file upload, we need different headers
            upload_headers = {
                'x-api-key': self.api_key
            }

            with open(file_path, 'rb') as file:
                files = [
                    ('file', ('file', file, 'application/pdf'))
                ]

                response = requests.post(
                    f'{self.base_url}/sources/add-file',
                    headers=upload_headers,
                    files=files
                )

                if response.status_code == 200:
                    self.source_id = response.json()['sourceId']
                    print(f'File uploaded successfully. Source ID: {self.source_id}')
                    return self.source_id
                else:
                    raise Exception(f'Upload failed: {response.status_code} - {response.text}')

        except Exception as e:
            raise Exception(f'Error uploading file: {str(e)}')

    def query_document(self, source_id: str, question: str) -> str:
        """
        Query the uploaded document with a specific question

        Args:
            source_id: Source ID of the uploaded document
            question: Question to ask about the document

        Returns:
            Answer from ChatPDF

        Raises:
            Exception: If query fails
        """
        try:
            data = {
                "sourceId": source_id,
                "messages": [
                    {
                        "role": "user",
                        "content": question
                    }
                ]
            }

            response = requests.post(
                f'{self.base_url}/chats/message',
                headers=self.headers,
                json=data
            )

            if response.status_code == 200:
                return response.json()['content']
            else:
                raise Exception(f'Query failed: {response.status_code} - {response.text}')

        except Exception as e:
            raise Exception(f'Error querying document: {str(e)}')

    def extract_document_data(self, file_path: str) -> Dict[str, Any]:
        """
        Extract structured data from PDF document using ChatPDF

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary containing extracted document data
        """
        try:
            # Upload the file
            source_id = self.upload_file(file_path)

            # Create a JSON-focused query based on your process_file.py
            extraction_query = """Return a JSON object with these fields:
            document_type (Receipt, Contract, Statement, Other),
            document_id,
            date,
            entity1_name,
            entity1_type (bank, company, person),
            entity2_name,
            entity2_type (bank, company, person),
            amount_value,
            amount_currency

            Please analyze the document and extract the relevant information. If a field cannot be found, use an empty string. Return only the JSON object, no additional text."""

            # Query the document
            response = self.query_document(source_id, extraction_query)

            # Parse the JSON response
            extracted_data = self._parse_json_response(response)

            return extracted_data

        except Exception as e:
            print(f"Error extracting data with ChatPDF: {str(e)}")
            return self._get_empty_data()

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the ChatPDF JSON response into structured data

        Args:
            response: Response text from ChatPDF

        Returns:
            Dictionary with parsed data
        """
        try:
            # Try to extract JSON from the response
            # Sometimes the response might have additional text around the JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                # Map the response to our expected structure
                extracted_data = self._get_empty_data()

                # Direct mapping for fields that match
                field_mapping = {
                    'document_type': 'document_type',
                    'document_id': 'document_id',
                    'date': 'date',
                    'entity1_name': 'entity1_name',
                    'entity1_type': 'entity1_type',
                    'entity1_id': 'entity1_id',
                    'entity2_name': 'entity2_name',
                    'entity2_type': 'entity2_type',
                    'entity2_id': 'entity2_id',
                    'amount_value': 'amount_value',
                    'amount_currency': 'amount_currency'
                }

                for response_key, data_key in field_mapping.items():
                    if response_key in data and data[response_key]:
                        # Clean the value and ensure it's not empty or null
                        value = str(data[response_key]).strip()
                        if value and value.lower() not in ['null', 'none', 'n/a', '']:
                            extracted_data[data_key] = value

                print(f"Successfully parsed JSON response: {extracted_data}")
                return extracted_data

            else:
                print("No JSON found in response, trying text parsing...")
                return self._parse_text_response(response)

        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}, trying text parsing...")
            return self._parse_text_response(response)
        except Exception as e:
            print(f"Error parsing response: {e}")
            return self._get_empty_data()

    def _parse_text_response(self, response: str) -> Dict[str, Any]:
        """
        Fallback parser for non-JSON responses

        Args:
            response: Response text from ChatPDF

        Returns:
            Dictionary with parsed data
        """
        data = self._get_empty_data()

        # Try to extract key-value pairs from text
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()

                # Map common variations
                key_mapping = {
                    'document_type': 'document_type',
                    'type': 'document_type',
                    'document_id': 'document_id',
                    'id': 'document_id',
                    'date': 'date',
                    'entity1_name': 'entity1_name',
                    'entity_1_name': 'entity1_name',
                    'first_entity': 'entity1_name',
                    'entity1_type': 'entity1_type',
                    'entity_1_type': 'entity1_type',
                    'entity1_id': 'entity1_id',
                    'entity_1_id': 'entity1_id',
                    'entity2_name': 'entity2_name',
                    'entity_2_name': 'entity2_name',
                    'second_entity': 'entity2_name',
                    'entity2_type': 'entity2_type',
                    'entity_2_type': 'entity2_type',
                    'entity2_id': 'entity2_id',
                    'entity_2_id': 'entity2_id',
                    'amount_value': 'amount_value',
                    'amount': 'amount_value',
                    'value': 'amount_value',
                    'amount_currency': 'amount_currency',
                    'currency': 'amount_currency'
                }

                if key in key_mapping and value and value.lower() not in ['null', 'none', 'n/a', '']:
                    data[key_mapping[key]] = value

        return data

    def _get_empty_data(self) -> Dict[str, Any]:
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

    def delete_source(self, source_id: Optional[str] = None) -> bool:
        """
        Delete uploaded source from ChatPDF (optional cleanup)

        Args:
            source_id: Source ID to delete. Uses instance source_id if not provided

        Returns:
            True if deletion was successful
        """
        if not source_id:
            source_id = self.source_id

        if not source_id:
            return False

        try:
            response = requests.post(
                f'{self.base_url}/sources/delete',
                headers=self.headers,
                json={'sources': [source_id]}
            )

            return response.status_code == 200

        except Exception as e:
            print(f"Error deleting source: {str(e)}")
            return False
