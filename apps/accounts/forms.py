"""Authentication forms."""

from django import forms


class LoginForm(forms.Form):
    """Login form with username and password fields."""

    username = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Username',
            'id': 'username',
            'autocomplete': 'username',
        })
    )

    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Password',
            'id': 'password',
            'autocomplete': 'current-password',
        })
    )
