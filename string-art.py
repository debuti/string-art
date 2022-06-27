#!/usr/bin/env python3
import argparse
import sys
import math
import time
import re
from PIL import Image, ImageOps, ImageDraw, PngImagePlugin


def printImage(args, imaged, w, h, close = True):
  '''255 is white, 0 is black'''
  def closewindow():
    import psutil
    for proc in psutil.process_iter(): 
      if proc.name() == "eom": proc.kill()
  img = Image.new("L", (w, h), "white")
  draw = ImageDraw.Draw(img)
  for y in range(0, h): 
    for x in range(0, w): draw.point((x, y), imaged[y][x])
  if close: closewindow()
  img.show()
  

def createPins(args, w, h):
    center = (round(w/2), round(h/2))
    radium = round((w if w < h else h)/2)-args.safetygap
    result = []
    
    oimg = Image.new("L", (w, h), "black")
    draw = ImageDraw.Draw(oimg)
    
    for i in range(0, args.pinnb):
      ang = i * 2 * math.pi / args.pinnb
      result.append((center[0] + round(radium * math.cos(ang)),
                     center[1] + round(radium * math.sin(ang))))

    draw.point(result, "white")

    if args.debug > 0:
      print(result)
      oimg.show()

    # TODO: Check that all pins are different / spaced with at least X
    
    oimgd = list(oimg.getdata())
    oimgd = [oimgd[offset:offset+w] for offset in range(0, w*h, w)]

    return (result, oimgd)

def testLine(args, gimgd, oimgd, w, h, line):
    #print("from {},{} to {},{}".format(line[0][0],line[0][1],line[1][0],line[1][1]))
    regressions = -1
    progressions = 1
    #printImage(args, gimgd, w, h, close=False)
    #printImage(args, oimgd, w, h, close=False)
    #print("size {}x{}".format(len(newd[0]),len(newd)))
    dx = line[1][0] - line[0][0]
    dy = line[1][1] - line[0][1]
    #print("dx {} dy {}".format(dx, dy))
    s = abs(dx) if abs(dx) > abs(dy) else abs(dy)
    #print("s {}".format(s))
    for i in range(1, s): # Skip the 1st point as it's the pin
      x = line[0][0] + round(i * dx/s)
      y = line[0][1] + round(i * dy/s)
      #print("x {} y {}".format(x, y))
      #print("gimgd {} oimgd {}".format(gimgd[y][x], oimgd[y][x]))
      diff = gimgd[y][x] - (oimgd[y][x] + args.lineweight)
      #print("diff {}".format(diff))
      #print("p {} r {} d {}".format(progressions, regressions, abs(progressions)/abs(regressions)))
      if diff < 0:
        regressions += diff
      else:
        progressions += diff
    #print("p {} r {} d {}".format(progressions, regressions, abs(progressions)/abs(regressions)))
    #time.sleep(100)
    return abs(progressions)/abs(regressions)

def drawLine(args, gimgd, oimgd, w, h, line):
    #print("from {},{} to {},{}".format(line[0][0],line[0][1],line[1][0],line[1][1]))
    newd = [row[:] for row in oimgd]
    #print("size {}x{}".format(len(newd[0]),len(newd)))
    dx = line[1][0] - line[0][0]
    dy = line[1][1] - line[0][1]
    #print("dx {} dy {}".format(dx, dy))
    s = abs(dx) if abs(dx) > abs(dy) else abs(dy)
    #print("s {}".format(s))
    for i in range(1, s): # Skip the 1st point as it's the pin
      x = line[0][0] + round(i * dx/s)
      y = line[0][1] + round(i * dy/s)
      #print("x {} y {}".format(x, y))
      # Conform the new image
      newd[y][x] += args.lineweight
    return newd

def main(args):
  def handleInputImage(args, fpath):
    iimg = Image.open(fpath).convert("RGBA")

    gimg = Image.new("L", iimg.size, "white")
    gimg.paste(iimg, (0, 0), iimg)
    gimg = ImageOps.invert(gimg)  
    if args.debug > 1: 
      gimg.show("Initial grayscale")
      time.sleep(2)
    (w, h) = gimg.size
    gimgd = list(gimg.getdata())
    gimgd = [gimgd[offset:offset+w] for offset in range(0, w*h, w)]
    
    return (w, h, gimgd) 

  # Extract useful data from input image
  (w, h, gimgd) = handleInputImage(args, args.inf.name)
  
  # Initialize the output canvas with the pins in place
  (pins, oimgd) = createPins(args, w, h)

  #printImage(args, oimgd, w, h)

  # TODO: Delegate processing on a rust dll library with FFI interface
  currentpin = args.startpin
  for step in range(0, args.linenb):
    if args.verbose > 0: print("Iteration {}, currentpin {} ".format(step, currentpin))
    qualification = {"init": False, "ratio": None, "line": None, "pin": None}
    for pin in range(2, args.pinnb-1): # Discard me and neighbours
      dstpin = (currentpin + pin) % args.pinnb
      line = (pins[currentpin], pins[dstpin])
      ratio = testLine(args, gimgd, oimgd, w, h, line)
      if not qualification["init"] or \
          (ratio > qualification["ratio"]):
        if args.verbose > 1: print("New best score at pin {}".format(dstpin))
        qualification["init"] = True
        qualification["ratio"] = ratio
        qualification["line"] = line
        qualification["pin"] = dstpin
  
    oimgd = drawLine(args, gimgd, oimgd, w, h, qualification["line"])
    currentpin = qualification["pin"]
    if False and step%10==9:
      printImage(args, oimgd, w, h)
      time.sleep(2)

  if args.outf != 'not-wanted':
    if args.outf == 'auto': args.outf = re.sub(r".png$", ".stringed.png", args.inf.name)

    # Write stringged output file
    oimg = Image.new("L", (w, h))
    draw = ImageDraw.Draw(oimg)
    for y in range(0, h):
      for x in range(0, w):
        draw.point((x, y), oimgd[y][x])
    oimg = ImageOps.invert(oimg)  

    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("string-art:pins", str(args.pinnb))
    metadata.add_text("string-art:start-pin", str(args.startpin))
    metadata.add_text("string-art:safety-gap", str(args.safetygap))
    metadata.add_text("string-art:lines", str(args.linenb))
    metadata.add_text("string-art:line-weight", str(args.lineweight))

    oimg.save(args.outf, "PNG", pnginfo=metadata)

if __name__=="__main__" :
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--in", dest="inf", required = True, type=argparse.FileType('r'))
    parser.add_argument("-o", "--out", dest="outf", type=str, nargs='?', const='auto', default='not-wanted')
    parser.add_argument("-p", "--pins", dest="pinnb", default = 300, type=int)
    parser.add_argument("-s", "--start-pin", dest="startpin", default = 0, type=int)
    parser.add_argument("-S", "--safety-gap", dest="safetygap", default = 10, type=int)
    parser.add_argument("-l", "--lines", dest="linenb", default = 5000, type=int)
    parser.add_argument("-w", "--line-weight", dest="lineweight", default = round(256/4), type=int)
    #TODO: line width
    parser.add_argument("-d", "--debug", dest="debug", action='count', default=0)
    parser.add_argument('-v', '--verbose', dest="verbose", action='count', default=0)
    main(parser.parse_args())
   