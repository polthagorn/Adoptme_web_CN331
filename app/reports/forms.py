from django import forms
from .models import Report

class ReportCreateForm(forms.ModelForm):
    # single field; we'll add "multiple" in HTML template
    media_files = forms.FileField(
        required=False,
        help_text="Attach images/videos/files (optional). Max 10MB each."
    )

    class Meta:
        model = Report
        fields = ["reason", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class ReportStatusForm(forms.ModelForm):
    class Meta:
        from .models import Report
        model = Report
        fields = ["status", "admin_note"]
        widgets = {"admin_note": forms.Textarea(attrs={"rows": 4})}


class UserSearchForm(forms.Form):
    q = forms.CharField(required=False, max_length=150)
