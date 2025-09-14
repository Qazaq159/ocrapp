import os
import tempfile
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from ocr_app.forms import DocumentForm, MultilingualDocumentForm
from ocr_app.models import Document
from ocr_app.ocr_processor import OCRProcessor


def index(request):
    """Home page view with file upload form"""
    if request.method == 'POST':
        form = MultilingualDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the uploaded file temporarily
            document = form.save(commit=False)


            try:
                # Create a temporary file to process
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    for chunk in request.FILES['file'].chunks():
                        temp_file.write(chunk)
                    temp_file_path = temp_file.name

                # Process the PDF with OCR
                processor = OCRProcessor()
                extracted_data = processor.process_pdf(temp_file_path)

                print(extracted_data)

                # Clean up the temporary file
                os.unlink(temp_file_path)

                # Update document with extracted data
                for key, value in extracted_data.items():
                    if hasattr(document, key):
                        setattr(document, key, value)

                # Save the document
                document.save()

                # Redirect to results page
                return redirect('document_detail', document_id=document.id)

            except Exception as e:
                messages.error(request, f"Error processing document: {str(e)}")
                return render(request, 'ocr_app/index.html', {'form': form})
    else:
        form = MultilingualDocumentForm()

    return render(request, 'ocr_app/index.html', {'form': form})




def document_detail(request, document_id):
    """View for displaying document details after processing"""
    try:
        document = Document.objects.get(id=document_id)
        return render(request, 'ocr_app/document_detail.html', {'document': document})
    except Document.DoesNotExist:
        messages.error(request, "Document not found")
        return redirect('index')


def document_list(request):
    """View for displaying all uploaded documents"""
    documents = Document.objects.all().order_by('-uploaded_at')
    return render(request, 'ocr_app/document_list.html', {'documents': documents})
