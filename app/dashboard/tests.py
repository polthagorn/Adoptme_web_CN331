from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from app.accounts.models import Profile
from app.shelters.models import ShelterProfile
from app.stores.models import Store


class DashboardBaseTest(TestCase):
    def setUp(self):

        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="pass1234"
        )

        self.admin2 = User.objects.create_superuser(
            username="admin2",
            email="admin2@test.com",
            password="pass1234"
        )

        self.user = User.objects.create_user(
            username="user1",
            email="user@test.com",
            password="pass1234"
        )
        Profile.objects.create(user=self.user, score=100)

        self.staff = User.objects.create_user(
            username="staff1",
            email="staff@test.com",
            password="pass1234",
            is_staff=True
        )
        Profile.objects.create(user=self.staff, score=100)

        self.banned = User.objects.create_user(
            username="banned1",
            email="banned@test.com",
            password="pass1234",
            is_active=False
        )
        Profile.objects.create(user=self.banned, score=100)

        self.owner = User.objects.create_user(
            username="owner1",
            email="owner@test.com",
            password="pass1234"
        )

        self.client.login(username="admin", password="pass1234")


# ----------------------------
# Basic pages
# ----------------------------
class DashboardPageTests(DashboardBaseTest):
    def test_dashboard_home_loads(self):
        res = self.client.get(reverse("dashboard_home"))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "dashboard/index.html")

    def test_user_list_loads(self):
        res = self.client.get(reverse("dashboard_users"))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, self.user.username)

    def test_shelter_approval_loads(self):
        ShelterProfile.objects.create(
            user=self.owner,
            name="Happy Shelter",
            status="PENDING",
        )
        url = reverse("shelter_approval")
        res = self.client.get(url)
        self.assertIn(res.status_code, (200, 302))
        if res.status_code == 302:
            self.fail(f"Expected 200 but got redirect to: {res['Location']}")

    def test_store_approval_loads(self):
        Store.objects.create(owner=self.owner, name="Pet Store", status="PENDING")
        res = self.client.get(reverse("store_approval"))
        self.assertEqual(res.status_code, 200)


# ----------------------------
# Permission branch coverage
# ----------------------------
class DashboardPermissionTests(DashboardBaseTest):
    def test_non_superuser_redirected(self):
        self.client.logout()
        normal = User.objects.create_user("normal1", "n@test.com", "pass1234")
        self.client.login(username="normal1", password="pass1234")

        res = self.client.get(reverse("dashboard_home"))
        self.assertEqual(res.status_code, 302)  # user_passes_test redirects

    def test_anonymous_redirected(self):
        self.client.logout()
        res = self.client.get(reverse("dashboard_home"))
        self.assertEqual(res.status_code, 302)


# ----------------------------
# user_list filter branches
# ----------------------------
class UserListFilterBranchTests(DashboardBaseTest):
    def test_user_list_search_q_branch(self):
        res = self.client.get(reverse("dashboard_users") + "?q=user1")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "user1")

    def test_user_list_status_active_branch(self):
        res = self.client.get(reverse("dashboard_users") + "?status=active")
        self.assertEqual(res.status_code, 200)

    def test_user_list_status_banned_branch(self):
        res = self.client.get(reverse("dashboard_users") + "?status=banned")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "banned1")

    def test_user_list_status_staff_branch(self):
        res = self.client.get(reverse("dashboard_users") + "?status=staff")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "staff1")

    def test_user_list_status_superuser_branch(self):
        res = self.client.get(reverse("dashboard_users") + "?status=superuser")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "admin")


# ----------------------------
# POST-only redirect branches
# ----------------------------
class PostOnlyRedirectBranchTests(DashboardBaseTest):
    def test_get_on_post_only_views_redirects(self):
        shelter = ShelterProfile.objects.create(user=self.owner, name="S1", status="PENDING")
        store = Store.objects.create(owner=self.owner, name="Store1", status="PENDING")

        # shelters
        self.assertEqual(self.client.get(reverse("approve_shelter", args=[shelter.id])).status_code, 302)
        self.assertEqual(self.client.get(reverse("reject_shelter", args=[shelter.id])).status_code, 302)

        # stores
        self.assertEqual(self.client.get(reverse("approve_store", args=[store.id])).status_code, 302)
        self.assertEqual(self.client.get(reverse("reject_store", args=[store.id])).status_code, 302)

        # users
        self.assertEqual(self.client.get(reverse("dashboard_delete_user", args=[self.user.id])).status_code, 302)
        self.assertEqual(self.client.get(reverse("dashboard_update_user_score", args=[self.user.id])).status_code, 302)
        self.assertEqual(self.client.get(reverse("dashboard_ban_user", args=[self.user.id])).status_code, 302)
        self.assertEqual(self.client.get(reverse("dashboard_unban_user", args=[self.user.id])).status_code, 302)


# ----------------------------
# Shelters approve/reject branches
# ----------------------------
class ShelterApprovalTests(DashboardBaseTest):
    def setUp(self):
        super().setUp()
        self.shelter = ShelterProfile.objects.create(
            user=self.owner,
            name="Happy Shelter",
            status="PENDING",
            rejection_reason="old reason" 
        )

    def test_approve_shelter(self):
        url = reverse("approve_shelter", args=[self.shelter.id])
        self.client.post(url, follow=True)

        self.shelter.refresh_from_db()
        self.assertEqual(self.shelter.status, "APPROVED")
        self.assertEqual(self.shelter.rejection_reason, "")

    def test_reject_shelter_with_reason(self):
        url = reverse("reject_shelter", args=[self.shelter.id])
        self.client.post(url, {"reason": "Invalid data"}, follow=True)

        self.shelter.refresh_from_db()
        self.assertEqual(self.shelter.status, "REJECTED")
        self.assertEqual(self.shelter.rejection_reason, "Invalid data")

    def test_reject_shelter_empty_reason_branch(self):
        url = reverse("reject_shelter", args=[self.shelter.id])
        self.client.post(url, {"reason": "   "}, follow=True)

        self.shelter.refresh_from_db()
        self.assertEqual(self.shelter.status, "REJECTED")
        self.assertEqual(self.shelter.rejection_reason, "")


# ----------------------------
# Stores approve/reject branches
# ----------------------------
class StoreApprovalTests(DashboardBaseTest):
    def setUp(self):
        super().setUp()
        self.store = Store.objects.create(
            owner=self.owner,
            name="Pet Store",
            status="PENDING"
        )

    def test_approve_store(self):
        url = reverse("approve_store", args=[self.store.id])
        self.client.post(url, follow=True)

        self.store.refresh_from_db()
        self.assertEqual(self.store.status, "APPROVED")

    def test_reject_store(self):
        url = reverse("reject_store", args=[self.store.id])
        self.client.post(url, follow=True)

        self.store.refresh_from_db()
        self.assertEqual(self.store.status, "REJECTED")


# ----------------------------
# User score branches
# ----------------------------
class UpdateUserScoreTests(DashboardBaseTest):
    def test_update_user_score_success(self):
        url = reverse("dashboard_update_user_score", args=[self.user.id])
        self.client.post(url, {"score": "250"}, follow=True)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.score, 250)

    def test_update_user_score_invalid_valueerror_branch(self):
        url = reverse("dashboard_update_user_score", args=[self.user.id])
        self.client.post(url, {"score": "abc"}, follow=True)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.score, 100)

    def test_update_user_score_clamp_branch(self):
        url = reverse("dashboard_update_user_score", args=[self.user.id])
        self.client.post(url, {"score": "999999"}, follow=True)

        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.score, 1000)

    def test_update_user_score_admin_blocked_branch(self):
        url = reverse("dashboard_update_user_score", args=[self.admin2.id])
        self.client.post(url, {"score": "10"}, follow=True)
        self.assertFalse(Profile.objects.filter(user=self.admin2).exists())


# ----------------------------
# Ban/unban branches (including "cannot ban self/admin")
# ----------------------------
class BanUnbanBranchTests(DashboardBaseTest):
    def test_ban_user_success(self):
        url = reverse("dashboard_ban_user", args=[self.user.id])
        self.client.post(url, follow=True)

        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertFalse(self.user.is_active)
        # ban reduces score by 50 in your view
        self.assertEqual(self.user.profile.score, 50)

    def test_ban_self_blocked_branch(self):
        url = reverse("dashboard_ban_user", args=[self.admin.id])
        self.client.post(url, follow=True)

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_ban_other_admin_blocked_branch(self):
        url = reverse("dashboard_ban_user", args=[self.admin2.id])
        self.client.post(url, follow=True)

        self.admin2.refresh_from_db()
        self.assertTrue(self.admin2.is_active)

    def test_unban_user_success(self):
        self.user.is_active = False
        self.user.save()

        url = reverse("dashboard_unban_user", args=[self.user.id])
        self.client.post(url, follow=True)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)


# ----------------------------
# Delete branches (including "cannot delete self/admin")
# ----------------------------
class DeleteUserBranchTests(DashboardBaseTest):
    def test_delete_user_success(self):
        url = reverse("dashboard_delete_user", args=[self.user.id])
        self.client.post(url, follow=True)

        self.assertFalse(User.objects.filter(id=self.user.id).exists())

    def test_delete_self_blocked_branch(self):
        url = reverse("dashboard_delete_user", args=[self.admin.id])
        self.client.post(url, follow=True)

        self.assertTrue(User.objects.filter(id=self.admin.id).exists())

    def test_delete_other_admin_blocked_branch(self):
        url = reverse("dashboard_delete_user", args=[self.admin2.id])
        self.client.post(url, follow=True)

        self.assertTrue(User.objects.filter(id=self.admin2.id).exists())
