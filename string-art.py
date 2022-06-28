#!/usr/bin/env python3
import argparse
import math
import time
import re
from PIL import Image, ImageOps, ImageDraw, PngImagePlugin # 9.1.1

def euclideanDistance(a, b, factor = 1):
  return  math.sqrt(pow(a[0] - b[0], 2) + pow(a[1] - b[1], 2)) * factor

def createPins(args, w, h):
  result = []
  center = (round(w/2), round(h/2))
  radium = round((w if w < h else h)/2) - args.safetygap
  
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
    if diff < 0: regressions  += diff
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
    line = []
    dx = pins[t][0] - pins[f][0]
    dy = pins[t][1] - pins[f][1]
    s = abs(dx) if abs(dx) > abs(dy) else abs(dy)
    for i in range(1, s): # Skip the 1st point as it's the pin
      x = pins[f][0] + round(i * dx/s)
      y = pins[f][1] + round(i * dy/s)
      line.append((x,y))
    lines[query] = line
  return lines[query]

def main(args):
  lines = {}
  listing = [args.startpin]
  strpxlen = 0

  (w, h, gimgd) = handleInputImage(args, args.inf.name)
  
  (pins, oimgd) = createPins(args, w, h)

  currentpin = args.startpin
  for step in range(0, args.linenb):
    if args.verbose > 0: print("({}/{}) - pin {} ".format(step, args.linenb-1, currentpin))
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
    strpxlen += euclideanDistance(pins[currentpin], pins[qualification["pin"]])
    currentpin = qualification["pin"]
    listing.append(currentpin)

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
                 ("string-art:string-len", str("Not available" if args.boardsize == 0 else "{:.2f}m".format((strpxlen*args.boardsize/((w if w < h else h)))/1000))),
                 ("string-art:line-weight", str(args.lineweight))]: metadata.add_text(*text)

    oimg.save(args.outf, "PNG", pnginfo=metadata)

  if args.outlistingf != 'not-wanted':
    if args.outlistingf == 'auto': args.outlistingf = re.sub(r".png$", ".listing.txt", args.inf.name)
    with open(args.outlistingf, "w") as outlstf:
      n = 10
      outlstf.write(
"""# Input data
 Input file:      {ifp}
 Resolution:      {w}x{h}
 Number of pins:  {pinnb}
 Start pin:       {spin}
 Safety gap:      {sgap}
 Board size:      {bsize}
# Information
 Angle betw pins: {angle}º
 Max lines:       {linenb}
# Stats
 String length:   {slen:.2f}m
 Most used pin:   {mvpp} is used {mvpt} times
 Unused pins:     {up}
# Pin sequence (in chunks of {n} pins)
{pseq}
""".format(**{"ifp":args.inf.name, "w":w, "h":h, "pinnb":args.pinnb, "spin":args.startpin, "sgap":args.safetygap, 
              "bsize":"Not provided" if args.boardsize == 0 else args.boardsize, "linenb": args.linenb,
              "slen":"Not available" if args.boardsize == 0 else (strpxlen*args.boardsize/((w if w < h else h)))/1000, # px to m
              "mvpp": max(set(listing), key=listing.count), "mvpt": listing.count(max(set(listing), key=listing.count)),
              "up": sorted(list(set(range(0, args.pinnb))-set(listing))), "n":n, "angle": (360/args.pinnb),
              "pseq":"\n".join([" "+str(listing[i:i + n]) for i in range(0, len(listing), n)])}))


if __name__=="__main__" :
    startt = time.time()
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--in", dest="inf", required = True, type=argparse.FileType('r'), help="Input image, must be PNG")
    parser.add_argument("-b", "--board-size", dest="boardsize", type=int, default=0, help="Physical board size, in mm, this will match the length of the shortest side of the input image")
    parser.add_argument("-o", "--out", dest="outf", type=str, nargs='?', const='auto', default='not-wanted', help="Output image path. If argument is not provided, it'll be calculated automatically")
    parser.add_argument("-ol", "--out-listing", dest="outlistingf", type=str, nargs='?', const='auto', default='not-wanted', help="Output listing path. If argument is not provided, it'll be calculated automatically")
    parser.add_argument("-p", "--pins", dest="pinnb", default = 300, type=int, help="Number of pins in the circle of pins")
    parser.add_argument("-s", "--start-pin", dest="startpin", default = 0, type=int, help="The pin that will have the string first")
    parser.add_argument("-S", "--safety-gap", dest="safetygap", default = 10, type=int, help="The algorithm will be applied to the center of the image. This parameter specifies the amount of shrink in diameter applied to the circle of pins")
    parser.add_argument("-l", "--lines", dest="linenb", default = 3000, type=int, help="Maximum number of lines that will be traced onto the image")
    parser.add_argument("-w", "--line-weight", dest="lineweight", default = round(256/4), type=int, help="Amount of darkness that a single line will contribute to the final image (0-255)")
    #TODO: Add line width parameter
    parser.add_argument('-v', '--verbose', dest="verbose", action='count', default=0, help="Increase the verbosity of the software")
    args = parser.parse_args()
    main(args)
    if args.verbose > 0: print("--- {:.2f} seconds ---" .format(time.time() - startt))

   