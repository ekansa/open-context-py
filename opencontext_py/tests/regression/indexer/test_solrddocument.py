import pytest
import logging
import random
from opencontext_py.apps.ocitems.manifest.models import Manifest
from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument

logger = logging.getLogger("tests-regression-logger")


@pytest.mark.django_db
def test_subjects_bone():
    """Tests solr_document creation on an example animal-bone subjects item."""
    uuid = '9095FCBB-35A8-452E-64A3-B8D52A0B2DB3'
    sd_obj = SolrDocument(uuid)
    if not sd_obj.oc_item:
        # Skip this test, this item is not in the DB
        return None
    sd_obj.make_solr_doc()
    assert sd_obj.fields['uuid'] == uuid
    assert sd_obj.fields['slug_type_uri_label'] == '1-dt05-1590___id___/subjects/9095FCBB-35A8-452E-64A3-B8D52A0B2DB3___DT05-1590'
    assert sd_obj.fields['item_type'] == 'subjects'
    assert '1-domuztepe-excavations' in sd_obj.fields['obj_all___project_id_fq']
    assert '1-domuztepe' in sd_obj.fields['obj_all___context_id_fq']
    assert 'oc-gen-cat-animal-bone' in sd_obj.fields['obj_all___oc_gen_subjects___pred_id_fq']
    assert 'obo-uberon-0001448' in sd_obj.fields['obj_all___oc_zoo_has_anat_id___pred_id_fq']


@pytest.mark.django_db
def test_subjects_coin():
    """Tests solr_document creation on an example coin subjects item."""
    uuid = 'BB35B081-FD20-4339-67F4-00DB99079338'
    sd_obj = SolrDocument(uuid)
    if not sd_obj.oc_item:
        # Skip this test, this item is not in the DB
        return None
    sd_obj.make_solr_doc()
    assert sd_obj.fields['uuid'] == uuid
    assert sd_obj.fields['item_type'] == 'subjects'
    assert '1-domuztepe-excavations' in sd_obj.fields['obj_all___project_id_fq']
    assert '1-domuztepe' in sd_obj.fields['obj_all___context_id_fq']
    assert 'oc-gen-cat-coin' in sd_obj.fields['obj_all___oc_gen_subjects___pred_id_fq']
    assert 2.0 in sd_obj.fields['1_thickness___pred_numeric']
    assert 'ocre-ric-7-anch-87' in sd_obj.fields['nmo_hastypeseriesitem___pred_id_fq']
    assert sd_obj.fields['image_media_count'] > 1


@pytest.mark.django_db
def test_predicates():
    """Tests solr_document creation on an example predicates item."""
    uuid = '04909421-C28E-46AF-98FA-10F888B64A4D'
    sd_obj = SolrDocument(uuid)
    if not sd_obj.oc_item:
        # Skip this test, this item is not in the DB
        return None
    sd_obj.make_solr_doc()
    assert sd_obj.fields['uuid'] == uuid
    assert sd_obj.fields['item_type'] == 'predicates'
    assert sd_obj.fields['slug_type_uri_label'] == '28-icp-ti___numeric___/predicates/04909421-C28E-46AF-98FA-10F888B64A4D___ICP - Ti'
    assert '28-asian-stoneware-jars' in sd_obj.fields['obj_all___project_id_fq']
    assert sd_obj.fields['image_media_count'] == 0


@pytest.mark.django_db
def test_media_human_flag():
    """Tests solr_document creation on an example media item with human remains flaging."""
    uuid = 'F675E155-81C9-4641-41AA-85A28DC44D90'
    sd_obj = SolrDocument(uuid)
    if not sd_obj.oc_item:
        # Skip this test, this item is not in the DB
        return None
    sd_obj.make_solr_doc()
    assert sd_obj.fields['uuid'] == uuid
    assert sd_obj.fields['item_type'] == 'media'
    assert '1-domuztepe-excavations' in sd_obj.fields['obj_all___project_id_fq']
    assert '1-domuztepe' in sd_obj.fields['obj_all___context_id_fq']
    assert sd_obj.fields.get('mimetype___pred_id') == 'http://purl.org/NET/mediatypes/image/jpeg'
    assert sd_obj.fields.get('filesize___pred_numeric') > 3000000.0
    assert 'oc-gen-cat-human-bone' in sd_obj.fields.get('rel__obj_all___oc_gen_subjects___pred_id_fq')
    assert sd_obj.fields['human_remains'] > 0


@pytest.mark.django_db
def test_documents():
    """Tests solr_document creation on an example documents item."""
    uuid = 'e4676e00-0b9f-40c7-9cb1-606965445056'
    sd_obj = SolrDocument(uuid)
    if not sd_obj.oc_item:
        # Skip this test, this item is not in the DB
        return None
    sd_obj.make_solr_doc()
    assert sd_obj.fields['uuid'] == uuid
    assert sd_obj.fields['item_type'] == 'documents'
    assert '24-murlo' in sd_obj.fields['obj_all___project_id_fq']
    assert '24-poggio-civitate' in sd_obj.fields['obj_all___context_id_fq']
    assert sd_obj.fields['slug_type_uri_label'] == '24-jn-ii-1972-05-011-134-tesoro-18-northern-extensio___id___/documents/e4676e00-0b9f-40c7-9cb1-606965445056___JN II (1972-05-01):1-134; Tesoro 18 - Northern Extension - Pottery'
    assert '24-trench-book-entry' in sd_obj.fields.get('24_document_type___pred_id_fq')
    assert sd_obj.fields['image_media_count'] > 10
    assert 'oc-gen-cat-exc-unit' in sd_obj.fields.get('rel__obj_all___oc_gen_subjects___pred_id_fq')


@pytest.mark.django_db
def test_projects():
    """Tests solr_document creation on an example projects item."""
    uuid = '3F6DCD13-A476-488E-ED10-47D25513FCB2'
    sd_obj = SolrDocument(uuid)
    if not sd_obj.oc_item:
        # Skip this test, this item is not in the DB
        return None
    sd_obj.make_solr_doc()
    assert sd_obj.fields['uuid'] == uuid
    assert sd_obj.fields['item_type'] == 'projects'
    assert '42-pyla-koutsopetria-archaeological-project-i-pedestrian' in sd_obj.fields['obj_all___project_id_fq']
    assert not 'obj_all___context_id_fq' in sd_obj.fields
    assert 'https://doi.org/10.6078/M7B56GNS' in sd_obj.fields.get('object_uri')
    assert '42-pkap-main-finds-descriptions' in sd_obj.fields.get('dc_terms_isreferencedby___pred_id_fq')
    assert 'bibo_status___pred_id' in sd_obj.fields
    assert 'dc_terms_subject___pred_id_fq' in sd_obj.fields
    assert 'https://doi.org/10.6078/M7B56GNS' in sd_obj.fields['persistent_uri']


@pytest.mark.django_db
def test_projects_with_sub_projects():
    """Tests solr_document creation on an example projects item that has sub-projects."""
    uuid = '416A274C-CF88-4471-3E31-93DB825E9E4A'
    sd_obj = SolrDocument(uuid)
    if not sd_obj.oc_item:
        # Skip this test, this item is not in the DB
        return None
    sd_obj.make_solr_doc()
    assert sd_obj.fields['uuid'] == uuid
    assert sd_obj.fields['item_type'] == 'projects'
    assert not 'obj_all___context_id_fq' in sd_obj.fields
    assert '52-coastal-state-site-data-for-sea-level-rise-modeling' in sd_obj.fields.get('obj_all___dc_terms_isreferencedby___pred_id_fq')
    assert 'bibo_status___pred_id' in sd_obj.fields
    assert 'dc_terms_subject___pred_id_fq' in sd_obj.fields
    assert 'https://doi.org/10.6078/M7N877Q0' in sd_obj.fields['persistent_uri']


@pytest.mark.django_db
def test_projects_is_sub_project():
    """Tests solr_document creation on an example projects item that has sub-projects."""
    uuid = '0cea2f4a-84cb-4083-8c66-5191628abe67'
    sd_obj = SolrDocument(uuid)
    if not sd_obj.oc_item:
        # Skip this test, this item is not in the DB
        return None
    sd_obj.make_solr_doc()
    assert sd_obj.fields['uuid'] == uuid
    assert sd_obj.fields['item_type'] == 'projects'
    assert '52-digital-index-of-north-american-archaeology-dinaa' in sd_obj.fields['root___project_id_fq']
    assert not 'obj_all___context_id_fq' in sd_obj.fields


def test_random_items(random_sample_items):
    """Tests solr_document creation a random sample of entities
       from each project, item_type, and class
    """
    # NOTE: This test, as currently configured requires about 45 minutes or so
    # to fully execute.
    num_tests = len(random_sample_items)
    i = 0
    for project_uuid, item_type, class_uri, uuid in random_sample_items:
        i += 1
        logger.info(
            'Test {}/{}: project_uuid="{}", item_type="{}", class_uri="{}", uuid="{}"'.format(
               i, num_tests, project_uuid, item_type, class_uri, uuid)
        )
        sd_obj = SolrDocument(uuid)
        sd_obj.make_solr_doc()
        logger.info('Number of solr fields made: {}'.format(len(sd_obj.fields)))
        assert sd_obj.fields['uuid'] == uuid
        assert sd_obj.fields['item_type'] == item_type
        if item_type != 'subjects':
            continue
        # Only do this if we're in a subject item.
        assert len(sd_obj.fields['obj_all___oc_gen_subjects___pred_id_fq']) > 0