(function($, window, document, undefined) {
    window.djangoPasswordStrength = {
        config: {
            passwordClass: 'password_strength',
            confirmationClass: 'password_confirmation',
        },

        init: function (config) {
            var self = this;
            // Setup configuration
            if ($.isPlainObject(config)) {
                $.extend(self.config, config);
            }
        },

        initListeners: function(element) {
            var self = this;
            var body = $('body');
            var el;

            if (element) {
                el = $(element).find('.' + self.config.passwordClass);
            } else {
                el = $('.' + self.config.passwordClass);
            }

            el.on('keyup', function() {
                var password_strength_bar = $(this).closest('div').find('.password_strength_bar');
                var password_strength_info = $(this).closest('div').find('.password_strength_info');

                if( $(this).val() ) {
                    var result = zxcvbn( $(this).val() );

                    if( result.score < 3 ) {
                        password_strength_bar.removeClass('progress-bar-success').addClass('progress-bar-warning');
                        password_strength_info.find('.label').removeClass('hidden');
                    } else {
                        password_strength_bar.removeClass('progress-bar-warning').addClass('progress-bar-success');
                        password_strength_info.find('.label').addClass('hidden');
                    }

                    password_strength_bar.width( ((result.score+1)/5)*100 + '%' ).attr('aria-valuenow', result.score + 1);
                    password_strength_info.find('.password_strength_time').html(self.display_time(result.crack_time));
                    password_strength_info.removeClass('hidden');
                } else {
                    password_strength_bar.removeClass('progress-bar-success').addClass('progress-bar-warning');
                    password_strength_bar.width( '0%' ).attr('aria-valuenow', 0);
                    password_strength_info.addClass('hidden');
                }
                self.match_passwords($(this));
            });

            var timer = null;
            if (element) {
                el = $(element).find('.' + self.config.confirmationClass);
            } else {
                el = $('.' + self.config.confirmationClass);
            }
            el.on('keyup', function() {
                var password_field;
                var confirm_with = $(this).data('confirm-with');

                if( confirm_with ) {
                    password_field = $('#' + confirm_with);
                } else {
                    password_field = $('.' + self.config.passwordClass);
                }

                if (timer !== null) clearTimeout(timer);

                timer = setTimeout(function() {
                    self.match_passwords(password_field, el);
                }, 400);
            });
        },

        display_time: function(seconds) {
            var minute = 60;
            var hour = minute * 60;
            var day = hour * 24;
            var month = day * 31;
            var year = month * 12;
            var century = year * 100;

            // Provide fake gettext for when it is not available
            if ( typeof gettext !== 'function' ) { gettext = function(text) { return text; }; }

            if ( seconds < minute ) return gettext('only an instant');
            if ( seconds < hour) return (1 + Math.ceil(seconds / minute)) + ' ' + gettext('minutes');
            if ( seconds < day) return (1 + Math.ceil(seconds / hour)) + ' ' + gettext('hours');
            if ( seconds < month) return (1 + Math.ceil(seconds / day)) + ' ' + gettext('days');
            if ( seconds < year) return (1 + Math.ceil(seconds / month)) + ' ' + gettext('months');
            if ( seconds < century) return (1 + Math.ceil(seconds / year)) + ' ' + gettext('years');

            return 'centuries';
        },

        match_passwords: function(password_field, confirmation_fields) {
            var self = this;
            var password = password_field.val();

            // Optional parameter: if no specific confirmation field is given, check all
            if( confirmation_fields === undefined ) { confirmation_fields = $('.' + self.config.confirmationClass); }
            if( confirmation_fields === undefined ) { return; }

            confirmation_fields.each(function(index, confirm_field) {
                var confirm_value = $(confirm_field).val();
                var confirm_with = $(confirm_field).data('confirm-with');

                if( confirm_with && confirm_with == password_field.attr('id')) {
                    if( confirm_value && password ) {
                        if (confirm_value === password) {
                            $(confirm_field).closest('div').find('.password_strength_info').addClass('hidden');
                        } else {
                            $(confirm_field).closest('div').find('.password_strength_info').removeClass('hidden');
                        }
                    } else {
                        $(confirm_field).parent().find('.password_strength_info').addClass('hidden');
                    }
                }
            });

            // If a password field other than our own has been used, add the listener here
            if ( !password_field.hasClass(self.config.passwordClass) && !password_field.data('password-listener') ) {
                password_field.on('keyup', function() {
                    self.match_passwords($(this));
                });
                password_field.data('password-listener', true);
            }
        },
    };

    // Call the init for backwards compatibility
    djangoPasswordStrength.init();

})(jQuery, window, document);
