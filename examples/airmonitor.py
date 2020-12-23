"""

A simple air pollution monitor.
I used ST7735 TFT display and  Adafruit CircuitPython RGB  library
as described [here](https://learn.adafruit.com/1-8-tft-display/python-wiring-and-setup)

It prints out time and data on the screen and eCO2 and other measurements.
Colors of text vary according to the measurement.

Note that by some reason R and B colors were switched on my display.
So go ahead and correct r and b according to your hardware in hand.

Also, my sensor pretty often shows impossible numbers for eCO2 (I would be dead already). 
To minimize these errors, I add re-initiation every hour. I hope it may be just a bad sensor.
If you find a way to make this system more robust without re-initiation, let me know.

Video is [here] https://youtu.be/4aXMTt8Ia9Q

-RTH 

"""



import time, logging
import subprocess
import digitalio
import board
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
from matplotlib.pyplot import get_cmap
import adafruit_rgb_display.st7735 as st7735  # pylint: disable=unused-import

from CCS811_RPi import CCS811_RPi
import SDL_Pi_HDC1000 

logging.basicConfig(format='%(asctime)s:%(lineno)-6d%(levelname)-8s:%(message)s', level=logging.INFO,filename="airpol.log")


HDC1080         = True

configuration = 0b100000
pause = 10
reinit = 3600
record = "rec.cvs"

# Configuration for CS and DC pins (these are PiTFT defaults):
cs_pin = digitalio.DigitalInOut(board.CE0)
dc_pin = digitalio.DigitalInOut(board.D25)
reset_pin = digitalio.DigitalInOut(board.D24)

# Config for display baudrate (default max is 24mhz):
BAUDRATE = 24000000

# Setup SPI bus using hardware SPI:
spi = board.SPI()

# pylint: disable=line-too-long
# Create the display:
disp = st7735.ST7735R(
    spi, 
    rotation=0,  # 2.2", 2.4", 2.8", 3.2" ILI9341
    height=160,
    width=128,
    cs=cs_pin,
    dc=dc_pin,
    rst=reset_pin,
    baudrate=BAUDRATE,
)
if disp.rotation % 180 == 90:
    height = disp.width 
    width = disp.height
else:
    width = disp.width 
    height = disp.height


TIME_FONTSIZE = 24
MESG_FONTSIZE = 16
HEAD_FONTSIZE = 10


image = Image.new("RGB", (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=(0, 0, 0))
disp.image(image)

# Load a TTF font.  Make sure the .ttf font file is in the
# same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
timefont = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", TIME_FONTSIZE)
mesgfont = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", MESG_FONTSIZE)
headfont = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", HEAD_FONTSIZE)

draw.rectangle((20, 20, width-20, height-20), outline=0, fill=(0, 0, 255))
disp.image(image)

def _print_on_screen_(text,x,y,font, r,g,b):
    draw.text((x, y), text, font=font, fill=(b,g,r))
    dx,dy = font.getsize(text)
    return x+dx+2,y+dy+2

def init_sensor():
    ccs811 = CCS811_RPi()
    hwid = ccs811.checkHWID()
    if(hwid == hex(129)):
            draw.rectangle((20, 20, width-20, height-20), outline=0, fill=(0, 255, 0))
            disp.image(image)
    else: 
        _print_on_screen_("HARDWARE\nERROR",0,0,timefont,255,0,0)
        disp.image(image)
        exit(1)

    if(HDC1080):
            hdc1000 = SDL_Pi_HDC1000.SDL_Pi_HDC1000()
            hdc1000.turnHeaterOff()
            hdc1000.setTemperatureResolution(SDL_Pi_HDC1000.HDC1000_CONFIG_TEMPERATURE_RESOLUTION_14BIT)
            hdc1000.setHumidityResolution(SDL_Pi_HDC1000.HDC1000_CONFIG_HUMIDITY_RESOLUTION_14BIT)
    else:
        hdc1000 = None
    #print 'MEAS_MODE:',ccs811.readMeasMode()
    ccs811.configureSensor(configuration)
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    _,y = _print_on_screen_(f'MEAS_MODE:',0,0,timefont,0,198,120)
    _,y = _print_on_screen_(f'      {ccs811.readMeasMode()}',0,y,timefont,0,198,120)
    _,y = _print_on_screen_(f'STATUS   :',0,y,timefont,120,198,0)
    _,y = _print_on_screen_(f'      {bin(ccs811.readStatus())}',0,y,timefont,120,198,0)
    time.sleep(2)
    # Use these lines if you need to pre-set and check sensor baseline value
    # if(INITIALBASELINE > 0):
            # ccs811.setBaseline(INITIALBASELINE)
            # print((ccs811.readBaseline()))
    return ccs811, hdc1000


 
cnt = 0
result = {
    "eCO2" : 0.,
    'TVOC' : 0.,
    'TEMP' : 0.,
    "HUMD" : 0.
}
ccs811, hdc1000 = None, None
    
while True:
    #Init sensor
    if cnt == 0 :
        del ccs811, hdc1000
        ccs811, hdc1000 = init_sensor()
        logging.info("Reset device")

    time.sleep(1)
    cnt  = (cnt+1)%reinit
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    x,y  = 0, 0
    TIME = time.strftime("%H{}%M".format(":" if cnt%2 == 0 else " ") )
    x0,y0  = _print_on_screen_(TIME,x,y+3,timefont,255,255,255)
    DATE = time.strftime("%d/%m\n%Y")
    _,_  = _print_on_screen_(DATE,x0+9,y+3,headfont,255,255,255)
    draw.line((x0+3, y   , x0+3 , y0+4),fill=(255,255,255),width=3)
    draw.line((0   , y0+4, width, y0+4),fill=(255,255,255),width=3)
    y = y0+8
    #----CO2
    CO2  = f"{result['eCO2']}"
    if result['eCO2'] == "ERROR":
        r,g,b = 1.,0.,0.
    else:
        r,g,b,_ = get_cmap('rainbow')(1. if result['eCO2'] > 1200 else result['eCO2']/1200)
    x0,y0  = _print_on_screen_("eCO2 :\nppm",x,y,headfont,int(255*r),int(255*g),int(255*b))
    _,y  = _print_on_screen_(CO2,x0+1,y,timefont,int(255*r),int(255*g),int(255*b))
    y   += 6
    #---TVOC
    TVOC  = f"{result['TVOC']}"
    if result['TVOC'] == "ERROR":
        r,g,b = 1.,0.,0.
    else:
        r,g,b,_ = get_cmap('rainbow')(1. if result['TVOC'] > 660 else result['TVOC']/660)
    x0,y0  = _print_on_screen_("TVOC :\nppb",x,y,headfont,int(255*r),int(255*g),int(255*b))
    _,y  = _print_on_screen_(TVOC,x0+1,y,timefont,int(255*r),int(255*g),int(255*b))
    y   += 6
    #---Temp
    TEMP  = "{:0.2f}".format(result['TEMP'])
    if result['TVOC'] == "ERROR":
        r,g,b = 1.,0.,0.
    else:
        r,g,b,_ = get_cmap('rainbow')(1. if result['TEMP'] > 50 else result['TEMP']/50)
    x0,y0  = _print_on_screen_("TEMP :\nC",x,y,headfont,int(255*r),int(255*g),int(255*b))
    _,y  = _print_on_screen_(TEMP,x0+1,y,timefont,int(255*r),int(255*g),int(255*b))
    y   += 6
    #---Humidity
    HUMID  = "{:0.2f}".format(result['HUMD'])
    if result['TVOC'] == "ERROR":
        r,g,b = 1.,0.,0.
    else:
        r,g,b,_ = get_cmap('rainbow')(1. if result['HUMD'] > 70 else result['HUMD']/70)
    x0,y0  = _print_on_screen_("HUMID:\n%",x,y,headfont,int(255*r),int(255*g),int(255*b))
    _,y  = _print_on_screen_(HUMID,x0+1,y,timefont,int(255*r),int(255*g),int(255*b))

    # Display image.
    disp.image(image)
        
    if cnt%pause != 0 : continue
    if(HDC1080):
            humidity = hdc1000.readHumidity()
            temperature = hdc1000.readTemperature()
            ccs811.setCompensation(temperature,humidity)
    else:
            humidity = 50.00
            temperature = 25.00
    try:
        statusbyte = ccs811.readStatus()
        logging.debug(f'STATUS: {bin(statusbyte)}')
    except:
        
        del ccs811
        ccs811 = CCS811_RPi()
        continue
    try:
       error = ccs811.checkError(statusbyte)
       if(error):
           logging.error(f'ERROR:{ccs811.checkError(statusbyte)}')
    except:
        del ccs811
        ccs811 = CCS811_RPi()
        continue
    try:
       if(not ccs811.checkDataReady(statusbyte)):
               logging.info('No new samples are ready')
               continue;
       result = ccs811.readAlg();
       if(not result):
           result = {
               "eCO2" : "ERROR",
               'TVOC' : "ERROR",
               'TEMP' : temperature,
               "HUMD" : humidity

           }
           continue;
       result["TEMP"] = temperature
       result["HUMD"] = humidity
       baseline = ccs811.readBaseline()
    except:
        del ccs811
        ccs811 = CCS811_RPi()
        continue
    #Record data
    if record:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(record,"a") as fd:
            fd.write(timestamp+f",{result['eCO2']},{result['TVOC']},{result['TEMP']},{result['HUMD']}"+"\n")
    
