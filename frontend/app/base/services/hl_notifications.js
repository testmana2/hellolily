angular.module('app.services').service('HLNotifications', HLNotifications);

HLNotifications.$inject = ['$state', 'LocalStorage'];
function HLNotifications($state, LocalStorage) {
    var storage = new LocalStorage('notificationTab');

    var timestamp = storage.getObjectValue('timestamp', false);
    var dateNow = new Date();
    var sendNotification = false;

    _notificationTabCheck();

    this.send = function(data) {
        _notificationTabCheck();
        if (sendNotification) {
            if (!('Notification' in window)) {
                toastr.error('This browser does not support desktop notification');
            } else if (Notification.permission === 'granted') {
                _makeNotification(data);
            } else if (Notification.permission !== 'denied') {
                Notification.requestPermission(function(permission) {
                    if (permission === 'granted') {
                        _makeNotification(data);
                    }
                });
            }
        }
    };

    function _makeNotification(data) {
        var notification = new Notification(data.title, {body: data.body, icon: data.icon});
        setTimeout(function() { notification.close(); }, 4000);

        notification.onclick = function() {
            if ('link' in data) {
                window.focus();
                if ('id' in data.link) {
                    $state.go(data.link.view, {id: data.link.id}, {reload: true});
                } else if ('params' in data.link) {
                    $state.go(data.link.view, data.link.params, {reload: true});
                }
            }
            ga('send', 'event', 'Caller info', 'Open', 'Popup');
        };
    }

    function _notificationTabCheck() {
        dateNow = new Date();
        timestamp = storage.getObjectValue('timestamp', false);
        if (!timestamp || timestamp < dateNow.getTime() - 3000) {
            storage.putObjectValue('timestamp', dateNow.getTime());
            sendNotification = true;
            setInterval(function() {
                dateNow = new Date();
                storage.putObjectValue('timestamp', dateNow.getTime());
            }, 1000);
        }
    }
}
