from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from .models import ContactMessage, Profile


class StudentRegistrationForm(UserCreationForm):
    full_name = forms.CharField(max_length=150)
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ["full_name", "username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data["full_name"].strip()
        first, _, last = full_name.partition(" ")
        user.first_name = first
        user.last_name = last
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class EmailOrUsernameLoginForm(forms.Form):
    identifier = forms.CharField(label="Username or Email")
    password = forms.CharField(widget=forms.PasswordInput)
    remember_me = forms.BooleanField(required=False)

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        identifier = cleaned.get("identifier")
        password = cleaned.get("password")
        if identifier and password:
            username = identifier
            if "@" in identifier:
                user = User.objects.filter(email__iexact=identifier).first()
                username = user.username if user else identifier
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise ValidationError("Please enter a valid username/email and password.")
        return cleaned

    def get_user(self):
        return self.user_cache


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()

    class Meta:
        model = Profile
        fields = ["avatar", "phone", "bio", "interests", "theme_preference"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.user.first_name
        self.fields["last_name"].initial = self.user.last_name
        self.fields["email"].initial = self.user.email

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        exists = User.objects.exclude(pk=self.user.pk).filter(email__iexact=email).exists()
        if exists:
            raise ValidationError("This email is already used by another account.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data["first_name"]
        self.user.last_name = self.cleaned_data["last_name"]
        self.user.email = self.cleaned_data["email"]
        if commit:
            self.user.save()
            profile.save()
        return profile


class StyledPasswordChangeForm(PasswordChangeForm):
    pass
