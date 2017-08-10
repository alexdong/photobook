import os
from PIL import Image
from datetime import datetime
import json
from jinja2 import Template

# The EXIF tag that holds orientation data.
EXIF_ORIENTATION_TAG = 274

# Obviously the only ones to process are 3, 6 and 8.
# All are documented here for thoroughness.
ORIENTATIONS = {
    1: ("Normal", 0),
    2: ("Mirrored left-to-right", 0),
    3: ("Rotated 180 degrees", 180),
    4: ("Mirrored top-to-bottom", 0),
    5: ("Mirrored along top-left diagonal", 0),
    6: ("Rotated 90 degrees", 270),
    7: ("Mirrored along top-right diagonal", 0),
    8: ("Rotated 270 degrees", 90)
}

def get_rotate_degree(exif):
    if EXIF_ORIENTATION_TAG not in exif:
        return 0

    orientation = exif[EXIF_ORIENTATION_TAG]
    if orientation in [3,6,8]:
        return 360 - ORIENTATIONS[orientation][1]
    else:
        return 0

def get_origin_time(exif):
    if 36867 not in exif:
        return None, None
    s = exif[36867]
    return s, datetime.strptime(s, "%Y:%m:%d %H:%M:%S")


def get_float(x):
    return float(x[0]) / float(x[1])


def convert_to_degrees(value):
    d = get_float(value[0])
    m = get_float(value[1])
    s = get_float(value[2])
    return d + (m / 60.0) + (s / 3600.0)


def get_lat_lon(exif):
    try:
        gps_latitude = exif[34853][2]
        gps_latitude_ref = exif[34853][1]
        gps_longitude = exif[34853][4]
        gps_longitude_ref = exif[34853][3]

        lat = convert_to_degrees(gps_latitude)
        if gps_latitude_ref != "N":
                lat *= -1
        lon = convert_to_degrees(gps_longitude)
        if gps_longitude_ref != "E":
            lon *= -1
        return lat, lon
    except KeyError:
        return None


def get_images():
    return [(f, Image.open(os.path.join('./img', f)))
             for f in os.listdir('./img')
             if f.lower().endswith('.jpg') and os.path.isfile(os.path.join('./img', f))]


if __name__ == '__main__':
    # load images from disk. Key is filename that's used in `db.images`.
    images = {}
    for (fname, im) in get_images():
        exif=im._getexif()
        created_at = get_origin_time(exif)[0]
        images[fname] = {
            'name': fname,
            'size': im.size,
            'rotate': get_rotate_degree(exif),
            'created_at': get_origin_time(exif)[0],
            'location': json.dumps(get_lat_lon(exif))
        }

    # load db for all pages. Each page contains `images` and `description`.
    pages = json.loads(open('pages.json').read())
    for page in pages:
        page['images'] = [images[fname] for fname in page['images']]
        if 'created_at' not in page:
            page['created_at'] = page['images'][0]['created_at']
        if 'location' not in page:
            page['location'] = page['images'][0]['location']

    # print(images)
    tmpl = Template(open('./template.j2').read())
    open('index.html', 'w').write(tmpl.render(pages=pages))
