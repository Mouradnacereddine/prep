from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

class CustomUser(AbstractUser):
    """Custom user model."""
    email = models.EmailField(
        _('email address'),
        unique=True,
        error_messages={
            'unique': _('A user with that email already exists.'),
        },
    )
    employee_id = models.CharField(
        _('employee ID'),
        max_length=10,
        unique=True,
        help_text=_('Required. 10 characters or fewer.'),
    )
    department = models.CharField(
        _('department'),
        max_length=50,
        help_text=_('The department this user belongs to.'),
    )
    email_verified = models.BooleanField(
        _('email verified'),
        default=False,
    )
    email_verification_token = models.CharField(
        _('email verification token'),
        max_length=100,
        blank=True,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'employee_id', 'department']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['email']

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return the full name for the user."""
        full_name = f'{self.first_name} {self.last_name}'
        return full_name.strip() or self.email

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.email.split('@')[0]

    def generate_verification_token(self):
        """Generate a unique token for email verification"""
        token = str(uuid.uuid4())
        self.email_verification_token = token
        self.save()
        return token

    def verify_email(self, token):
        """Verify user's email with the given token"""
        if self.email_verification_token == token:
            self.email_verified = True
            self.email_verification_token = ''
            self.save()
            return True
        return False
