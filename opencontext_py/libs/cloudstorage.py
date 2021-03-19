from libcloud.storage.types import Provider
from libcloud.storage.providers import get_driver

from django.conf import settings



# NOTE: This is a convenience to use local settings
# to look up Apache Libcloud supported cloud service providers.
# See: https://libcloud.readthedocs.io/en/stable/storage/supported_providers.html
SUPPORTED_CLOUD_SERVICE_PROVIDERS = {
    'ALIYUN_OSS': Provider.ALIYUN_OSS,
    'AURORAOBJECTS': Provider.AURORAOBJECTS,
    'AZURE_BLOBS': Provider.AZURE_BLOBS,
    'BACKBLAZE_B2': Provider.BACKBLAZE_B2,
    'DIGITALOCEAN_SPACES': Provider.DIGITALOCEAN_SPACES,
    'GOOGLE_STORAGE': Provider.GOOGLE_STORAGE,
    'KTUCLOUD': Provider.KTUCLOUD,
    'LOCAL': Provider.LOCAL,
    'MINIO': Provider.MINIO,
    'NIMBUS': Provider.NIMBUS,
    'NINEFOLD': Provider.NINEFOLD,
    'OPENSTACK_SWIFT': Provider.OPENSTACK_SWIFT,
    'S3': Provider.S3,
    'S3_RGW': Provider.S3_RGW,
    'S3_RGW_OUTSCALE': Provider.S3_RGW_OUTSCALE,
}


def get_storage_provider():
    """Returns the Cloud Service provider"""
    if not settings.CLOUD_STORAGE_SERVICE:
        return None
    return SUPPORTED_CLOUD_SERVICE_PROVIDERS.get(
        settings.CLOUD_STORAGE_SERVICE
    )

def get_cloud_storage_driver():
    """Returns a cloud storage driver connected to a service provider"""
    provider = get_storage_provider()
    if not provider or not settings.CLOUD_KEY or not settings.CLOUD_SECRET:
        return None
    cls = get_driver(provider)
    driver = cls(key=settings.CLOUD_KEY, secret=settings.CLOUD_SECRET)
    return driver
