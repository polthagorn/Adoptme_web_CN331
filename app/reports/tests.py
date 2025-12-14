from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages import get_messages
from .views import _infer_media_type

from .models import Report, ReportMedia


class ReportsViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="pass12345")
        self.other = User.objects.create_user(username="bob", password="pass12345")
        self.staff = User.objects.create_user(username="staff", password="pass12345", is_staff=True)


    def test_create_report_get_ok(self):
        self.client.login(username="alice", password="pass12345")
        url = reverse("create_report") + f"?ct=auth.user&id={self.other.id}"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Report")

    def test_create_report_post_creates_report(self):
        self.client.login(username="alice", password="pass12345")
        url = reverse("create_report") + f"?ct=auth.user&id={self.other.id}"

        res = self.client.post(url, data={
            "reason": Report.Reason.HARASSMENT,
            "description": "bad behavior",
        })

        self.assertEqual(res.status_code, 302)  # success redirect
        self.assertEqual(Report.objects.count(), 1)

        r = Report.objects.first()
        self.assertEqual(r.reporter, self.user)
        self.assertEqual(r.reason, Report.Reason.HARASSMENT)
        self.assertEqual(r.target_object_id, self.other.id)

        ct = ContentType.objects.get_for_model(User)
        self.assertEqual(r.target_content_type, ct)

    def test_create_report_prevents_duplicate_open_reports(self):
        ct = ContentType.objects.get_for_model(User)
        Report.objects.create(
            reporter=self.user,
            reason=Report.Reason.SPAM,
            description="first",
            target_content_type=ct,
            target_object_id=self.other.id,
            status=Report.Status.OPEN,
        )

        self.client.login(username="alice", password="pass12345")
        url = reverse("create_report") + f"?ct=auth.user&id={self.other.id}"
        res = self.client.post(url, data={
            "reason": Report.Reason.SPAM,
            "description": "second",
        })

        self.assertEqual(res.status_code, 302)
        self.assertEqual(Report.objects.count(), 1)  # still 1

    def test_create_report_saves_media_attachments(self):
        self.client.login(username="alice", password="pass12345")
        url = reverse("create_report") + f"?ct=auth.user&id={self.other.id}"

        img = SimpleUploadedFile("test.png", b"fakepngdata", content_type="image/png")
        vid = SimpleUploadedFile("test.mp4", b"fakevideodata", content_type="video/mp4")

        res = self.client.post(
            url,
            data={
                "reason": Report.Reason.OTHER,
                "description": "with files",
                # IMPORTANT: for multi-upload, Django accepts list under same key
                "media_files": [img, vid],
            },
        )

        self.assertEqual(res.status_code, 302)
        self.assertEqual(Report.objects.count(), 1)
        self.assertEqual(ReportMedia.objects.count(), 2)

        types = set(ReportMedia.objects.values_list("media_type", flat=True))
        self.assertIn(ReportMedia.MediaType.IMAGE, types)
        self.assertIn(ReportMedia.MediaType.VIDEO, types)

    def test_report_user_search_requires_login(self):
        url = reverse("report_user_search")
        res = self.client.get(url)
        # If your view is login_required, expect 302. If not, change to 200.
        # I assume it is login_required in your code:
        self.assertEqual(res.status_code, 302)

    def test_report_user_search_lists_users(self):
        self.client.login(username="alice", password="pass12345")
        url = reverse("report_user_search") + "?q=bo"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "@bob")

    def test_report_bug_requires_login(self):
        url = reverse("report_bug")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)

    def test_report_bug_creates_bug_report(self):
        self.client.login(username="alice", password="pass12345")
        url = reverse("report_bug")

        screenshot = SimpleUploadedFile("bug.png", b"bugimg", content_type="image/png")

        res = self.client.post(url, data={
            "reason": "bug",                 # your bug template uses hidden reason=bug
            "description": "something broke",
            "media_files": [screenshot],
        })

        self.assertEqual(res.status_code, 302)
        r = Report.objects.latest("id")
        self.assertEqual(r.reporter, self.user)
        self.assertEqual(r.reason, Report.Reason.BUG)
        self.assertEqual(ReportMedia.objects.filter(report=r).count(), 1)

    def test_admin_report_list_requires_staff(self):
        self.client.login(username="alice", password="pass12345")
        url = reverse("admin_report_list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)  # redirected because not staff

    def test_admin_report_list_staff_ok(self):
        self.client.login(username="staff", password="pass12345")
        url = reverse("admin_report_list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Reports")

    def test_admin_report_detail_update(self):
        ct = ContentType.objects.get_for_model(User)
        report = Report.objects.create(
            reporter=self.user,
            reason=Report.Reason.SPAM,
            description="spam",
            target_content_type=ct,
            target_object_id=self.other.id,
        )

        self.client.login(username="staff", password="pass12345")
        url = reverse("admin_report_detail", kwargs={"pk": report.pk})

        res = self.client.post(url, data={
            "status": Report.Status.RESOLVED,
            "admin_note": "handled",
        })

        self.assertEqual(res.status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.status, Report.Status.RESOLVED)
        self.assertEqual(report.handled_by, self.staff)
        self.assertEqual(report.admin_note, "handled")

    def test_create_report_invalid_missing_ct(self):
        self.client.login(username="alice", password="pass12345")
        url = reverse("create_report")  # no ct, no id
        res = self.client.get(url, follow=True)

        self.assertEqual(res.status_code, 200)
        msgs = [m.message for m in get_messages(res.wsgi_request)]
        self.assertTrue(any("Invalid report target" in m for m in msgs))

    def test_create_report_invalid_ct_without_dot(self):
        self.client.login(username="alice", password="pass12345")
        url = reverse("create_report") + f"?ct=authuser&id={self.other.id}"  # no dot
        res = self.client.get(url, follow=True)

        self.assertEqual(res.status_code, 200)
        msgs = [m.message for m in get_messages(res.wsgi_request)]
        self.assertTrue(any("Invalid report target" in m for m in msgs))

    def test_admin_report_list_filters_by_valid_status(self):
        # Create two reports with different status
        ct = ContentType.objects.get_for_model(User)
        Report.objects.create(
            reporter=self.user,
            reason=Report.Reason.SPAM,
            description="open report",
            target_content_type=ct,
            target_object_id=self.other.id,
            status=Report.Status.OPEN,
        )
        Report.objects.create(
            reporter=self.user,
            reason=Report.Reason.SPAM,
            description="resolved report",
            target_content_type=ct,
            target_object_id=self.other.id,
            status=Report.Status.RESOLVED,
        )

        self.client.login(username="staff", password="pass12345")
        url = reverse("admin_report_list") + "?status=resolved"
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "resolved report")
        self.assertNotContains(res, "open report")

    def test_admin_report_list_ignores_invalid_status_param(self):
        # If status is not in choices, it should NOT filter
        ct = ContentType.objects.get_for_model(User)
        Report.objects.create(
            reporter=self.user,
            reason=Report.Reason.SPAM,
            description="r1",
            target_content_type=ct,
            target_object_id=self.other.id,
            status=Report.Status.OPEN,
        )
        Report.objects.create(
            reporter=self.user,
            reason=Report.Reason.SPAM,
            description="r2",
            target_content_type=ct,
            target_object_id=self.other.id,
            status=Report.Status.RESOLVED,
        )

        self.client.login(username="staff", password="pass12345")
        url = reverse("admin_report_list") + "?status=NOT_A_STATUS"
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "r1")
        self.assertContains(res, "r2")

    def test_admin_report_detail_get_branch(self):
        ct = ContentType.objects.get_for_model(User)
        report = Report.objects.create(
            reporter=self.user,
            reason=Report.Reason.SPAM,
            description="spam here",
            target_content_type=ct,
            target_object_id=self.other.id,
            status=Report.Status.OPEN,
        )

        self.client.login(username="staff", password="pass12345")
        url = reverse("admin_report_detail", kwargs={"pk": report.pk})
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Report")  # page renders
        # Form should be present
        self.assertContains(res, "name=\"status\"")

    def test_report_bug_get_branch(self):
        self.client.login(username="alice", password="pass12345")
        url = reverse("report_bug")
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Report Bug")  # from template title/header

    def test_infer_media_type_default_file_branch(self):
        """
        Hit the _infer_media_type() default return FILE.
        We trigger it by uploading a non-image/video with unknown content_type.
        """
        self.client.login(username="alice", password="pass12345")
        url = reverse("create_report") + f"?ct=auth.user&id={self.other.id}"

        txt = SimpleUploadedFile("note.txt", b"hello", content_type="text/plain")
        res = self.client.post(url, data={
            "reason": Report.Reason.OTHER,
            "description": "file branch",
            "media_files": [txt],
        })

        self.assertEqual(res.status_code, 302)
        self.assertEqual(Report.objects.count(), 1)
        media = ReportMedia.objects.first()
        self.assertEqual(media.media_type, ReportMedia.MediaType.FILE)

    def test_infer_media_type_image_by_extension_branch(self):
        """
        Hit image branch by extension even if content_type is weird/empty.
        """
        self.client.login(username="alice", password="pass12345")
        url = reverse("create_report") + f"?ct=auth.user&id={self.other.id}"

        img = SimpleUploadedFile("pic.webp", b"fake", content_type="application/octet-stream")
        res = self.client.post(url, data={
            "reason": Report.Reason.OTHER,
            "description": "image ext branch",
            "media_files": [img],
        })

        self.assertEqual(res.status_code, 302)
        media = ReportMedia.objects.latest("id")
        self.assertEqual(media.media_type, ReportMedia.MediaType.IMAGE)

    def test_infer_media_type_video_by_extension_branch(self):
        """
        Hit video branch by extension.
        """
        self.client.login(username="alice", password="pass12345")
        url = reverse("create_report") + f"?ct=auth.user&id={self.other.id}"

        vid = SimpleUploadedFile("clip.mkv", b"fake", content_type="application/octet-stream")
        res = self.client.post(url, data={
            "reason": Report.Reason.OTHER,
            "description": "video ext branch",
            "media_files": [vid],
        })

        self.assertEqual(res.status_code, 302)
        media = ReportMedia.objects.latest("id")
        self.assertEqual(media.media_type, ReportMedia.MediaType.VIDEO)

    def test__infer_media_type_image_video_file(self):
        img = SimpleUploadedFile("a.png", b"x", content_type="image/png")
        vid = SimpleUploadedFile("b.mp4", b"x", content_type="video/mp4")
        txt = SimpleUploadedFile("c.txt", b"x", content_type="text/plain")

        self.assertEqual(_infer_media_type(img), ReportMedia.MediaType.IMAGE)
        self.assertEqual(_infer_media_type(vid), ReportMedia.MediaType.VIDEO)
        self.assertEqual(_infer_media_type(txt), ReportMedia.MediaType.FILE)

    def test_create_report_requires_login(self):
        url = reverse("create_report") + f"?ct=auth.user&id={self.other.id}"

        res = self.client.get(url)

        login_url = reverse("login")
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.url.startswith(login_url))
        self.assertIn("next=", res.url)
