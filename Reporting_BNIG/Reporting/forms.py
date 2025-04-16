from django import forms

class UploadExcelForm(forms.Form):
    excel_file = forms.FileField(
        label="Selectionner un fichier Excel",
        widget=forms.FileInput(attrs={'accept': '.xlsx, .xls'})

    )