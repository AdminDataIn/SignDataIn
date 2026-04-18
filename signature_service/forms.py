from django import forms


class SignatureRequestCreateForm(forms.Form):
    document = forms.FileField(label="Documento")
    signer_name = forms.CharField(label="Nombre firmante", max_length=255)
    signer_email = forms.EmailField(label="Email", max_length=254)

    def clean_document(self):
        document = self.cleaned_data["document"]
        if not document.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Solo se permiten archivos PDF.")
        return document
