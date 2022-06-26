#!/usr/bin/env python3

import argparse
import sys
from PIL import Image, ImageOps, ImageDraw


def main(args):
    iimg = Image.open(args.inf.name)
    (w, h) = iimg.size
    print(iimg.format, w, h, iimg.mode)

    gimg = ImageOps.grayscale(iimg)
    (w, h) = gimg.size
    print(gimg.format, w, h, gimg.mode)
    gimgd = list(gimg.getdata())
    print(type(gimgd))
    gimg.show()
    print(len(gimgd))
#    pixels = [pixels[i * width:(i + 1) * width] for i in xrange(height)]
    print(type(gimgd[0]))
    gimgd = [gimgd[offset:offset+w] for offset in range(0, w*h, w)]

    for y in range(0, h):
        print("\n{:03}: ".format(y), end = '')
        for x in range(0, w):
            print('#' if gimgd[y][x] > 64 else ' ', end = '') 
            #print("{} ".format(gimgd[y][x]), end = '')

    # Write stringged output file
    oimg = Image.new("L", gimg.size)
    draw = ImageDraw.Draw(oimg)
    draw.line((0, 0) + oimg.size, fill=128)
    draw.line((0, oimg.size[1], oimg.size[0], 0), fill=128)
    oimg.save(args.outf, "PNG")

if __name__=="__main__" :
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--in", dest="inf", required = True, type=argparse.FileType('r'))
    parser.add_argument("-o", "--out", dest="outf", required = True, type=str)
    main(parser.parse_args())
   