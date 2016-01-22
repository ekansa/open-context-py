import requests
import reversion  # version control object
from time import sleep
from django.db import models


# Mediafile has basic metadata about media resources (binary files) associated with a media resource item
@reversion.register  # records in this model under version control
class Mediafile(models.Model):
    FILE_TYPES = ['oc-gen:fullfile',
                  'oc-gen:preview',
                  'oc-gen:thumbnail',
                  'oc-gen:hero']
    MEDIA_MIMETYPE_NS = 'http://purl.org/NET/mediatypes/'
    PDF_DEFAULT_THUMBNAIL = 'http://opencontext.org/static/oc/images/icons/pdf-noun-89522.png'
    uuid = models.CharField(max_length=50, db_index=True)
    project_uuid = models.CharField(max_length=50, db_index=True)
    source_id = models.CharField(max_length=50, db_index=True)
    file_type = models.CharField(max_length=50, db_index=True)
    mime_type_uri = models.CharField(max_length=200)
    file_uri = models.CharField(max_length=400)
    filesize = models.DecimalField(max_digits=19, decimal_places=3)
    highlight = models.IntegerField(null=True)  # rank for showcasing, highlighting as interesting
    updated = models.DateTimeField(auto_now=True)

    def get_file_info(self):
        """ Gets information about the file from a remote server """
        if(self.filesize < 1 or len(self.mime_type_uri) < 2):
            mm = ManageMediafiles()
            ok = mm.get_head_info(self.file_uri)
            if ok:
                self.mime_type_uri = mm.mime_type_uri
                self.filesize = mm.filesize

    def save(self, *args, **kwargs):
        """
        saves a manifest item with a good slug
        """
        if self.filesize is None:
            self.filesize = 0
        if self.mime_type_uri is None:
            self.mime_type_uri = ''
        if self.highlight is None:
            self.highlight = 0
        self.get_file_info()
        super(Mediafile, self).save(*args, **kwargs)

    class Meta:
        db_table = 'oc_mediafiles'
        unique_together = (('uuid', 'file_type'),)


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

    def get_head_info(self, file_uri, redirect_ok=False):
        output = False
        r = requests.head(file_uri)
        if r.status_code == requests.codes.ok:
            if 'Content-Length' in r.headers:
                self.filesize = r.headers['Content-Length']
            if 'Content-Type' in r.headers:
                self.raw_mime_type = r.headers['Content-Type']
                self.mime_type_uri = self.raw_to_mimetype_uri(self.raw_mime_type)
                self.genfile_type = self.mime_to_general_file_type(self.genfile_type)
                output = True
        elif redirect_ok:
            if r.status_code >= 300 and r.status_code <= 310:
                output = True
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
