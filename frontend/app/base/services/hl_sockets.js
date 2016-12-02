angular.module('app.services').service('HLSockets', HLSockets);

HLSockets.$inject = ['$state', '$timeout', '$rootScope', 'Settings', 'HLNotifications'];
function HLSockets($state, $timeout, $rootScope, Settings, HLNotifications) {
    var wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    var ws = new ReconnectingWebSocket(wsScheme + '://' + window.location.host + '/');

    var heartbeatContent = '❤️';
    var heartbeatInterval = null;
    var heartbeatMissed = 0;

    ws.onopen = function() {
        heartbeatMissed = 0;
        heartbeatInterval = setInterval(function() {
            try {
                heartbeatMissed++;
                if (heartbeatMissed >= 5) {
                    throw new Error('Too many missed heartbeats.');
                }
                ws.send(heartbeatContent);
            } catch (e) {
                clearInterval(heartbeatInterval);
                heartbeatInterval = null;
                ws.refresh();
            }
        }, 45000);
    };

    ws.onmessage = function(message) {
        if (message.data === heartbeatContent) {
            heartbeatMissed = 0;
            return;
        }
        listener(JSON.parse(message.data));
        ga('send', 'event', 'Caller info', 'Answer', 'Incoming call');
    };

    function listener(data) {
        if ('notification' in data) {
            HLNotifications.send(data.notification);
        }
    }
}
