#!/usr/bin/env python3
import argparse
import sys
import math
import time
import re
from PIL import Image, ImageOps, ImageDraw, PngImagePlugin # 9.1.1

def euclideanDistance(a, b):
  return  math.sqrt(pow(a[0] - b[0], 2) + pow(a[1] - b[1], 2))

def createPins(args, w, h):
  center = (round(w/2), round(h/2))
  radium = round((w if w < h else h)/2) - args.safetygap
  result = []
  
  oimg = Image.new("L", (w, h), "black")
  draw = ImageDraw.Draw(oimg)
  
  for i in range(0, args.pinnb):
    ang = i * 2 * math.pi / args.pinnb
    result.append((center[0] + round(radium * math.cos(ang)),
                    center[1] + round(radium * math.sin(ang))))

  draw.point(result, "white")

  if args.boardsize > 0:
    phyDistanceBetweenPins = args.boardsize * euclideanDistance(result[0], result[1]) / ((radium)*2 + args.safetygap)
    if phyDistanceBetweenPins < 5:
      print("The physical separation between pins is {:.3f}mm but at least 5mm are recommended".format(phyDistanceBetweenPins))
      input("Press <Enter> if you wish to continue anyway or Ctrl+C to kill the software")
  
  oimgd = list(oimg.getdata())
  oimgd = [oimgd[offset:offset+w] for offset in range(0, w*h, w)]

  return (result, oimgd)

def testLine(args, gimgd, oimgd, linepts):
  regressions = -1
  progressions = 1
  for (x, y) in linepts:
    diff = gimgd[y][x] - (oimgd[y][x] + args.lineweight)
    if diff < 0: regressions += diff
    else:        progressions += diff
  return abs(progressions)/abs(regressions)

def drawLine(args, gimgd, oimgd, linepts):
  newd = [row[:] for row in oimgd]
  for (x, y) in linepts: newd[y][x] += args.lineweight
  return newd

def handleInputImage(args, fpath):
  iimg = Image.open(fpath).convert("RGBA")

  gimg = Image.new("L", iimg.size, "white")
  gimg.paste(iimg, (0, 0), iimg)
  gimg = ImageOps.invert(gimg)
  (w, h) = gimg.size
  gimgd = list(gimg.getdata())
  gimgd = [gimgd[offset:offset+w] for offset in range(0, w*h, w)]
  
  return (w, h, gimgd) 

def getLazyLinepts(args, pins, lines, line):
  (f, t) = line
  query = (f, t) if f > t else (t, f)
  if not query in lines:
    listing = []
    dx = pins[t][0] - pins[f][0]
    dy = pins[t][1] - pins[f][1]
    s = abs(dx) if abs(dx) > abs(dy) else abs(dy)
    for i in range(1, s): # Skip the 1st point as it's the pin
      x = pins[f][0] + round(i * dx/s)
      y = pins[f][1] + round(i * dy/s)
      listing.append((x,y))
    lines[query] = listing
  return lines[query]

def main(args):
  lines = {}

  # Extract useful data from input image
  (w, h, gimgd) = handleInputImage(args, args.inf.name)
  
  # Initialize the output canvas with the pins in place
  (pins, oimgd) = createPins(args, w, h)

  currentpin = args.startpin
  for step in range(0, args.linenb):
    if args.verbose > 0: print("Iteration {}, currentpin {} ".format(step, currentpin))
    qualification = {"ratio": None, "linepts": None, "pin": None}
    for pin in range(2, args.pinnb-1): # Discard me and neighbours
      dstpin = (currentpin + pin) % args.pinnb
      linepts = getLazyLinepts(args, pins, lines, (currentpin, dstpin))
      ratio = testLine(args, gimgd, oimgd, linepts)
      if not qualification["ratio"] or (ratio > qualification["ratio"]):
        if args.verbose > 1: print("New best score at pin {}".format(dstpin))
        qualification["ratio"] = ratio
        qualification["linepts"] = linepts
        qualification["pin"] = dstpin
  
    oimgd = drawLine(args, gimgd, oimgd, qualification["linepts"])
    currentpin = qualification["pin"]

  if args.outf != 'not-wanted':
    if args.outf == 'auto': args.outf = re.sub(r".png$", ".stringed.png", args.inf.name)

    oimg = Image.new("L", (w, h))
    draw = ImageDraw.Draw(oimg)
    for y in range(0, h):
      for x in range(0, w):
        draw.point((x, y), oimgd[y][x])
    oimg = ImageOps.invert(oimg)  

    metadata = PngImagePlugin.PngInfo()
    for text in [("string-art:pins", str(args.pinnb)),
                 ("string-art:start-pin", str(args.startpin)),
                 ("string-art:safety-gap", str(args.safetygap)),
                 ("string-art:lines", str(args.linenb)),
                 ("string-art:line-weight", str(args.lineweight))]: metadata.add_text(*text)

    oimg.save(args.outf, "PNG", pnginfo=metadata)

if __name__=="__main__" :
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--in", dest="inf", required = True, type=argparse.FileType('r'))
    parser.add_argument("-b", "--board-size", dest="boardsize", type=int, default=0, help="Physical board size, in mm, this will match the length of the shortest side of the input image")
    parser.add_argument("-o", "--out", dest="outf", type=str, nargs='?', const='auto', default='not-wanted')
    parser.add_argument("-p", "--pins", dest="pinnb", default = 300, type=int)
    parser.add_argument("-s", "--start-pin", dest="startpin", default = 0, type=int)
    parser.add_argument("-S", "--safety-gap", dest="safetygap", default = 10, type=int)
    parser.add_argument("-l", "--lines", dest="linenb", default = 3000, type=int)
    parser.add_argument("-w", "--line-weight", dest="lineweight", default = round(256/4), type=int)
    #TODO: line width
    parser.add_argument('-v', '--verbose', dest="verbose", action='count', default=0)
    #TODO: instructions output
    #TODO: stats: wire meters, histogram per pin, length of the canvas
    main(parser.parse_args())
   