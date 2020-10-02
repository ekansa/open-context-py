"""
NOTE: This is model is here in case we want to go back to a situation
where we store string text values in another DB table outside of assertions
"""

# OCstring stores string content, with each string unique to a project
# @reversion.register  # records in this model under version control
# class AllString(models.Model):
class AllString():
    uuid = models.UUIDField(primary_key=True, editable=True)
    project = models.ForeignKey(
        AllManifest,
        db_column='project_uuid', 
        related_name='+', 
        on_delete=models.CASCADE
    )
    source_id = models.TextField(db_index=True)
    # Note for multilingual text, choose the main language.
    language =  models.ForeignKey(
        AllManifest,
        db_column='language_uuid', 
        related_name='+', 
        on_delete=models.PROTECT, 
        default=configs.DEFAULT_LANG_UUID
    )
    updated = models.DateTimeField(auto_now=True)
    content = models.TextField()
    meta_json = JSONField(default=dict)

    def make_hash_id(
        self, 
        project_id,
        content='', 
        language_id=configs.DEFAULT_LANG_UUID,
        extra=[],
    ):
        """
        Creates a hash-id to insure unique content for a project and language
        """
        hash_obj = hashlib.sha1()
        all_hash_items = [str(project_id), str(language_id)]
        if len(extra):
            # Don't make a hash_id based on the
            # content. Use the items listed in extra
            # to help define the uniqueness and the ID for
            # the string. This lets us make very targetted
            # updates associated with just 1 assertion.
            all_hash_items += [str(e) for e in extra]
        
        # Sort all the elements of the list going
        # get hashed. This keeps keep the logic used to generate
        # a hash (and later uuid) inside the Strings model so it
        # will be more consistent.
        
        # Remove duplicate elements from the hash.
        all_hash_items = list(set(all_hash_items))
        # Sort them for deterministic consistency.
        all_hash_items.sort()

        # Now add the content for hashing. All this makes it very
        # possible to make a deterministic id, but one that's
        # unlikely to ever be repeated within a project. 
        all_hash_items.append(content.strip())

        concat_string = " ".join(all_hash_items)
        hash_obj.update(concat_string.encode('utf-8'))
        return hash_obj.hexdigest()
    
    def primary_key_create(
        self, 
        project_id, 
        content='',
        language_id=configs.DEFAULT_LANG_UUID,
        extra=[],
    ):
        """Deterministically make a primary key using a prefix from the project"""

        # Make the first part from the subject's uuid.
        project_id = str(project_id)
        uuid_prefix = project_id.split('-')[0]

        # Make a hash for this Assertion based on all those parts
        # that need to be unique.
        hash_id = self.make_hash_id(
            project_id=project_id,
            content=content,
            language_id=language_id,
            extra=extra,
        )
        # Now convert that hash into a uuid. Note, we're only using
        # the first 32 characters. This should still be enough to have
        # really, really high certainty we won't have hash-collisions on
        # data that should not be considered unique. If we run into a problem
        # we can always override this.
        uuid_from_hash_id = str(
            GenUUID.UUID(hex=hash_id[:32])
        )
        new_parts = uuid_from_hash_id.split('-')
        uuid = '-'.join(
            ([uuid_prefix] + new_parts[1:])
        )
        return uuid
    
    def primary_key_create_for_self(self):
        """Makes a primary key using a prefix from the subject"""
        if self.uuid:
            # One is already defined, so skip this step.
            return self.uuid
        return self. primary_key_create(
            project_id=self.project.uuid,
            content=self.content,
            language_id=self.language.uuid,
        )

    def save(self, *args, **kwargs):
        """
        creates the hash-id on saving to insure a unique string for a project
        """
        # Make sure the project is really a project.
        validate_related_project(project_obj=self.project)
        # Make sure the language has the right
        # manifest object item_type
        validate_related_manifest_item_type(
            man_obj=self.language,
            allowed_types=['languages'],
            obj_role='language'
        )
        self.content = self.content.strip()    
        self.uuid = self.primary_key_create_for_self()
        super(AllString, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_all_strings'
