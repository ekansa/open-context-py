import json
from django.conf import settings
from opencontext_py.libs.rootpath import RootPath
from opencontext_py.libs.general import LastUpdatedOrderedDict


class RequestDict():

    def __init__(self):
        self.security_ok = True  # False if a security threat detected in the request
        self.is_bot = False
        self.do_bot_limit = False
        self.refresh_cache = False

    def make_request_dict_json(self, request, spatial_context):
        """ makes a JSON object of the request object
            to help deal with memory problems
        """
        request_dict = self.make_request_obj_dict(request, spatial_context)
        json_string = json.dumps(request_dict,
                                 ensure_ascii=False, indent=4)
        return json_string

    def make_request_obj_dict(self, request, spatial_context):
        """ makes the Django request object into a dictionary obj """
        bot_ok_params = [
            # these are params OK for a bot to request
            'proj',
            'page',
            'rows',
            'start',
            'as-bot'  # so we can experiment to get bot-views easily
        ]
        new_request = LastUpdatedOrderedDict()
        if spatial_context is not None:
            new_request['path'] = spatial_context
        else:
            new_request['path'] = False
        if request is not False:
            bot_herder = BotHerder()
            self.is_bot = bot_herder.check_bot(request)
            if 'as-bot' in request.GET:
                self.is_bot = True
            if self.is_bot:
                if spatial_context is not None:
                    # bots don't get to search by context
                    self.do_bot_limit = True
            for key, key_val in request.GET.items():  # "for key in request.GET" works too.
                if key == 'refresh-cache':
                    # request to refresh the cache for this page, but note!
                    # we're not including it in the new_request
                    self.refresh_cache = True
                elif key != 'callback' and self.is_bot is False:
                    # so JSON-P callbacks not in the request
                    self.security_check(request, key)  # check for SQL injections
                    new_request[key] = request.GET.getlist(key)
                    new_request = self.dinaa_period_kludge(key, new_request)
                elif key in bot_ok_params and self.is_bot:
                    # only allow bot crawling with page, rows, or start parameters
                    # this lets bots crawl the search, but not execute faceted searches
                    if key != 'as-bot':
                        new_request[key] = request.GET.getlist(key)
                elif key not in bot_ok_params and self.is_bot:
                    # bot has request parameters that we don't want to support
                    self.do_bot_limit = True
                else:
                    # do nothing
                    pass
                if self.security_ok is False:
                    break
        return new_request

    def dinaa_period_kludge(self, key, new_request):
        """ makes sure we dive a bit into the period hiearchy for
            requests to a DINAA period
        """
        if key == 'prop':
            new_prop_list = []
            for prop_list_item in new_request[key]:
                if 'dinaa-00001' in prop_list_item \
                   and 'dinaa-00001---dinaa-00002' not in prop_list_item:
                    prop_list_item = prop_list_item.replace('dinaa-00001', 'dinaa-00001---dinaa-00002')
                new_prop_list.append(prop_list_item)
            new_request[key] = new_prop_list
        return new_request

    def security_check(self, request, key):
        """ simple check for SQL injection attack,
            these are evil doers at work, no need
            even to pass this on to solr
        """
        evil_list = ['union select ',
                     'char(',
                     'delete from',
                     'truncate table',
                     'drop table',
                     '&#',
                     '/*']
        for param_val in request.GET.getlist(key):
            val = param_val.lower()
            for evil in evil_list:
                if evil in val:
                    self.security_ok = False
        return self.security_ok


class BotHerder():
    """ methods to detect bots and herd them so they don't overly
        tax the faceted search with too many filters complex
    """
    BOT_USERAGENTS = [
        'Googlebot',
        'Slurp',
        'Twiceler',
        'msnbot',
        'KaloogaBot',
        'YodaoBot',
        'Baiduspider',
        'googlebot',
        'Speedy Spider',
        'DotBot',
        'bingbot',
        'BLEXBot',
        'Exabot',
        'YandexBot',
        'Sogou',
        'Qwantify',
        'SemrushBot',
        'semrush',
        'ltx71',
        'MJ12bot',
        'spbot',
        'http://2re.site/',
        'https://7ooo.ru/',
    ]

    def __init__(self):
        self.is_bot = False
        self.bot_useragents = self.BOT_USERAGENTS
        self.no_name_agent = 'Secretagent'

    def check_bot(self, request):
        """ checks to see if the user agent is a bot """
        user_agent = request.META.get('HTTP_USER_AGENT', None)
        if not user_agent:
            user_agent = self.no_name_agent
        for bot_agent in self.bot_useragents:
            if bot_agent in user_agent:
                self.is_bot = True
                break
        return self.is_bot
