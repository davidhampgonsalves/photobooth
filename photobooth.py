#! /usr/bin/env python
import os, errno
import cv
import threading
import winsound
import shutil
from datetime import datetime
import Image
import ImageFont, ImageDraw, ImageOps

import strip_printer

# dependancies:
#   python 2.7
#   winsound(on windows), on linux change the playSound function to something else
#   openCV python bindings
#   PIL(python imaging library)
#   PyWin32 - for printing

PHOTOBOOTH_WINDOW = "photobooth"
PHOTO_COUNT = 4
PHOTO_FILE_EXTENSION = 'png'
PHOTO_FORMAT = 'PNG'

PHOTO_FOLDER = 'photos/'
ORIGINAL_FOLDER = 'photos/originals/'
STRIPE_FOLDER = 'photos/stripes/'
COLOR_FOLDER = 'photos/stripes/color/'
GREYSCALE_FOLDER = 'photos/stripes/greyscale/'
SOUND_FOLDER = 'sounds/'

HALF_WIDTH = 175
HALF_HEIGHT = 200

PHOTO_WIDTH = HALF_WIDTH * 2
PHOTO_HEIGHT = HALF_HEIGHT * 2

PAGE_WIDTH = 1400;
PAGE_HEIGHT = 1800;

FOOTER_HEIGHT = 130
BORDER_WIDTH = 10
BG_COLOR = (255,255,255)

def main():
    create_folder_struct()
    
    cv.NamedWindow(PHOTOBOOTH_WINDOW , 1)
    capture = cv.CaptureFromCAM(1)

    #when the program starts the booth needs to be empty
    is_booth_empty = True
    #capture a few frames to let the light levels adjust
    for i in range(100):
        cv.QueryFrame(capture)
    #now create a histogram of the empty booth to compare against in the future
    empty_booth_hist = get_hsv_hist(cv.QueryFrame(capture))

    while(True):
        img = cv.QueryFrame(capture)
        
        #check if button is pressed(enter)
        key = cv.WaitKey(10)

        if(key == 32):
            playAudio('start')
            take_picture(capture, 1)
            take_picture(capture, 2)
            take_picture(capture, 3)
            take_picture(capture, 4)
            playAudio('end')
            path = create_photo_strips()
            strip_printer.print_strip(path)
            archive_images()
        elif(key == 27):
            break
            
        #check for movement
        booth_empty_check = check_is_booth_empty(img, empty_booth_hist)
        if booth_empty_check != None and is_booth_empty != booth_empty_check:
            print 'hello' if is_booth_empty else 'goodbye'
            #playAudio('hello' if is_booth_empty else 'goodbye')
            is_booth_empty = not is_booth_empty
        
        cv.ShowImage(PHOTOBOOTH_WINDOW , img)


def create_folder_struct():
    create_folder(PHOTO_FOLDER)
    create_folder(ORIGINAL_FOLDER)
    create_folder(STRIPE_FOLDER)
    create_folder(COLOR_FOLDER)
    create_folder(GREYSCALE_FOLDER)

def create_folder(folderPath):
    try:
        os.makedirs(folderPath)
    except OSError, e:
        if e.errno != errno.EEXIST:
            raise

def take_picture(capture, i):
    playAudio('cheese-' + str(i))
    #capture a couple frames to get the current frame,
    #I think all my blocking calls mess up the capture process 
    #for open cv, requesting a couple frames seems to solve that,
    #it also creates a nice deplay between the audio and the capture
    for j in range(5):
        img = cv.QueryFrame( capture )
        cv.ShowImage(PHOTOBOOTH_WINDOW , img)
        cv.WaitKey(100)
    playAudio('click')
    cv.SaveImage(PHOTO_FOLDER + str(i) + '.png',img)
                
def get_hsv_hist(img):
    hsv = cv.CloneImage(img)
    cv.CvtColor(img, hsv, cv.CV_BGR2HSV)
    
    h_plane = cv.CreateImage ((cv.GetSize(img)[0],cv.GetSize(img)[1]), 8, 1)
    s_plane = cv.CreateImage ((cv.GetSize(img)[0],cv.GetSize(img)[1]), 8, 1)
    cv.Split(hsv, h_plane, s_plane, None, None)
    
    hist = cv.CreateHist([32,64], cv.CV_HIST_ARRAY, [[0,180], [0,255]], 1)
    cv.CalcHist([h_plane, s_plane], hist)
    return hist
    
def check_is_booth_empty(img, empty_booth_hist):
    hist = get_hsv_hist(img)    
    difference = cv.CompareHist(empty_booth_hist, hist, cv.CV_COMP_CORREL)
    
    print difference
    if difference > 0.90:
        return True
    elif difference < 0.80:
        return False
    else:
        #too hard to say so return None
        None



def create_photo_strips():
    '''using the original images we build a color and black and white photo strip and save it to photos/strips'''
    strip = Image.new('RGB', (PHOTO_HEIGHT + (BORDER_WIDTH * 2) + FOOTER_HEIGHT, (PHOTO_WIDTH * PHOTO_COUNT) + (BORDER_WIDTH * 2)), BG_COLOR)    

    for i in range(PHOTO_COUNT):
        photo = Image.open(PHOTO_FOLDER + str(i+1) + '.' + PHOTO_FILE_EXTENSION)
        
        w, h = map(lambda x: x/2, photo.size)
        
        photo = ImageOps.fit(photo, (PHOTO_WIDTH, PHOTO_HEIGHT), centering=(0.5, 0.5))
        photo = photo.rotate(270)
        photo = ImageOps.autocontrast(photo, cutoff=0)
        
        strip.paste(photo, (FOOTER_HEIGHT, (i * PHOTO_WIDTH) + (i * BORDER_WIDTH)))

    #append footer

    font = ImageFont.truetype('font_1.ttf', 40)

    footer_img = Image.new("RGB", ((PHOTO_COUNT * PHOTO_WIDTH) + (PHOTO_COUNT * BORDER_WIDTH), FOOTER_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(footer_img)
    draw.text((220, 40), "ashley & david's wedding, july 28, 2012", font=font, fill=(100,100,0))
    strip.paste(footer_img.rotate(270), (0,0))

    strip.save(COLOR_FOLDER + current_timestamp() + '.png', PHOTO_FORMAT)
    ImageOps.grayscale(strip).save(GREYSCALE_FOLDER + current_timestamp() + '.png', PHOTO_FORMAT)

    strip_to_print = Image.new('RGB', (PAGE_WIDTH, PAGE_HEIGHT), BG_COLOR)
    strip_to_print.paste(ImageOps.grayscale(strip), (-BORDER_WIDTH, -BORDER_WIDTH))

    strip_to_print.save('to_print.png', PHOTO_FORMAT)
    
    return 'to_print.png'
    
def current_timestamp():
    return datetime.now().strftime("%d.%m.%y-%H.%M.%S")

def archive_images():
    '''move the original images to the photos/originals and rename them with a timestamp.  Also delete the now printed version of the strip'''
    for i in range(1, 4):
        shutil.move(PHOTO_FOLDER + str(i) + '.png', ORIGINAL_FOLDER + current_timestamp() + ' ' + str(i) + '.png')
    os.remove('to_print.png')
    
    
def playAudio(audio_name):
    '''play the audio file assoicated with the given name, this blocks while the sound plays'''
    winsound.PlaySound(SOUND_FOLDER + audio_name + '.wav', winsound.SND_FILENAME)

if __name__=="__main__":
    main()
