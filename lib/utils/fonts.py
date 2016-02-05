import math


def measureFont(pnmFont, pointSize):
    """
    Measure the font's char size (w,h tuple), font char offset (w,h tuple),
    and Y draw offset
    :param pnmFont:
    :param pointSize:
    :return:
    """
    pnmFont.setPixelSize(pointSize)
    pnmFont.setScaleFactor(1.0)
    pnmFont.setNativeAntialias(True)

    # the freetype font can render well outside the expected
    # bounding box, so figure out the actual metrics
    adv = 1
    # max size
    w, h = 0, 0
    # maximum size above baseline
    t = pointSize
    # maximum descender
    b = 0
    for i in range(256):
        g = pnmFont.getGlyph(i)
        if g.getWidth() == 0:
            continue
        adv = max(adv, g.getWidth())
        w = max(w, g.getWidth())
        h = max(h, g.getHeight())
        t = min(t, g.getTop())
        b = max(b, -g.getTop() + g.getHeight())


    # 2 seems to be... um... padding?  I dunno.  Sigh.
    fontCharOffset = (w - adv, t + pointSize - 2)

    spAdv = int(pnmFont.getSpaceAdvance() * pointSize)
    #print "adv:",adv, "spAdv:",spAdv,"sizes:",w,"//",h,"top:",t,"bottom:",b

    # We calculated the maximum character advance.
    # Maybe the space advance is stupid, though.
    # We prefer to use the calculated glyph size,
    # but if the space advance is larger (though not insanely so), use that.
    if adv < spAdv:
        if adv * 2 > spAdv:
            adv = spAdv
        else:
            adv = int(math.sqrt(adv * spAdv / 2))

    fontCharSize = (adv, pointSize)

    return fontCharSize, fontCharOffset, pointSize - b


