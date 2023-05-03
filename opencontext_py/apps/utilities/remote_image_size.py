from urllib import request as ulreq
from PIL import ImageFile

def get_image_dimensions(uri):
    """Get the filesize and the image size"""
    try:
        file = ulreq.urlopen(uri)
    except:
        file = None
    if not file:
        return {}
    size = file.headers.get("content-length")
    if size:
        size = int(size)
    p = ImageFile.Parser()
    size_dict = {
        'filesize': size,
        'width': None,
        'height': None,
    }
    while True:
        data = file.read(1024)
        if not data:
            break
        p.feed(data)
        if p.image:
            size_dict['width'] = p.image.size[0]
            size_dict['height'] = p.image.size[1]
            break
    file.close()
    return size_dict