from django.test import TestCase
from opencontext_py.apps.ocitems.ocitem.models import OCitem
#from opencontext_py.apps.ldata.linkannotations.recursion import LinkRecursion


class TestPredicateValues(TestCase):

    def setUp(self):
        self.oc_item = OCitem(
            ).get_item('FA6BFBFD-39EB-4474-A2D9-860B2D1B81A6')
        self.json_ld = self.oc_item.json_ld
        self.oc_label = self.json_ld['label']

    def test_get_oc_item_label(self):
        #oc_label = self.json_ld['label']
        self.assertEqual(self.oc_label, 'CAT # 20')
