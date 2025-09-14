from django.db import models

class Document(models.Model):
    DOCUMENT_TYPES = (
        ('receipt', 'Receipt'),
        ('contract', 'Contract'),
        ('statement', 'Statement'),
        ('other', 'Other'),
    )

    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPES, blank=True)
    document_id = models.CharField(max_length=100, blank=True)
    date = models.CharField(max_length=100, blank=True)

    # Entity 1 information (can be bank, company, or person)
    entity1_name = models.CharField(max_length=200, blank=True)
    entity1_type = models.CharField(max_length=50, blank=True)  # bank, company, person
    entity1_id = models.CharField(max_length=100, blank=True)  # BIN, IIN, account number

    # Entity 2 information (can be bank, company, or person)
    entity2_name = models.CharField(max_length=200, blank=True)
    entity2_type = models.CharField(max_length=50, blank=True)  # bank, company, person
    entity2_id = models.CharField(max_length=100, blank=True)  # BIN, IIN, account number

    # Transaction information
    amount_value = models.CharField(max_length=100, blank=True)
    amount_currency = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return f"{self.document_type} - {self.document_id}"
