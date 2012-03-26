#! /usr/bin/env python
import cv
import threading
import winsound
import shutil
from datetime import datetime
import Image
import ImageFont, ImageDraw, ImageOps

# dependancies:
#   python 2.7
#   winsound(on windows), on linux change the playSound function to something else
#   openCV python bindings
#   PIL(python imaging library)    

PHOTOBOOTH_WINDOW = "photobooth"
PHOTO_COUNT = 3
PHOTO_FILE_EXTENSION = 'png'
PHOTO_FORMAT = 'PNG'

HALF_WIDTH = 150
HALF_HEIGHT = 200

PHOTO_WIDTH = HALF_WIDTH * 2
PHOTO_HEIGHT = HALF_HEIGHT * 2 

FOOTER_HEIGHT = 130
BORDER_WIDTH = 10
BG_COLOR = (255,255,255)

def main():
    cv.NamedWindow(PHOTOBOOTH_WINDOW , 1)
    capture = cv.CaptureFromCAM(0)

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
        if(key == 13):
            playAudio('start')
            take_picture(capture, 1)
            take_picture(capture, 2)
            take_picture(capture, 3)
            playAudio('end')
            create_photo_strips()
            archive_images()
        elif(key == 27):
            break
            
        #check for movement
        booth_empty_check = check_is_booth_empty(img, empty_booth_hist)
        if booth_empty_check != None and is_booth_empty != booth_empty_check:
            print 'hello' if is_booth_empty else 'goodbye'
            playAudio('hello' if is_booth_empty else 'goodbye')
            is_booth_empty = not is_booth_empty
        
        cv.ShowImage(PHOTOBOOTH_WINDOW , img)

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
    cv.SaveImage('photos/' + str(i) + '.png',img)
                
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
    strip = Image.new('RGB', (PHOTO_WIDTH + (BORDER_WIDTH * 2), (PHOTO_HEIGHT * PHOTO_COUNT) + (BORDER_WIDTH * 2) + FOOTER_HEIGHT), BG_COLOR)    

    for i in range(PHOTO_COUNT):
        photo = Image.open('photos/' + str(i+1) + '.' + PHOTO_FILE_EXTENSION)
        
        w, h = map(lambda x: x/2, photo.size)
        
        photo = ImageOps.fit(photo, (PHOTO_WIDTH, PHOTO_HEIGHT), centering=(0.5, 0.5))
        photo = ImageOps.autocontrast(photo, cutoff=0)
        
        strip.paste(photo, (BORDER_WIDTH, (i * PHOTO_HEIGHT) + (i * BORDER_WIDTH)))

    #append footer
    draw = ImageDraw.Draw(strip)

    font = ImageFont.truetype('font_1.ttf', 30)
    font_2 = ImageFont.truetype('font_1.ttf', 20)
    footer_pos = (PHOTO_HEIGHT * PHOTO_COUNT) + (BORDER_WIDTH * 2)

    draw.text((BORDER_WIDTH* 4, footer_pos + 15), "ashley & david's", font=font, fill=(0,0,0))
    draw.text((BORDER_WIDTH * 9, footer_pos + 50), "wedding", font=font, fill=(0,0,0))
    draw.text((BORDER_WIDTH * 9, footer_pos + 80), "july 29, 2012", font=font_2, fill=(100,100,100))

    strip.save('photos/stripes/color/' + current_timestamp() + '.png', PHOTO_FORMAT)
    ImageOps.grayscale(strip).save('photos/stripes/greyscale/' + current_timestamp() + '.png', PHOTO_FORMAT)
    
def current_timestamp():
    return datetime.now().strftime("%d.%m.%y-%H.%M.%S")

def archive_images():
    '''move the original images to the photos/originals and rename them with a timestamp'''
    for i in range(1, 4):
        shutil.move('photos/' + str(i) + '.png', 'photos/originals/' + current_timestamp() + ' ' + str(i) + '.png')
    
def playAudio(audio_name):
    '''play the audio file assoicated with the given name, this blocks while the sound plays'''
    winsound.PlaySound('sounds/' + audio_name + '.wav', winsound.SND_FILENAME)

if __name__=="__main__":
    main()