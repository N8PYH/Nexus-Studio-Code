import pyautogui as pg
import time
import os
import pygetwindow as gw
import psutil
from PIL import Image

def press(key_name):
    pg.press(key_name)

def hotkey(key_name1, key_name2):
    pg.hotkey(key_name1, key_name2)

def click(pos_x, pos_y):
    pg.click(pos_x, pos_y)

def screenshot(file_name):
    im1 = pg.screenshot()
    im2 = pg.screenshot(file_name)

def sleep(time_seconds):
    time.sleep(time_seconds)

def getpos():
    return pg.position()
