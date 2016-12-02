import json

from channels import Group
from django.contrib.staticfiles.templatetags.staticfiles import static
from rest_framework import viewsets
from rest_framework.decorators import list_route
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from lily.cases.models import Case
from lily.deals.models import Deal
from lily.users.models import LilyUser
from lily.search.functions import search_number
from lily.tenant.api.mixins import SetTenantUserMixin
from lily.utils.functions import parse_phone_number

from .serializers import CallSerializer
from ..models import Call


class CallViewSet(SetTenantUserMixin, viewsets.ModelViewSet):
    """
    Returns a list of all calls in the system.
    """
    # Set the queryset, without .all() this filters on the tenant and takes care of setting the `base_name`.
    queryset = Call.objects
    # Set the serializer class for this viewset.
    serializer_class = CallSerializer
    # Set all filter backends that this viewset uses.
    filter_backends = (OrderingFilter,)
    # OrderingFilter: set the default ordering fields.
    ordering = ('id',)

    def get_queryset(self):
        """
        Set the queryset here so it filters on tenant and works with pagination.
        """
        return super(CallViewSet, self).get_queryset().filter()

    def create(self, request, *args, **kwargs):
        instance = super(CallViewSet, self).create(request, *args, **kwargs)
        call = request.data
        calledUser = LilyUser.objects.filter(
            internal_number=call.get('internal_number'),
            tenant_id=request.user.tenant_id
        ).first()
        if calledUser:
            number = parse_phone_number(call.get('caller_number'))
            result = search_number(request.user.tenant_id, number)

            notificationData = {
                'title': '%s Calling' % number,
                'body': ''
            }

            data = result.get('data')
            if data:
                accounts = data.get('accounts')
                if accounts and len(accounts) == 1:
                    account = accounts[0]
                    notificationData.update({
                        'body': 'Phone number: %s' % number,
                        'icon': static('app/images/notification_icons/account.png'),
                        'link': {
                            'view': 'base.accounts.detail',
                            'id': account.get('id')
                        }
                    })

                    try:
                        deal = Deal.objects.filter(account_id=account.get('id'), is_archived=False).latest('created')
                        notificationData.update({
                            'body': 'Last deal: %s\n%s' % (
                                deal.created.strftime('%d-%m-%Y'),
                                notificationData.get('body')
                            ),
                        })
                    except Deal.DoesNotExist:
                        pass

                    try:
                        case = Case.objects.filter(account_id=account.get('id'), is_archived=False).latest('created')
                        notificationData.update({
                            'body': 'Last case: %s\n%s' % (
                                case.created.strftime('%d-%m-%Y'),
                                notificationData.get('body')
                            ),
                        })
                    except Case.DoesNotExist:
                        pass

                    if data.get('contacts'):
                        contacts = data.get('contacts')
                        if len(contacts) > 1:
                            notificationData.update({
                                'title': 'Somebody from %s Calling' % account.get('name'),
                            })
                        else:
                            notificationData.update({
                                'title': '%s %s from %s Calling' % (contacts[0].get('first_name'),
                                                                    contacts[0].get('last_name'),
                                                                    account.get('name')),
                            })
                    else:
                        notificationData.update({
                            'title': '%s Calling' % account.get('name'),
                        })
                else:
                    contact = data.get('contacts')[0]
                    notificationData.update({
                        'title': '%s %s Calling' % (contact.get('first_name'), contact.get('last_name')),
                        'body': 'Phone number: %s' % number,
                        'icon': static('app/images/notification_icons/contact.png'),
                        'link': {
                            'view': 'base.contacts.detail',
                            'id': contact.get('id')
                        }
                    })
            else:
                notificationData.update({
                    'icon': static('app/images/notification_icons/add-account.png'),
                    'link': {
                        'view': 'base.accounts.create',
                        'params': {
                            'phone_numbers': [{'number': number, 'type': 'work'}]
                        }
                    }
                })

                callerName = call.get('caller_name', '')
                if callerName != '':
                    notificationData.update({
                        'title': '%s Calling' % callerName,
                        'body': 'Phone number: %s' % number,
                        'link': {
                            'view': 'base.accounts.create',
                            'params': {
                                'name': callerName,
                                'phone_numbers': [{'number': number, 'type': 'work'}]
                            }
                        }
                    })

            Group("user-%s" % calledUser.id).send({
                "text": json.dumps({
                    'notification': notificationData
                })
            })

        return instance

    @list_route(methods=['GET'])
    def latest(self, request):
        """
        Gets the latest call of the current user based on internal number.
        """
        user = self.request.user
        internal_number = user.internal_number
        call = Call.objects.filter(internal_number=internal_number, status=Call.ANSWERED).last()

        if call:
            call = self.get_serializer(call).data

        return Response({'call': call})
