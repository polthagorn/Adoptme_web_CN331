from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import Report, ReportMedia
from .forms import ReportCreateForm, ReportStatusForm, UserSearchForm

def staff_required(view):
    return user_passes_test(lambda u: u.is_authenticated and u.is_staff)(view)
# test will not cover media files
def _infer_media_type(uploaded_file): # pragma: no cover
    name = (uploaded_file.name or "").lower()
    ctype = (getattr(uploaded_file, "content_type", "") or "").lower()

    if ctype.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return ReportMedia.MediaType.IMAGE
    if ctype.startswith("video/") or name.endswith((".mp4", ".mov", ".webm", ".mkv")):
        return ReportMedia.MediaType.VIDEO
    return ReportMedia.MediaType.FILE

@login_required
def create_report(request):
    """
    URL expects:
    ?ct=<app_label.model>&id=<object_id>
    Example: ?ct=posts.post&id=12
    """
    ct_str = request.GET.get("ct")
    obj_id = request.GET.get("id")

    if not ct_str or not obj_id or "." not in ct_str:
        messages.error(request, "Invalid report target.")
        return redirect("home")

    app_label, model = ct_str.split(".", 1)
    content_type = get_object_or_404(ContentType, app_label=app_label, model=model)

    model_cls = content_type.model_class()
    target_obj = get_object_or_404(model_cls, pk=obj_id)

    existing = Report.objects.filter(
        reporter=request.user,
        target_content_type=content_type,
        target_object_id=target_obj.pk,
        status__in=[Report.Status.OPEN, Report.Status.IN_REVIEW],
    ).first()
    if existing:
        messages.info(request, "You already reported this. Our team will review it.")
        return redirect(request.META.get("HTTP_REFERER", "home"))

    if request.method == "POST":
        form = ReportCreateForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.target_content_type = content_type
            report.target_object_id = target_obj.pk
            report.save()

            # Save multiple media attachments
            for f in request.FILES.getlist("media_files"):
                ReportMedia.objects.create(
                    report=report,
                    media_type=_infer_media_type(f),
                    file=f,
                )

            messages.success(request, "Thanks! Your report has been submitted.")
            return redirect(request.META.get("HTTP_REFERER", "home"))
    else:
        form = ReportCreateForm()

    return render(request, "reports/report_create.html", {"form": form, "target": target_obj})


@login_required
def report_user_search(request):
    """
    Page with search bar to find user and then click "Report" on them.
    """
    form = UserSearchForm(request.GET or None)
    users = User.objects.none()

    if form.is_valid():
        q = (form.cleaned_data.get("q") or "").strip()
        if q:
            users = (
                User.objects
                .filter(Q(username__icontains=q) | Q(email__icontains=q))
                .exclude(id=request.user.id)[:20]
            )

    return render(request, "reports/report_user_search.html", {"form": form, "users": users})


@staff_required
def admin_report_list(request):
    status = request.GET.get("status", "")
    qs = Report.objects.select_related("reporter", "handled_by", "target_content_type")

    if status in [s for s, _ in Report.Status.choices]:
        qs = qs.filter(status=status)

    return render(request, "reports/admin_report_list.html", {"reports": qs, "status": status})


@staff_required
def admin_report_detail(request, pk):
    report = get_object_or_404(
        Report.objects.select_related("reporter", "handled_by", "target_content_type"),
        pk=pk,
    )

    if request.method == "POST":
        form = ReportStatusForm(request.POST, instance=report)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.handled_by = request.user
            updated.save()
            messages.success(request, "Report updated.")
            return redirect("admin_report_detail", pk=report.pk)
    else:
        form = ReportStatusForm(instance=report)

    return render(request, "reports/admin_report_detail.html", {"report": report, "form": form})

def _infer_media_type(uploaded_file):
    name = (uploaded_file.name or "").lower()
    ctype = (getattr(uploaded_file, "content_type", "") or "").lower()
    if ctype.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
        return ReportMedia.MediaType.IMAGE
    if ctype.startswith("video/") or name.endswith((".mp4", ".mov", ".webm", ".mkv")):
        return ReportMedia.MediaType.VIDEO
    return ReportMedia.MediaType.FILE

@login_required
def report_bug(request):

    if request.method == "POST":
        form = ReportCreateForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.reporter = request.user
            report.reason = Report.Reason.BUG

            # target = reporter user (simple + always valid)
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(request.user.__class__)
            report.target_content_type = ct
            report.target_object_id = request.user.id

            report.save()

            for f in request.FILES.getlist("media_files"):
                ReportMedia.objects.create(
                    report=report,
                    media_type=_infer_media_type(f),
                    file=f,
                )

            messages.success(request, "Thanks! Your bug report was submitted.")
            return redirect("home")
    else:
        form = ReportCreateForm(initial={"reason": Report.Reason.BUG})

    return render(request, "reports/report_bug.html", {"form": form})