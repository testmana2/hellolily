/**
 * Router definition.
 */
angular.module('app.contacts').config(contactConfig);

contactConfig.$inject = ['$stateProvider'];
function contactConfig($stateProvider) {
    $stateProvider.state('base.contacts.create', {
        url: '/create',
        views: {
            '@': {
                templateUrl: 'contacts/controllers/form.html',
                controller: ContactCreateUpdateController,
                controllerAs: 'vm',
            },
        },
        ncyBreadcrumb: {
            label: 'Create',
        },
        resolve: {
            currentContact: function() {
                return null;
            },
        },
    });

    $stateProvider.state('base.contacts.detail.edit', {
        url: '/edit',
        views: {
            '@': {
                templateUrl: 'contacts/controllers/form.html',
                controller: ContactCreateUpdateController,
                controllerAs: 'vm',
            },
        },
        ncyBreadcrumb: {
            label: 'Edit',
        },
        resolve: {
            currentContact: ['Contact', '$stateParams', function(Contact, $stateParams) {
                var contactId = $stateParams.id;
                return Contact.get({id: contactId}).$promise;
            }],
        },
    });

    $stateProvider.state('base.contacts.create.fromAccount', {
        url: '/account/{accountId:[0-9]{1,}}',
        views: {
            '@': {
                templateUrl: 'contacts/controllers/form.html',
                controller: ContactCreateUpdateController,
                controllerAs: 'vm',
            },
        },
        ncyBreadcrumb: {
            skip: true,
        },
        resolve: {
            currentContact: function() {
                return null;
            },
        },
    });
}

/**
 * Controller to create a new contact.
 */
angular.module('app.contacts').controller('ContactCreateUpdateController', ContactCreateUpdateController);

ContactCreateUpdateController.$inject = ['$scope', '$state', '$stateParams', '$timeout', 'Account',
    'Contact', 'HLFields', 'HLForms', 'HLResource', 'HLSearch', 'Settings', 'currentContact'];
function ContactCreateUpdateController($scope, $state, $stateParams, $timeout, Account, Contact,
                                       HLFields, HLForms, HLResource, HLSearch, Settings, currentContact) {
    var vm = this;

    vm.contact = {};
    vm.errors = {
        name: [],
    };

    vm.saveContact = saveContact;
    vm.cancelContactCreation = cancelContactCreation;
    vm.addRelatedField = addRelatedField;
    vm.removeRelatedField = removeRelatedField;
    vm.refreshAccounts = refreshAccounts;
    vm.checkExistingContact = checkExistingContact;
    vm.mergeContactData = mergeContactData;

    activate();

    ////

    function activate() {
        _getContact();

        $timeout(function() {
            // Focus the first input on page load.
            angular.element('.form-control')[0].focus();
            $scope.$apply();
        });
    }

    function _getContact() {
        // Fetch the contact or create empty contact.
        if (currentContact) {
            vm.contact = currentContact;
            Settings.page.setAllTitles('edit', currentContact.full_name);

            if (vm.contact.hasOwnProperty('social_media') && vm.contact.social_media.length) {
                angular.forEach(vm.contact.social_media, function(profile) {
                    vm.contact[profile.name] = profile.username;
                });
            }
        } else {
            Settings.page.setAllTitles('create', 'contact');
            vm.contact = Contact.create();

            if ($stateParams.accountId) {
                Account.get({id: $stateParams.accountId}, function(account) {
                    vm.contact.accounts.push(account);
                    vm.account = account;
                });
            }

            if (Settings.email.data) {
                // Auto fill data if it's available
                if (Settings.email.data.contact) {
                    if (Settings.email.data.contact.firstName) {
                        vm.contact.first_name = Settings.email.data.contact.firstName;
                    }

                    if (Settings.email.data.contact.lastName) {
                        vm.contact.last_name = Settings.email.data.contact.lastName;
                    }

                    checkExistingContact();

                    if (Settings.email.data.contact.emailAddress) {
                        vm.contact.email_addresses.push({
                            email_address: Settings.email.data.contact.emailAddress,
                            status: 2,
                        });
                    }
                }

                if (Settings.email.data.account) {
                    vm.contact.accounts.push(Settings.email.data.account);
                }
            }
        }
    }

    function addRelatedField(field) {
        HLFields.addRelatedField(vm.contact, field);
    }

    function removeRelatedField(field, index, remove) {
        HLFields.removeRelatedField(vm.contact, field, index, remove);
    }

    function cancelContactCreation() {
        if (Settings.email.sidebar.form === 'contact') {
            Settings.email.sidebar.form = null;
            Settings.email.sidebar.contact = false;
        } else {
            if (Settings.page.previousState && !Settings.page.previousState.state.abstract) {
                // Check if we're coming from another page.
                $state.go(Settings.page.previousState.state, Settings.page.previousState.params);
            } else {
                $state.go('base.contacts');
            }
        }
    }

    function saveContact(form) {
        var accounts = [];
        var copiedContact;
        var twitterId;
        var linkedinId;

        // Check if a contact is being added via the + contact page or via
        // a supercard.
        if (Settings.email.sidebar.isVisible) {
            ga('send', 'event', 'Contact', 'Save', 'Email Sidebar');
        } else {
            if ($stateParams.accountId) {
                ga('send', 'event', 'Contact', 'Save', 'Account Widget');
            } else {
                ga('send', 'event', 'Contact', 'Save', 'Default');
            }
        }

        HLForms.blockUI();
        HLForms.clearErrors(form);

        // Store the ids of the current social media objects.
        angular.forEach(vm.contact.social_media, function(value) {
            if (value.name === 'twitter') {
                twitterId = value.id;
            } else if (value.name === 'linkedin') {
                linkedinId = value.id;
            }
        });

        vm.contact.social_media = [];
        if (vm.contact.twitter) {
            vm.contact.social_media.push({
                name: 'twitter',
                username: vm.contact.twitter,
            });
            // Re-use social media id in case of an edit.
            if (twitterId) {
                vm.contact.social_media[vm.contact.social_media.length - 1].id = twitterId;
            }
        }

        if (vm.contact.linkedin) {
            vm.contact.social_media.push({
                name: 'linkedin',
                username: vm.contact.linkedin,
            });
            // Re-use social media ids in case of an edit.
            if (linkedinId) {
                vm.contact.social_media[vm.contact.social_media.length - 1].id = linkedinId;
            }
        }

        vm.contact = HLFields.cleanRelatedFields(vm.contact);

        copiedContact = angular.copy(vm.contact);

        if (copiedContact.accounts && copiedContact.accounts.length) {
            angular.forEach(copiedContact.accounts, function(account) {
                if (account) {
                    accounts.push({id: account.id});
                }
            });

            copiedContact.accounts = accounts;
        }

        if (copiedContact.id) {
            // If there's an ID set it means we're dealing with an existing contact, so update it
            copiedContact.$update(function() {
                toastr.success('I\'ve updated the contact for you!', 'Done');
                $state.go('base.contacts.detail', {id: copiedContact.id}, {reload: true});
            }, function(response) {
                _handleBadResponse(response, form);
            });
        } else {
            copiedContact.$save(function() {
                toastr.success('I\'ve saved the contact for you!', 'Yay');

                _postSave(copiedContact);
            }, function(response) {
                _handleBadResponse(response, form);
            });
        }
    }

    function refreshAccounts(query) {
        var accountsPromise;

        if (!vm.accounts || query.length) {
            accountsPromise = HLSearch.refreshList(query, 'Account');

            if (accountsPromise) {
                accountsPromise.$promise.then(function(data) {
                    vm.accounts = data.objects;
                });
            }
        }
    }

    function checkExistingContact() {
        var fullName;

        if (!vm.contact.id && vm.contact.first_name && vm.contact.last_name) {
            fullName = vm.contact.first_name + ' ' + vm.contact.last_name;

            Contact.search({filterquery: 'full_name:"' + fullName + '"'}).$promise.then(function(results) {
                vm.contactSuggestions = results.objects;
            });
        }
    }

    function mergeContactData(contact) {
        var args = {
            id: contact.id,
            accounts: [],
            email_addresses: vm.contact.email_addresses,
        };

        angular.forEach(vm.contact.accounts, function(account) {
            if (account) {
                args.accounts.push({id: account.id});
            }
        });

        HLResource.patch('Contact', args).$promise.then(function() {
            _postSave(contact);
        });
    }

    function _postSave(contact) {
        new Intercom('trackEvent', 'contact-created');

        if (Settings.email.sidebar.form === 'contact') {
            Settings.email.sidebar.form = null;
            Settings.email.sidebar.contact = true;
            Settings.email.data.contact = contact;
        } else {
            if ($stateParams.accountId) {
                // Redirect back to account if contact was created from the account page.
                $state.go('base.accounts.detail', {id: $stateParams.accountId}, {reload: true});
            } else {
                $state.go('base.contacts.detail', {id: contact.id}, {reload: true});
            }
        }
    }

    $scope.$watch('vm.contact.accounts', function() {
        if (vm.contact.accounts) {
            if (vm.contact.accounts.length === 1) {
                Account.get({id: vm.contact.accounts[0].id}, function(account) {
                    if (!vm.account || vm.account.id !== account.id) {
                        vm.account = account;
                    }
                });
            } else if (vm.contact.accounts.length === 0) {
                vm.account = null;
            }
        }
    }, true);

    function _handleBadResponse(response, form) {
        HLForms.setErrors(form, response.data);

        toastr.error('Uh oh, there seems to be a problem', 'Oops!');
    }

    $scope.$on('saveContact', function() {
        saveContact($scope.contactForm);
    });
}
