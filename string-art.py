#!/usr/bin/env python3
import argparse
import sys
import math
import time
from PIL import Image, ImageOps, ImageDraw

def terminalPrintImage(args, imaged, w, h):
    for y in range(0, h):
        print("\n{:03}: ".format(y), end = '')
        for x in range(0, w):
            print('#' if imaged[y][x] > 64 else ' ', end = '') 

def printImage(args, imaged, w, h):
    '''255 is white, 0 is black'''
    closewindow()
    img = Image.new("L", (w, h), "white")
    draw = ImageDraw.Draw(img)
    for y in range(0, h):
      for x in range(0, w):
        draw.point((x, y), imaged[y][x])
    img.show()
  
def closewindow():
  import psutil
  for proc in psutil.process_iter():
      if proc.name() == "eom":
          proc.kill()

def createPins(args, w, h):
    center = (round(w/2), round(h/2))
    radium = round((w if w < h else h)/2)-args.safetygap
    result = []
    
    oimg = Image.new("L", (w, h), "white")
    draw = ImageDraw.Draw(oimg)
    
    for i in range(0, args.pinnb):
      ang = i * 2 * math.pi / args.pinnb
      result.append((center[0] + round(radium * math.cos(ang)),
                     center[1] + round(radium * math.sin(ang))))

    draw.point(result, "black")

    if args.debug > 0:
      print(result)
      oimg.show()

    # TODO: Check that all pins are different / spaced with at least X
    
    oimgd = list(oimg.getdata())
    oimgd = [oimgd[offset:offset+w] for offset in range(0, w*h, w)]

    return (result, oimgd)

def drawLine(args, w, h, line):
    #print("from {},{} to {},{}".format(line[0][0],line[0][1],line[1][0],line[1][1]))
    newd = [[0]*w for i in range(h)]
    #print("size {}x{}".format(len(newd[0]),len(newd)))
    dx = line[1][0] - line[0][0]
    dy = line[1][1] - line[0][1]
    #print("dx {} dy {}".format(dx, dy))
    s = abs(dx) if abs(dx) > abs(dy) else abs(dy)
    #print("s {}".format(s))
    for i in range(0, s):
      x = line[0][0] + round(i * dx/s)
      y = line[0][1] + round(i * dy/s)
      #print("x {} y {}".format(x, y))
      newd[y][x] += args.lineweight
    return newd

def diffImages(args, gimgd, newd): 
  diff = 0
  for y in range(0, len(gimgd)):
    for x in range(0, len(gimgd[y])):
      diff = gimgd[y][x] - newd[y][x]
  return diff

def addImagesInPlace(args, imgd, newd):
  for y in range(0, len(imgd)):
    for x in range(0, len(imgd[y])):
      imgd[y][x] -= newd[y][x]

def main(args):
    iimg = Image.open(args.inf.name)
    
    gimg = Image.new("L", iimg.size, "white") 
    gimg.paste(iimg, (0, 0), iimg)
    gimg = ImageOps.invert(gimg)  
    if args.debug > 1: 
      gimg.show("Initial grayscale")
      time.sleep(2)
    (w, h) = gimg.size
    print(gimg.size)
    gimgd = list(gimg.getdata())
    gimgd = [gimgd[offset:offset+w] for offset in range(0, w*h, w)]

    #terminalPrintImage(args, gimgd, w, h)
    
    # Initialize the output canvas with the pins in place
    (pins, oimgd) = createPins(args, w, h)

    printImage(args, oimgd, w, h)

    currentpin = args.startpin
    for step in range(0, args.linenb):
      if args.verbose > 2: print("Iteration {}, currentpin {} ".format(step, currentpin))
      qualification = {"score": w*h*255, "mod": None, "pin": None}
      for pin in range(2, args.pinnb-1): # Discard me and neighbours
        dstpin = (currentpin + pin) % args.pinnb
        line = (pins[currentpin], pins[dstpin])
        newd = drawLine(args, w, h, line)
        if True:
          printImage(args, newd, w, h)
          time.sleep(0.5)
        diff = diffImages(args, gimgd, newd)
        if diff < qualification["score"]:
          print("New best score at pin {}".format(pin))
          qualification = {"score": diff, "mod": newd, "pin": pin}
        
      addImagesInPlace(args, oimgd, qualification["mod"])
      currentpin = qualification["pin"]
      printImage(args, oimgd, w, h)
      time.sleep(2)

        

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
    parser.add_argument("-p", "--pins", dest="pinnb", default = 300, type=int)
    parser.add_argument("-s", "--start-pin", dest="startpin", default = 0, type=int)
    parser.add_argument("-S", "--safety-gap", dest="safetygap", default = 1, type=int)
    parser.add_argument("-l", "--lines", dest="linenb", default = 100, type=int)
    parser.add_argument("-w", "--line-weight", dest="lineweight", default = round(256/4), type=int)
    parser.add_argument("-d", "--debug", dest="debug", action='count', default=0)
    parser.add_argument('-v', '--verbose', dest="verbose", action='count', default=0)
    main(parser.parse_args())
   