from .lily_search import LilySearch
from django.forms.models import model_to_dict

from lily.accounts.models import Account


def search_number(tenant_id, number):
    search = LilySearch(
        tenant_id=tenant_id,
        model_type='accounts_account',
        size=1,
    )

    # Try to find an account with the given phone number.
    search.filter_query('phone_numbers.number:"%s"' % number)

    hits, facets, total, took = search.do_search()
    if hits:
        account = Account.objects.get(pk=hits[0].get('id'))
        unfilteredContacts = [model_to_dict(contact) for contact in account.contacts.all()]
        contacts = [dict((x, contact[x]) for x in ('id', 'first_name', 'last_name')) for contact in unfilteredContacts]

        if contacts:
            return {
                'data': {
                    'accounts': [hits[0]],
                    'contacts': contacts
                },
            }
        else:
            return {
                'data': {
                    'accounts': [hits[0]]
                },
            }

    else:
        search = LilySearch(
            tenant_id=tenant_id,
            model_type='contacts_contact',
            size=1,
        )

        search.filter_query('phone_numbers.number:"%s"' % number)

        hits, facets, total, took = search.do_search()
        if hits:
            if hits[0].get('accounts'):
                return {
                    'data': {
                        'accounts': hits[0].get('accounts'),
                        'contacts': [hits[0]]
                    },
                }
            else:
                return {
                    'data': {
                        'contacts': [hits[0]]
                    },
                }

    return {}
