from flask import Flask, jsonify, render_template, request
from werkzeug import SharedDataMiddleware
import tempfile, os
import simplejson as json
import SimpleCV
import PIL
from PIL import ImageEnhance
import pprint
import sys
import numpy as np
from i2g import writeGif
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import boto
import hashlib
import time

app = Flask(__name__)

#IMAGE_URL_BASE = 'https://s3.amazonaws.com/yacosnaps/'
IMAGE_URL_BASE = 'https://snaps.yacomink.com/'
IMAGE_BUCKET = 'yacosnaps'
IMAGE_BUCKET_PREFIX = 't/'

CANVAS_WIDTH=364
CANVAS_HEIGHT=316
PAGE_WIDTH=150
PAGE_HEIGHT=194
PAGE_FILL_WIDTH=135
PAGE_FILL_HEIGHT=175

FRAME_PAGE_POSITIONS = [
    # trump_clipped_0.png
    [((217,238),(230,269),(104,271),(103,241)),((232,272),(250,312),(106,313),(104,273))],
    # trump_clipped_1.png,
    [((213,237),(229,267),(106,269),(103,240)),((232,268),(251,308),(112,310),(107,271))],
    # trump_clipped_2.png,
    [((182,186),(208,254),(92,269),(74,200)),((209,257),(244,295),(115,310),(94,272))],
    # trump_clipped_3.png,
    [((136,107),(201,157),(126,244),(64,190)),((207,160),(263,193),(182,293),(130,249))],
    # trump_clipped_4.png,
    [((133,105),(213,136),(172,241),(89,208)),((220,138),(298,164),(254,276),(178,243))],
    # trump_clipped_5.png,
    [((164,129),(241,134),(232,248),(154,249)),((248,136),(336,142),(328,256),(238,248))],
    # trump_clipped_6.png,
    [((175,143),(249,140),(253,254),(178,264)),((255,140),(336,136),(341,248),(260,254))],
    # trump_clipped_7.png,
    [((175,141),(238,137),(244,250),(180,262)),((244,137),(329,132),(336,243),(250,248))],
    # trump_clipped_8.png,
    [((167,141),(235,137),(239,250),(171,262)),((240,137),(326,133),(331,244),(246,249))],
    # trump_clipped_9.png,
    [((166,136),(234,134),(238,246),(170,257)),((240,133),(325,129),(330,241),(244,246))],
    # trump_clipped_10.png,
    [((164,136),(232,133),(236,246),(168,256)),((237,133),(323,131),(328,242),(242,245))],
    # trump_clipped_11.png,
    [((161,130),(230,128),(234,242),(165,252)),((235,128),(323,125),(327,238),(240,241))],
    # trump_clipped_12.png,
    [((138,125),(217,124),(220,239),(142,248)),((223,124),(314,120),(318,237),(226,239))],
    # trump_clipped_13.png,
    [((90,118),(182,124),(178,244),(82,243)),((189,125),(278,124),(273,250),(182,244))],
    # trump_clipped_14.png,
    [((80,126),(176,134),(166,256),(69,251)),((183,134),(276,141),(266,270),(172,258))],
    # trump_clipped_15.png,
    [((92,129),(189,136),(181,258),(85,255)),((196,137),(288,142),(281,270),(187,258))],
    # trump_clipped_16.png,
    [((103,133),(198,138),(191,261),(96,258)),((206,139),(300,144),(292,272),(198,261))],
    # trump_clipped_17.png,
    [((104,132),(200,138),(192,261),(96,258)),((208,139),(302,144),(293,273),(198,261))],
    # trump_clipped_18.png,
    [((95,129),(192,136),(181,258),(85,254)),((199,138),(291,144),(281,273),(188,259))],
    # trump_clipped_19.png,
    [((56,122),(149,134),(134,251),(42,240)),((155,134),(235,146),(218,272),(140,253))],
    # trump_clipped_20.png,
    [((33,118),(113,131),(96,247),(17,231)),((118,132),(181,144),(161,272),(101,249))],
    # trump_clipped_21.png,
    [((36,123),(120,137),(104,256),(22,238)),((126,138),(185,154),(167,283),(110,257))],
    # trump_clipped_22.png,
    [((31,123),(119,138),(103,262),(17,244)),((125,139),(189,155),(171,290),(109,263))],
    # trump_clipped_23.png,
    [((25,122),(116,137),(100,268),(8,249)),((123,138),(194,155),(173,298),(105,271))],
    # trump_clipped_24.png,
    [((18,123),(112,138),(96,272),(2,254)),((121,140),(191,157),(172,304),(102,274))],
    # trump_clipped_25.png,
    [((8,124),(106,141),(89,278),(0,260)),((115,141),(189,158),(168,309),(95,280))],
    # trump_clipped_26.png,
    [((70,116),(184,136),(154,257),(50,241)),((188,140),(214,184),(178,315),(156,260))],
    # trump_clipped_27.png,
    [((200,180),(283,162),(229,238),(147,262)),((0,0),(0,0),(0,0),(0,0))],
    # trump_clipped_28.png,
    [((0,0),(0,0),(0,0),(0,0)),((0,0),(0,0),(0,0),(0,0))],
    # trump_clipped_29.png,
    [((0,0),(0,0),(0,0),(0,0)),((0,0),(0,0),(0,0),(0,0))],
]

def getSizeForPageObject(twidth,theight):

    crop_width=0
    crop_height=0

    width = PAGE_FILL_WIDTH
    height = PAGE_FILL_HEIGHT

    thumb_ratio = float(twidth) / float(theight)
    page_ratio = float(width) / float(height)
 
    if (page_ratio > thumb_ratio):
        crop_height = height
        crop_width = int(round(height * thumb_ratio, 0))
    elif (page_ratio <= thumb_ratio):
        crop_width = width
        crop_height = int(round( (width * (1/thumb_ratio)), 0 ))

    return (crop_width, crop_height)


def getPageSizedImage(image):

    # Get dimensions image will occupy in page
    thumb_dimensions = getSizeForPageObject(image.width, image.height)
    width = thumb_dimensions[0]
    height = thumb_dimensions[1]

    # Center crop region in available page and define corners
    x_offset = int(round((PAGE_WIDTH - width) / 2, 0))
    y_offset = int(round((PAGE_HEIGHT - height) / 3, 0))
    
    c1 = (x_offset,y_offset)
    c2 = (width + x_offset,y_offset)
    c3 = (width + x_offset,height + y_offset)
    c4 = (x_offset,height + y_offset)

    image = image.resize(PAGE_WIDTH,PAGE_HEIGHT).invert().warp((c1,c2,c3,c4)).invert().resize(CANVAS_WIDTH, CANVAS_HEIGHT)

    return image

@app.route('/')
def show(name=None):

    gif_frames = [];

    left_path = request.args.get('left')
    right_path = request.args.get('right')
    frames = request.args.get('frames')
    if (frames):
        frames = int(frames)
    if (not frames or frames > len(FRAME_PAGE_POSITIONS)):
        frames = len(FRAME_PAGE_POSITIONS)
    hasher = hashlib.sha1()
    hasher.update(left_path)
    hasher.update(right_path)
    hasher.update(str(frames))

    loc = '/tmp/' + hasher.hexdigest() + '.gif'
    s3path = IMAGE_BUCKET_PREFIX + hasher.hexdigest() + '.gif' 

    # Specify credentials for s3 in env vars
    conn = S3Connection()
    b = conn.get_bucket(IMAGE_BUCKET)
    k = Key(b)
    k.key = s3path 
    if (b.get_key(k.key)):
        return render_template('index.html', img='https://snaps.yacomink.com/' + k.key)

    for i in range(0, frames):
        over_left = getPageSizedImage(SimpleCV.Image(left_path));
        over_right = getPageSizedImage(SimpleCV.Image(right_path));

        left_page_coords = FRAME_PAGE_POSITIONS[i][0]
        right_page_coords = FRAME_PAGE_POSITIONS[i][1]
        over = False
        if (left_page_coords[0] != (0,0)):
            over = over_left.warp(left_page_coords)
            if (right_page_coords[0] != (0,0)):
                over = over + over_right.warp(right_page_coords)

        foreground = PIL.Image.open(os.path.dirname(__file__) + '/trumps/trump_clipped_' + str(i) + '.png')

        if (over):
            out = over.getPIL()
            out = PIL.ImageEnhance.Brightness(out).enhance(0.91)
            out.paste(foreground, (0,0), foreground)
            gif_frames.append(out)
        else:
            gif_frames.append(foreground)


    writeGif(loc, gif_frames, duration=0.24)

    k.set_contents_from_filename(loc)
    k.set_acl('public-read')
    os.remove(loc)

    return render_template('index.html', img=IMAGE_URL_BASE + s3path + '?z=' + str(time.clock()))


if __name__ == '__main__':
    if app.config['DEBUG']:
        from werkzeug import SharedDataMiddleware
        import os
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
                '/': os.path.join(os.path.dirname(__file__), 'static')
        })
    app.run('0.0.0.0', debug=True)
