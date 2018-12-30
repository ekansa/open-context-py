import collections
import hashlib
import requests
import reversion  # version control object
from jsonfield import JSONField  # json field for complex objects
from time import sleep
from django.db import models


# Mediafile has basic metadata about media resources (binary files) associated with a media resource item
@reversion.register  # records in this model under version control
class Mediafile(models.Model):

    FILE_TYPES = [
        'oc-gen:fullfile',
        'oc-gen:preview',
        'oc-gen:thumbnail',
        'oc-gen:hero',
        'oc-gen:iiif',
        'oc-gen:archive',
        'oc-gen:ia-fullfille',
        'oc-gen:x3dom-model',
        'oc-gen:x3dom-texture'
        'oc-gen:nexus-3d',
    ]
    
    MEDIA_MIMETYPE_NS = 'http://purl.org/NET/mediatypes/'
    NEXUS_3D_MIME_TYPE = 'http://vcg.isti.cnr.it/nexus/'
    NEXUS_3D_COMPRESS_MIME_TYPE = 'http://vcg.isti.cnr.it/nexus/#nxz'
    PDF_DEFAULT_THUMBNAIL = 'https://opencontext.org/static/oc/images/icons/pdf-noun-89522.png'
    THREED_DEFAULT_THUMBNAIL = 'https://opencontext.org/static/oc/images/icons/3d-noun-37529.png'
    GIS_DEFAULT_THUMBNAIL = 'https://opencontext.org/static/oc/images/icons/gis-noun-14294.png'
    RASTER_DEFAULT_THUMBNAIL = 'https://opencontext.org/static/oc/images/icons/raster-small.png'
    
    hash_id = models.CharField(max_length=50, primary_key=True)
    uuid = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    file_type = models.CharField(max_length=50, db_index=True)
    mime_type_uri = models.CharField(max_length=200)
    file_uri = models.CharField(max_length=400)
    filesize = models.DecimalField(max_digits=19, decimal_places=3)
    highlight = models.IntegerField(default=0)  # rank for showcasing, highlighting as interesting
    # sup_json is for occationally occuring metadata fields.
    sup_json = JSONField(default={},
                         load_kwargs={'object_pairs_hook': collections.OrderedDict},
                         blank=True)
    updated = models.DateTimeField(auto_now=True)
    
    def make_hash_id(self):
        """
        Make a hash-id to insure unique combinations of uuids, file_types and highlight.
        By default, highlight is generally 0, which means that most of the time, saving a record
        to this model will only have 1 unqiue combination of uuid and file_type. However, for
        sake of some flexibility, we can have more than one uuid + file_type combination if the
        highlight value is changed. This would allow, for instance multiple "oc-gen:archive" records
        so we can point to multiple repositories that hold the binary media.
        """
        hash_obj = hashlib.sha1()
        concat_string = str(self.uuid) + " " + str(self.file_type) + " " + str(self.highlight)
        hash_obj.update(concat_string.encode('utf-8'))
        raw_hash = hash_obj.hexdigest()
        if len(self.uuid) > 8:
            # this helps keep uuids together on the table, reduces DB lookup time
            hash_id = self.uuid[0:8] + '-' + raw_hash
        else:
            hash_id = self.uuid + '-' + raw_hash
        return hash_id

    def get_file_info(self):
        """ Gets information about the file from a remote server """
        if(self.filesize < 1 or len(self.mime_type_uri) < 2):
            mm = ManageMediafiles()
            ok = mm.get_head_info(self.file_uri)
            if ok:
                self.mime_type_uri = mm.mime_type_uri
                self.filesize = int(float(mm.filesize))

    def save(self, *args, **kwargs):
        """
        saves a mediafile item with a hash_id 
        """
        if self.filesize is None:
            self.filesize = 0
        if self.mime_type_uri is None:
            self.mime_type_uri = ''
        if self.highlight is None:
            self.highlight = 0
        self.get_file_info()
        if (self.file_type == 'oc-gen:nexus-3d' and
            (self.mime_type_uri == '' or self.mime_type_uri is None)):
            # the nexus-3d file format does not have an official mime type, so
            # reference the webpage for Nexus-3D for now
            self.mime_type_uri = self.NEXUS_3D_MIME_TYPE
            if len(self.file_uri) > 4 and self.file_uri[-4:].lower() == '.nxz':
                # specify the compressed mime type.
                self.mime_type_uri = self.NEXUS_3D_COMPRESS_MIME_TYPE
        # make the hash_id last so the hash is generated
        # with the self.highlight value
        self.hash_id = self.make_hash_id()
        super(Mediafile, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_mediafiles'
        unique_together = (('uuid', 'file_type', 'highlight'),)


class ManageMediafiles():
    """
    Methods to look-up filesizes and mime-types
    """

    def __init__(self):
        self.file_uri = False
        self.genfile_type = False
        self.raw_mime_type = False
        self.mime_type_uri = False
        self.filesize = False
        self.delay = .33

    def get_head_info(self, file_uri, redirect_ok=False, retry=True):
        output = False
        try:
            r = requests.head(file_uri)
            if r.status_code == requests.codes.ok:
                if 'Content-Length' in r.headers:
                    self.filesize = int(r.headers['Content-Length'])
                if 'Content-Type' in r.headers:
                    self.raw_mime_type = r.headers['Content-Type']
                    self.mime_type_uri = self.raw_to_mimetype_uri(self.raw_mime_type)
                    self.genfile_type = self.mime_to_general_file_type(self.genfile_type)
                    output = True
            elif redirect_ok:
                if r.status_code >= 300 and r.status_code <= 310:
                    output = True
        except:
            if retry:
                # try again after a break
                sleep(.3)
                output = self.get_head_info(file_uri,
                                            redirect_ok,
                                            False)
        return output

    def update_missing_filesize_by_project(self, project_uuid):
        """ updates filesize zero media files by project """
        miss_media = Mediafile.objects\
                              .filter(filesize=0,
                                      project_uuid=project_uuid)
        total_len = len(miss_media)
        i = 0
        for mfile in miss_media:
            i += 1
            print(str(i) + ' of ' + str(total_len) + ', file: ' + mfile.file_uri)
            mfile.save()  # should automatically request filesize
            sleep(self.delay)  # short delay so as to not overwhelm servers

    def update_missing_mimetypes(self):
        """ Gets media files without mimetypes, updates them """
        miss_media = Mediafile.objects\
                              .filter(mime_type_uri='')
        total_len = len(miss_media)
        i = 0
        for mfile in miss_media:
            i += 1
            print(str(i) + ' of ' + str(total_len) + ', file: ' + mfile.file_uri)
            mfile.save()  # should automatically request mime-type
            sleep(self.delay)  # short delay so as to not overwhelm servers

    def raw_to_mimetype_uri(self, raw_mime_type):
        """
        Converts a raw mime-type to a mime_type_uri
        """
        return Mediafile.MEDIA_MIMETYPE_NS + raw_mime_type

    def mime_to_general_file_type(self, mime_type):
        """
        Converts either a raw, a prefixed, or a full mimetype uri to
        a general file type
        """
        output = False
        use_mime = str(mime_type)
        if(':' in use_mime):
            col_parts = use_mime.split(':')
            if(len(col_parts) > 1):
                use_mime = col_parts[1]
        if('/' in use_mime):
            mime_parts = use_mime.split('/')
            len_parts = len(parts)
            if(len_parts > 1):
                output = mime_parts[len_parts - 2]
        return output
