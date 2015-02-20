from django import forms
from django.contrib import messages
from django.contrib.auth.forms import PasswordResetForm, AuthenticationForm, SetPasswordForm
from django.contrib.auth.hashers import is_password_usable
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.urlresolvers import reverse
from django.forms import TextInput
from django.forms.formsets import BaseFormSet
from django.template import loader
from django.utils.http import int_to_base36
from django.utils.translation import ugettext_lazy as _
from django_password_strength.widgets import PasswordStrengthInput, PasswordConfirmationInput
from lily.socialmedia.connectors import LinkedIn, Twitter
from lily.socialmedia.models import SocialMedia

from lily.tenant.middleware import get_current_user
from lily.utils.forms import HelloLilyForm, HelloLilyModelForm
from lily.utils.forms.widgets import JqueryPasswordInput, AddonTextInput

from .models import LilyUser


class CustomAuthenticationForm(AuthenticationForm):
    """
    This form is a subclass from the default AuthenticationForm. Necessary to set CSS classes and
    custom error_messages.
    """
    error_messages = {
        'invalid_login': _("Please enter a correct e-mail address and password. "
                           "Note that both fields are case-sensitive."),
        'no_cookies': _("Your Web browser doesn't appear to have cookies "
                        "enabled. Cookies are required for logging in."),
        'inactive': _("This account is inactive."),
    }

    username = forms.CharField(
        label=_('Email address'),
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control placeholder-no-fix',
            'autocomplete': 'off',
            'placeholder': _('Email address'),
        })
    )
    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control placeholder-no-fix',
            'autocomplete': 'off',
            'placeholder': _('Password'),
        })
    )
    remember_me = forms.BooleanField(label=_('Remember me on this device'), required=False)


class CustomPasswordResetForm(PasswordResetForm):
    """
    This form is a subclass from the default PasswordResetForm.
    LilyUser is used for validation instead of User.
    """
    error_messages = {
        'unknown': _("That e-mail address doesn't have an associated user account. Are you sure you've registered?"),
        'unusable': _("The user account associated with this e-mail address cannot reset the password."),
        'inactive_error_message': _('You cannot request a password reset for an account that is inactive.'),
    }

    email = forms.EmailField(
        label=_('Email address'),
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control placeholder-no-fix',
            'placeholder': _('Email address'),
        })
    )

    def form_valid(self, form):
        """
        Overloading super().form_valid to add a message telling an e-mail was sent.
        """

        # Send e-mail
        super(CustomPasswordResetForm, self).form_valid(form)

        # Show message
        messages.info(
            self.request,
            _('An <nobr>e-mail</nobr> with reset instructions has been sent to %s.') % form.cleaned_data['email']
        )

        return self.get_success_url()

    def clean_email(self):
        """
        Validates that an active user exists with the given email address.
        """
        email = self.cleaned_data["email"]
        self.users_cache = LilyUser.objects.filter(email__iexact=email, is_active=True)

        if not len(self.users_cache):
            raise forms.ValidationError(self.error_messages['unknown'])
        else:
            for user in self.users_cache:
                if not user.is_active:
                    raise forms.ValidationError(self.error_messages['inactive_error_message'])
        if any((is_password_usable(user.password)) for user in self.users_cache):
            raise forms.ValidationError(self.error_messages['unusable'])
        return email

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None):
        """
        Overloading super().save to use a custom email_template_name.
        """
        email_template_name = 'email/password_reset.email'
        for user in self.users_cache:
            if not domain_override:
                current_site = get_current_site(request)
                site_name = current_site.name
                domain = current_site.domain
            else:
                site_name = domain = domain_override
            context_data = {
                'email': user.email,
                'domain': domain,
                'site_name': site_name,
                'uid': int_to_base36(user.id),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': use_https and 'https' or 'http',
            }
            subject = loader.render_to_string(subject_template_name, context_data)
            # Email subject *must not* contain newlines
            subject = ''.join(subject.splitlines())
            email = loader.render_to_string(email_template_name, context_data)
            send_mail(subject, email, from_email, [str(user.email)])


class CustomSetPasswordForm(SetPasswordForm):
    """
    This form is a subclass from the default SetPasswordForm.
    LilyUser is used for validation instead of User.
    """
    new_password1 = forms.CharField(label=_('New password'), widget=JqueryPasswordInput())
    new_password2 = forms.CharField(label=_('Confirmation'), widget=forms.PasswordInput())


class ResendActivationForm(HelloLilyForm):
    """
    Form that allows a user to retry sending the activation e-mail.
    """
    error_messages = {
        'unknown': _("That e-mail address doesn't have an associated user account. Are you sure you've registered?"),
        'active': _("You cannot request a new activation e-mail for an account that is already active."),
    }

    email = forms.EmailField(label=_('E-mail address'), max_length=255)

    def clean_email(self):
        """
        Validates that an active user exists with the given email address.
        """
        email = self.cleaned_data['email']
        users_cache = LilyUser.objects.filter(email__iexact=email)
        if not len(users_cache):
            raise ValidationError(code='invalid', message=self.error_messages['unknown'])
        else:
            for user in users_cache:
                if user.is_active:
                    raise ValidationError(code='invalid', message=self.error_messages['active'])
        return email


class RegistrationForm(HelloLilyForm):
    """
    This form allows new user registration.
    """
    email = forms.EmailField(label=_('E-mail'), max_length=255)
    password = forms.CharField(
        label=_('Password'),
        min_length=6,
        widget=JqueryPasswordInput(attrs={
            'placeholder': _('Password')
        })
    )
    password_repeat = forms.CharField(
        label=_('Password confirmation'),
        min_length=6,
        widget=forms.PasswordInput(attrs={
            'placeholder': _('Password confirmation')
        })
    )
    first_name = forms.CharField(label=_('First name'), max_length=255)
    preposition = forms.CharField(label=_('Preposition'), max_length=100, required=False)
    last_name = forms.CharField(label=_('Last name'), max_length=255)

    def clean_email(self):
        if LilyUser.objects.filter(email__iexact=self.cleaned_data['email']).exists():
            raise ValidationError(code='invalid', message=_('E-mail address already in use.'))
        else:
            return self.cleaned_data['email']

    def clean(self):
        """
        Form validation: passwords should match and email should be unique.
        """
        cleaned_data = super(RegistrationForm, self).clean()

        password = cleaned_data['password']
        password_repeat = cleaned_data['password_repeat']

        if password != password_repeat:
            self._errors['password'] = self.error_class([_('The two password fields didn\'t match.')])

        return cleaned_data


class UserRegistrationForm(RegistrationForm):
    """
    Form for accepting invitations.
    """
    email = forms.EmailField(
        label=_('E-mail'),
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'mws-register-email disabled',
            'readonly': 'readonly',
        })
    )

    def clean_email(self):
        if self.cleaned_data['email'] != self.initial['email']:
            raise ValidationError(code='invalid', message=_('You can\'t change the e-mail address of the invitation.'))
        else:
            return self.cleaned_data['email']


class InvitationForm(HelloLilyForm):
    """
    This is the invitation form, it is used to invite new users to join an account.
    """
    first_name = forms.CharField(
        label=_('First name'),
        max_length=255,
        widget=forms.TextInput(attrs={
            'placeholder': _('First name')
        })
    )
    email = forms.EmailField(
        label=_('E-mail'),
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': _('Email Adress')
        })
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            LilyUser.objects.get(email__iexact=email)
        except LilyUser.DoesNotExist:
            return email
        else:
            raise ValidationError(code='invalid', message=_('This e-mail address is already linked to a user.'))


# ------------------------------------------------------------------------------------------------
# Formsets
# ------------------------------------------------------------------------------------------------
class RequiredFirstFormFormset(BaseFormSet):
    """
    This formset requires that the first form that is submitted is filled in.
    """
    def __init__(self, *args, **kwargs):
        super(RequiredFirstFormFormset, self).__init__(*args, **kwargs)

        try:
            self.forms[0].empty_permitted = False
        except IndexError:
            print "index error bij de init van required first form formset"

    def clean(self):
        if self.total_form_count() < 1:
            raise forms.ValidationError(_("We need some data before we can proceed. Fill out at least one form."))


class RequiredFormset(BaseFormSet):
    """
    This formset requires all the forms that are submitted are filled in.
    """
    # TODO: check the extra parameter to statisfy that all initial forms are filled in.
    def __init__(self, *args, **kwargs):
        super(RequiredFormset, self).__init__(*args, **kwargs)
        for form in self.forms:
            form.empty_permitted = False


class InvitationFormset(RequiredFirstFormFormset):
    """
    This formset is sending invitations to users based on e-mail addresses.
    """
    def clean(self):
        """Checks that no two email addresses are the same."""
        super(InvitationFormset, self).clean()

        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        emails = []
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            email = form.cleaned_data['email']
            if email and email in emails:
                raise ValidationError(
                    code='invalid',
                    message=_('You can\'t invite someone more than once (e-mail addresses must be unique).')
                )
            emails.append(email)


class UserProfileForm(HelloLilyModelForm):
    twitter = forms.CharField(
        label=_('Twitter'),
        required=False,
        widget=AddonTextInput(
            icon_attrs={
                'class': 'icon-twitter',
                'position': 'left',
                'is_button': False
            }
        )
    )

    linkedin = forms.CharField(
        label=_('LinkedIn'),
        required=False,
        widget=AddonTextInput(
            icon_attrs={
                'class': 'icon-linkedin',
                'position': 'left',
                'is_button': False
            }
        )
    )

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)

        if self.instance.pk:
            twitter = self.instance.social_media.filter(name='twitter').first()
            self.fields['twitter'].initial = twitter.username if twitter else ''
            linkedin = self.instance.social_media.filter(name='linkedin').first()
            self.fields['linkedin'].initial = linkedin.username if linkedin else ''

    def clean_twitter(self):
        """
        Check if added twitter name or url is valid.

        Returns:
            string: twitter username or empty string.
        """
        twitter = self.cleaned_data.get('twitter')

        if twitter:
            try:
                twit = Twitter(twitter)
            except ValueError:
                raise ValidationError(_('Please enter a valid username or link'), code='invalid')
            else:
                return twit.username
        return twitter

    def clean_linkedin(self):
        """
        Check if added linkedin url is a valid linkedin url.

        Returns:
            string: linkedin username or empty string.
        """
        linkedin = self.cleaned_data['linkedin']

        if linkedin:
            try:
                lin = LinkedIn(linkedin)
            except ValueError:
                raise ValidationError(_('Please enter a valid username or link'), code='invalid')
            else:
                return lin.username

        return linkedin

    def save(self, commit=True):
        """
        Save contact to instance, and to database if commit is True.

        Returns:
            instance: an instance of the contact model
        """
        instance = super(UserProfileForm, self).save(commit)

        if commit:
            twitter_input = self.cleaned_data.get('twitter')
            linkedin_input = self.cleaned_data.get('linkedin')

            if twitter_input and instance.social_media.filter(name='twitter').exists():
                # There is input and there are one or more twitters connected, so we get the first of those.
                twitter_queryset = self.instance.social_media.filter(name='twitter')
                if self.fields['twitter'].initial:  # Only filter on initial if there is initial data.
                    twitter_queryset = twitter_queryset.filter(username=self.fields['twitter'].initial)
                twitter_instance = twitter_queryset.first()

                # And we edit it to store our new input.
                twitter = Twitter(self.cleaned_data.get('twitter'))
                twitter_instance.username = twitter.username
                twitter_instance.profile_url = twitter.profile_url
                twitter_instance.save()
            elif twitter_input:
                # There is input but no connected twitter, so we create a new one.
                twitter = Twitter(self.cleaned_data.get('twitter'))
                twitter_instance = SocialMedia.objects.create(
                    name='twitter',
                    username=twitter.username,
                    profile_url=twitter.profile_url,
                )
                instance.social_media.add(twitter_instance)
            else:
                # There is no input and zero or more connected twitters, so we delete them all.
                instance.social_media.filter(name='twitter').delete()

            if linkedin_input and instance.social_media.filter(name='linkedin').exists():
                # There is input and there are one or more linkedins connected, so we get the first of those.
                linkedin_instance = self.instance.social_media.filter(name='linkedin')
                if self.fields['linkedin'].initial:  # Only filter on initial if there is initial data.
                    linkedin_instance = linkedin_instance.filter(username=self.fields['linkedin'].initial)
                linkedin_instance = linkedin_instance.first()

                # And we edit it to store our new input.
                linkedin = LinkedIn(self.cleaned_data.get('linkedin'))
                linkedin_instance.username = linkedin.username
                linkedin_instance.profile_url = linkedin.profile_url
                linkedin_instance.save()
            elif linkedin_input:
                # There is input but no connected linkedin, so we create a new one.
                linkedin = LinkedIn(self.cleaned_data.get('linkedin'))
                linkedin_instance = SocialMedia.objects.create(
                    name='linkedin',
                    username=linkedin.username,
                    profile_url=linkedin.profile_url,
                )
                instance.social_media.add(linkedin_instance)
            else:
                # There is no input and zero or more connected twitters, so we delete them all.
                instance.social_media.filter(name='linkedin').delete()

        return instance

    class Meta:
        model = LilyUser
        fieldsets = [
            (_('Personal information'), {
                'fields': [
                    'first_name',
                    'preposition',
                    'last_name',
                ],
            }),
            (_('Contact information'), {
                'fields': [
                    'phone_number',
                    'twitter',
                    'linkedin',
                ],
            }),
            (_('Language and time'), {
                'fields': [
                    'language',
                    'timezone',
                ],
            }),
        ]


class UserAccountForm(HelloLilyModelForm):
    old_password = forms.CharField(label=_('Current password'), widget=forms.PasswordInput())
    new_password1 = forms.CharField(label=_('New password'), widget=PasswordStrengthInput(), required=False)
    new_password2 = forms.CharField(
        label=_('Confirm new password'),
        widget=PasswordConfirmationInput(confirm_with='new_password1'),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(UserAccountForm, self).__init__(*args, **kwargs)

        self.fields['email'].required = False
        self.fields['old_password'].help_text = '<a href="%s" tabindex="-1">%s</a>' % (
            reverse('password_reset'),
            unicode(_('Forgot your password?'))
        )

    def clean(self):
        cleaned_data = super(UserAccountForm, self).clean()
        new_password1 = cleaned_data.get('new_password1')
        new_password2 = cleaned_data.get('new_password2')

        if new_password1 or new_password2:
            if not new_password1 == new_password2:
                self._errors["new_password2"] = self.error_class([_('Your passwords don\'t match.')])

        return cleaned_data

    def clean_old_password(self):
        old_password = self.cleaned_data['old_password']
        logged_in_user = get_current_user()

        if not logged_in_user.check_password(old_password):
            self._errors["old_password"] = self.error_class([_('Password is incorrect.')])

        return old_password

    def save(self, commit=True):
        new_password = self.cleaned_data.get('new_password1')
        if new_password:
            logged_in_user = get_current_user()
            logged_in_user.set_password(new_password)
            logged_in_user.save()

        return super(UserAccountForm, self).save(commit)

    class Meta:
        model = LilyUser
        fieldsets = [
            (_('Change your email address'), {
                'fields': ['email', ],
            }), (_('Change your password'), {
                'fields': ['new_password1', 'new_password2', ],
            }), (_('Confirm your password'), {
                'fields': ['old_password', ],
            })
        ]
