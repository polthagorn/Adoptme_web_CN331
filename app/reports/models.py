from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ValidationError

def report_upload_to(instance, filename):
    # reports/<report_id>/<filename>
    rid = instance.report_id or "new"
    return f"reports/{rid}/{filename}"

class Report(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        IN_REVIEW = "in_review", "In Review"
        RESOLVED = "resolved", "Resolved"
        REJECTED = "rejected", "Rejected"

    class Reason(models.TextChoices):
        BUG = "bug", "Bug / Glitches"
        SPAM = "spam", "Spam"
        SCAM = "scam", "Scam / Fraud"
        INAPPROPRIATE = "inappropriate", "Inappropriate content"
        HARASSMENT = "harassment", "Harassment / Hate"
        ANIMAL_WELFARE = "animal_welfare", "Animal welfare concern"
        MISLEADING = "misleading", "Misleading information"
        OTHER = "other", "Other"

    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reports_made")
    reason = models.CharField(max_length=30, choices=Reason.choices)
    description = models.TextField(blank=True)

    # Generic target (post/store/user/etc.)
    target_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    target_object_id = models.PositiveIntegerField()
    target = GenericForeignKey("target_content_type", "target_object_id")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)

    handled_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="reports_handled"
    )
    admin_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["target_content_type", "target_object_id"]),
        ]

    def __str__(self):
        return f"Report #{self.id} by {self.reporter} ({self.reason})"


class ReportMedia(models.Model):
    """
    Attach images/videos/files to a report.
    """
    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        FILE = "file", "File"

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="media")
    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    file = models.FileField(upload_to=report_upload_to)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Basic safety: limit size to 10MB (adjust if you want)
        if self.file and hasattr(self.file, "size") and self.file.size > 10 * 1024 * 1024:
            raise ValidationError("File too large (max 10MB).")

    def __str__(self):
        return f"Media #{self.id} ({self.media_type}) for Report #{self.report_id}"
