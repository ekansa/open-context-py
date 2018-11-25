#!/usr/bin/env python
from django.conf import settings


class RequestNegotiation():
    """ Useful methods for Open Context 
        to do some simple content negotiation
    """

    def __init__(self, default_type='text/html'):
        self.default_type = default_type  # the default mime-type supported
        self.supported_types = []  # other types supported
        self.supported = True
        self.use_response_type = default_type  # use this response type
        self.error_message = False

    def anonymize_request(self, request):
        """ anonymizes a request by flushing session cookies for users
            that are not logged in
        """
        if not request.user.is_authenticated():
            # the user is not authenticated, therefore
            # we will default to expire the session cookie for a user after the default
            pass
            # request.session.set_expiry((24 * 60 * 60))  # expire in a day
            # request.session.flush()
            # request.session.clear()
        return request
    
    def anonymize_response(self, request, response):
        """ anonymizes a response by deleting cookies for users
            that are not logged in
        """
        if not request.user.is_authenticated():
            if settings.SESSION_COOKIE_NAME in request.COOKIES:
                response.delete_cookie(
                    settings.SESSION_COOKIE_NAME,
                    path=settings.SESSION_COOKIE_PATH,
                    domain=settings.SESSION_COOKIE_DOMAIN,
                )
        return response

    def check_request_support(self, raw_client_accepts):
        """ check to see if the client_accepts
            mimetypes are supported by
            this part of Open Context
        """
        client_accepts = str(raw_client_accepts)
        if '*/*' in client_accepts:
            # client happy to accept all
            self.use_response_type = self.default_type
        elif ('text/*' in client_accepts \
             or 'text/plain' in client_accepts) \
             and 'text/' in self.default_type:
            self.use_response_type = self.default_type
        elif (self.default_type in client_accepts and
              client_accepts.startswith('application/ld+json') and
              'application/ld+json' in self.supported_types):
            # This satisfies the JSON-LD playground, which is OK
            # with both json and json-ld media types, but which
            # will only get JSON, so may get upset with list-of-list
            # GeoJSON features which normal people are OK with.
            self.use_response_type = 'application/ld+json' 
        elif self.default_type in client_accepts:
            # client accepts our default
            self.use_response_type = self.default_type
        else:
            # a more selective client, probably wanting
            # a machine-readable representation
            self.use_response_type = False
            client_accepts_len = len(client_accepts)
            for support_type in self.supported_types:
                # print('Support type: ' + str(support_type) + ' in ' + client_accepts)
                if len(support_type) <= client_accepts_len:
                    if support_type == client_accepts:
                        # we do support the alternative
                        self.use_response_type = support_type
                    elif support_type in client_accepts:
                        self.use_response_type = support_type
            if self.use_response_type is False:
                # client wants what we don't support
                self.supported = False
                self.use_response_type = 'text/plain'
                self.error_message = 'This resource not available in the requested mime-type: '
                self.error_message += client_accepts + '\n\n '
                self.error_message += 'The following representations are supported: \n '
                self.error_message += self.default_type + '; \n '
                self.error_message += '; \n '.join(self.supported_types)
