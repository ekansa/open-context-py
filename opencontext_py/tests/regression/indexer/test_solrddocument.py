import pytest
from opencontext_py.apps.indexer.solrdocumentnew import SolrDocumentNew as SolrDocument




@pytest.mark.django_db
def test_solr_document_subjects_bone():
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
def test_solr_document_subjects_coin():
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
def test_solr_document_predicates():
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
def test_solr_document_media_human_flag():
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
    