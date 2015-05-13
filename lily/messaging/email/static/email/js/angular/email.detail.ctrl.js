(function(){
    'use strict';

    angular.module('app.email').config(emailConfig);
    emailConfig.$inject = ['$stateProvider'];
    function emailConfig ($stateProvider){
        $stateProvider.state('base.email.detail', {
            url: '/detail/{id:[0-9]{1,}}',
            views: {
                '@base.email': {
                    templateUrl: 'email/email_detail.html',
                    controller: 'EmailDetail',
                    controllerAs: 'vm'
                }
            }
        });
    }

    /**
     * EmailDetail controller to show an emailmessage
     */
    angular.module('app.email').controller('EmailDetail', EmailDetail);


    EmailDetail.$inject = ['$scope', '$state', '$stateParams', 'EmailMessage', 'SelectedEmailAccount'];
    function EmailDetail ($scope, $state, $stateParams, EmailMessage, SelectedEmailAccount) {
        var vm = this;
        vm.displayAllRecipients = false;
        vm.message = null;
        vm.archiveMessage = archiveMessage;
        vm.trashMessage = trashMessage;
        vm.deleteMessage = deleteMessage;
        vm.toggleOverlay = toggleOverlay;
        vm.markAsUnread = markAsUnread;

        $scope.conf.pageTitleBig = 'Email message';
        $scope.conf.pageTitleSmall = 'sending love through the world!';

        activate();

        //////

        function activate() {
            _getMessage();
        }

        function _getMessage() {
            EmailMessage.get({id: $stateParams.id}, function(result) {
                if (result.body_html) {
                    result.bodyHTMLUrl = '/messaging/email/html/' + result.id + '/';
                }
                vm.message = result;
                // It's easier to iterate through a single array, so make an array with all recipients
                vm.message.all_recipients = result.received_by.concat(result.received_by_cc);

                if (!result.read) {
                    EmailMessage.markAsRead($stateParams.id, true);
                }
                // Store current email account
                SelectedEmailAccount.setCurrentAccountId(vm.message.account);
            });
        }

        function archiveMessage() {
            EmailMessage.archive({id: vm.message.id}).$promise.then(function () {
                $state.go('base.email.list', { 'labelId': 'INBOX' });
            });
        }

        function trashMessage() {
            EmailMessage.trash({id: vm.message.id}).$promise.then(function () {
                $state.go('base.email.list', { 'labelId': 'INBOX' });
            });
        }

        function deleteMessage () {
            EmailMessage.delete({id: vm.message.id}).$promise.then(function () {
                $state.go('base.email.list', { 'labelId': 'INBOX' });
            });
        }

        function toggleOverlay () {
            vm.displayAllRecipients = !vm.displayAllRecipients;

            var $emailRecipients = $('.email-recipients');

            if (vm.displayAllRecipients) {
                $emailRecipients.height($emailRecipients[0].scrollHeight);
            } else {
                $emailRecipients.height('1.30em');
            }
        }

        function markAsUnread() {
            EmailMessage.markAsRead(vm.message.id, false).$promise.then(function () {
                $state.go('base.email.list', { 'labelId': 'INBOX' });
            });
        }
    }
})();
