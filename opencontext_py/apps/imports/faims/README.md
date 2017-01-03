# Basic FAIMS (https://www.fedarch.org/) Importer

These classes read FAIMS generated XML data to import:
(1) Linking Relations (predicates)
(2) Descriptive Attributes (predicates)
(3) Controlled Vocabulary concepts (types)
(4) Entities (now subjects, but later media, documents, persons, etc.)
(5) Linking and Descrptive assertions about entities

This works as a basic importer to bring FAIMS data into Open Context, so
these data can see further edits and organization. The importer retains a record
of FAIMS-identifiers ("uuid" element + attribute strings) in the sup_json field of
the Open Context manifest. This enables precise provenance and association of 
FAIMS records and corresponding records in Open Context.

## TO DO:
(1) Import media files (esp. images) and associations with other FAIMS records
(2) Suggest spatial containment. Test imports to make spatial containment relationships
typically failed because of recurive / circular containment relationships. We need to
test relationships to make sure we don't run into this trouble.
(3) Import certainty metrics, notes about assertions, and documentation about controlled
vocabularies and predicates. This is an important but straightforward improvement.

    # STEP 1: DELETE PRIOR DATA
    source_id = 'faims-survey'
    project_uuid = '59ae0bd4-2dda-4428-b163-8ef0d579e2b9'
    from opencontext_py.apps.imports.sources.unimport import UnImport
    unimp = UnImport(source_id, project_uuid)
    unimp.delete_ok = True
    unimp.delete_all()

    # STEP 2: SET UP CONFIG FILES
    source_id = 'faims-survey'
    project_uuid = '59ae0bd4-2dda-4428-b163-8ef0d579e2b9'
    from opencontext_py.apps.imports.faims.main import FaimsImport
    faims_imp = FaimsImport()
    faims_imp.project_uuid = project_uuid
    faims_imp.source_id = source_id
    faims_imp.root_subject_label = 'Mordor'
    faims_imp.gen_configs('faims-survey')

    # STEP 3: EDIT CONFIG FILES


    # STEP 4: SAVE RECONCILE PREDICATES, TYPES
    source_id = 'faims-survey'
    project_uuid = '59ae0bd4-2dda-4428-b163-8ef0d579e2b9'
    from opencontext_py.apps.imports.faims.main import FaimsImport
    faims_imp = FaimsImport()
    faims_imp.project_uuid = project_uuid
    faims_imp.source_id = source_id
    faims_imp.save_reconcile_predicates_types('faims-survey')


    # STEP 5: SAVE ENTITIES then DESCRIBE THEM
    source_id = 'faims-survey'
    project_uuid = '59ae0bd4-2dda-4428-b163-8ef0d579e2b9'
    from opencontext_py.apps.imports.faims.main import FaimsImport
    faims_imp = FaimsImport()
    faims_imp.root_subject_label = 'Mordor'
    faims_imp.project_uuid = project_uuid
    faims_imp.source_id = source_id     
    faims_imp.save_describe_entities('faims-survey')
