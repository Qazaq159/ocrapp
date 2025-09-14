from django import forms
from ocr_app.models import Document

class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = [
            'file', 'document_type', 'document_id', 'date', 
            'entity1_name', 'entity1_type',
            'entity2_name', 'entity2_type',
            'amount_value', 'amount_currency'
        ]
        labels = {
            'file': 'Upload File',
            'document_type': 'Document Type',
            'document_id': 'Document ID',
            'date': 'Date',
            'entity1_name': 'Entity 1 Name',
            'entity1_type': 'Entity 1 Type',
            'entity2_name': 'Entity 2 Name',
            'entity2_type': 'Entity 2 Type',
            'amount_value': 'Amount Value',
            'amount_currency': 'Currency',
        }
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'file-input',
                'accept': '.pdf',
                'id': 'id_file'
            }),
            'entity1_type': forms.Select(choices=[
                ('', '---'),
                ('bank', 'Bank'),
                ('company', 'Company'),
                ('person', 'Person')
            ]),
            'entity2_type': forms.Select(choices=[
                ('', '---'),
                ('bank', 'Bank'),
                ('company', 'Company'),
                ('person', 'Person')
            ]),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if not file.name.endswith('.pdf'):
                raise forms.ValidationError('Only PDF files are allowed.')
            if file.size > 10 * 1024 * 1024:  # 10MB limit
                raise forms.ValidationError('File size cannot exceed 10MB.')
        return file


class MultilingualDocumentForm(DocumentForm):
    """Document form with multilingual labels and help texts"""
    class Meta(DocumentForm.Meta):
        labels = {
            'file': 'Upload File / Загрузить файл / Файлды жүктеу',
            'document_type': 'Document Type / Тип документа / Құжат түрі',
            'document_id': 'Document ID / Номер документа / Құжат нөмірі',
            'date': 'Date / Дата / Күні',
            'entity1_name': 'Entity 1 Name / Название организации 1 / Ұйым 1 атауы',
            'entity1_type': 'Entity 1 Type / Тип организации 1 / Ұйым 1 түрі',
            'entity1_id': 'Entity 1 ID / Идентификатор 1 / Сәйкестендіргіш 1',
            'entity2_name': 'Entity 2 Name / Название организации 2 / Ұйым 2 атауы',
            'entity2_type': 'Entity 2 Type / Тип организации 2 / Ұйым 2 түрі',
            'entity2_id': 'Entity 2 ID / Идентификатор 2 / Сәйкестендіргіш 2',
            'amount_value': 'Amount / Сумма / Сома',
            'amount_currency': 'Currency / Валюта / Валюта',
        }
        help_texts = {
            'entity1_type': 'Bank, company or person / Банк, компания или человек / Банк, компания немесе адам',
            'entity2_type': 'Bank, company or person / Банк, компания или человек / Банк, компания немесе адам',
            'entity1_id': 'BIN/IIN/Account number / БИН/ИИН/Номер счета / БСН/ЖСН/Шот нөмірі',
            'entity2_id': 'BIN/IIN/Account number / БИН/ИИН/Номер счета / БСН/ЖСН/Шот нөмірі',
        }
