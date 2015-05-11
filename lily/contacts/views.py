import anyjson
from django.contrib import messages
from django.db.models.query_utils import Q
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from django.views.generic import View
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from lily.search.lily_search import LilySearch
from lily.utils.functions import is_ajax
from lily.utils.views.mixins import LoginRequiredMixin, ExportListViewMixin

from .forms import CreateUpdateContactForm
from .models import Contact, Function


class ExportContactView(LoginRequiredMixin, ExportListViewMixin, View):

    http_method_names = ['get']
    file_name = 'contacts.csv'

    # ExportListViewMixin
    exportable_columns = {
        'id': {
            'headers': [_('ID')],
            'columns_for_item': ['id']
        },
        'name': {
            'headers': [_('Name')],
            'columns_for_item': ['name']
        },
        'contactInformation': {
            'headers': [
                _('Email'),
                _('Work Phone'),
                _('Mobile Phone'),
            ],
            'columns_for_item': [
                'email',
                'phone_work',
                'phone_mobile',
            ]
        },
        'worksAt': {
            'headers': [_('Works at')],
            'columns_for_item': ['accounts']
        },
        'created': {
            'headers': [_('Created')],
            'columns_for_item': ['created']
        },
        'modified': {
            'headers': [_('Modified')],
            'columns_for_item': ['modified']
        },
        'tags': {
            'headers': [_('Tags')],
            'columns_for_item': ['tag']
        },
    }

    # ExportListViewMixin
    def value_for_column(self, contact, column):
        try:
            if column == 'accounts':
                # 'accounts' is a dict, so we need to process it differently
                value = []
                for account in contact.get('accounts', []):
                    value.append(account['name'])
            else:
                value = contact[column]

            if isinstance(value, list):
                value = ', '.join(value)
        except KeyError:
            value = ''
        return value

    # ExportListViewMixin
    def get_items(self):
        search = LilySearch(
            tenant_id=self.request.user.tenant_id,
            model_type='contacts_contact',
            page=0,
            size=1000000000,
        )

        if self.request.GET.get('export_filter'):
            search.query_common_fields(self.request.GET.get('export_filter'))
        return search.do_search()[0]


class CreateUpdateContactMixin(LoginRequiredMixin):
    """
    Base class for AddAContactView and EditContactView.
    """
    template_name = 'contacts/contact_form.html'
    form_class = CreateUpdateContactForm

    def get_context_data(self, **kwargs):
        """
        Provide a url to go back to.
        """
        kwargs = super(CreateUpdateContactMixin, self).get_context_data(**kwargs)
        kwargs.update({
            'back_url': self.get_success_url(),
        })

        return kwargs

    def form_valid(self, form):
        """
        Save m2m relations to edited contact (i.e. Phone numbers, E-mail addresses and Addresses).
        """
        success_url = super(CreateUpdateContactMixin, self).form_valid(form)

        # Show save message
        messages.success(self.request, _('%s (Contact) has been %s.') % (self.object.full_name(), self.action))

        return success_url


class AddContactView(CreateUpdateContactMixin, CreateView):
    """
    View to add a contact. Also supports a smaller (quickbutton) form for ajax requests.
    """
    action = 'saved'

    def get_form_kwargs(self):
        kwargs = super(AddContactView, self).get_form_kwargs()
        kwargs.update({
            'formset_form_attrs': {
                'addresses': {
                    'exclude_address_types': ['visiting'],
                    'extra_form_kwargs': {
                        'initial': {
                            'type': 'home',
                        }
                    }
                }
            }
        })
        return kwargs

    def form_invalid(self, form):
        """
        Overloading super().form_invalid to mark the primary checkbox for e-mail addresses as
        checked for postbacks.
        """
        return super(AddContactView, self).form_invalid(form)

    def get_success_url(self):
        """
        Get the url to redirect to after this form has succesfully been submitted.
        """
        if self.object:
            return '/#/contacts/' + str(self.object.id)
        else:
            return '/#contacts'


class EditContactView(CreateUpdateContactMixin, UpdateView):
    """
    View to edit a contact.
    """
    model = Contact
    action = 'edited'

    def get_success_url(self):
        """
        Get the url to redirect to after this form has succesfully been submitted.
        """
        # return '%s?order_by=5&sort_order=desc' % (reverse('contact_list'))
        return '/#/contacts/%s' % self.object.pk


class DeleteContactView(LoginRequiredMixin, DeleteView):
    """
    Delete an instance and all instances of m2m relationships.
    """
    model = Contact
    success_url = '/#/contacts'

    def delete(self, request, *args, **kwargs):
        """
        Overloading super().delete to remove the related models and the instance itself.
        """
        self.object = self.get_object()
        self.object.email_addresses.remove()
        self.object.addresses.remove()
        self.object.phone_numbers.remove()
        self.object.tags.remove()

        functions = Function.objects.filter(contact=self.object)
        functions.delete()

        # Show delete message
        messages.success(self.request, _('%s (Contact) has been deleted.') % self.object.full_name())

        self.object.delete()

        redirect_url = self.get_success_url()
        if is_ajax(request):
            response = anyjson.serialize({
                'error': False,
                'redirect_url': redirect_url
            })
            return HttpResponse(response, content_type='application/json')

        return redirect(redirect_url)
