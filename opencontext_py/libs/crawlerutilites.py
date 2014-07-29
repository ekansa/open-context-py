import time
import re


class CrawlerUtilities():
    '''
    Utilities useful for the crawler app
    '''
    def is_valid_document(self, document):
        '''
        Validate that numeric and date fields contain only numeric and
        date data.
        '''
        is_valid = True
        for key in document:
            if key.endswith('numeric'):
                for value in document[key]:
                    if not(self.is_valid_float(value)):
                        is_valid = False
            if key.endswith('date'):
                for value in document[key]:
                    if not(self.is_valid_date(value)):
                        is_valid = False
        return is_valid

    def is_valid_float(self, value):
        return isinstance(value, float)

    def is_valid_date(self, value):
        pattern = re.compile(
            '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,3})?Z'
            )
        return bool(pattern.search(value))

    def get_crawl_rate_in_seconds(self, document_count, start_time):
        return str(round(document_count/(time.time() - start_time), 3))

    def get_elapsed_time_in_seconds(self, start_time):
        return str(round((time.time() - start_time), 3))
