from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class OpenRedirectTest(TestCase):
    """H-1: next= URL must be validated to prevent open redirect."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser', password='testpassword123',
            is_superuser=True,
        )
        self.login_url = reverse('accounts:login')

    def test_safe_relative_next_redirects_correctly(self):
        response = self.client.post(
            f'{self.login_url}?next=/reports/',
            {'username': 'testuser', 'password': 'testpassword123'},
        )
        self.assertRedirects(response, '/reports/', fetch_redirect_response=False)

    def test_absolute_external_next_falls_back_to_home(self):
        response = self.client.post(
            f'{self.login_url}?next=https://evil.com/steal',
            {'username': 'testuser', 'password': 'testpassword123'},
        )
        self.assertRedirects(response, '/', fetch_redirect_response=False)

    def test_protocol_relative_next_falls_back_to_home(self):
        response = self.client.post(
            f'{self.login_url}?next=//evil.com/steal',
            {'username': 'testuser', 'password': 'testpassword123'},
        )
        self.assertRedirects(response, '/', fetch_redirect_response=False)

    def test_missing_next_redirects_to_home(self):
        response = self.client.post(
            self.login_url,
            {'username': 'testuser', 'password': 'testpassword123'},
        )
        self.assertRedirects(response, '/', fetch_redirect_response=False)
