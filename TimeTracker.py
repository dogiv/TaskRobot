#%%
import time
from datetime import datetime
from PyQt5.QtWidgets import * 
from PyQt5.QtCore import QTimer

import ctypes
from ctypes import wintypes, windll, create_unicode_buffer
import win32api

class TimeTracker1:

    class LastInputInfo(ctypes.Structure):
        _fields_ = [
            ('cbSize', wintypes.UINT),
            ('dwTime',wintypes.DWORD),
            ]

    def __init__(self):
        self.start_time = None
        self.end_time = None

        self.liinfo = TimeTracker1.LastInputInfo()
        self.liinfo.cbSize = ctypes.sizeof(self.liinfo)
        pLastInputInfo = ctypes.POINTER(TimeTracker1.LastInputInfo)
        self.GetLastInputInfo = windll.user32.GetLastInputInfo
        self.GetLastInputInfo.restype = wintypes.BOOL
        self.GetLastInputInfo.argtypes = [pLastInputInfo]

        kernel32 = windll.kernel32
        GetTickCount = kernel32.GetTickCount
        Sleep = kernel32.Sleep

        self.timer = QTimer()
        self.timer.timeout.connect(self.poll_foreground_window_title)
        self.timer.start(1000)

        self.current_window = None
        self.windowlog = []
        self.logposition = 0 # index of the first log entry that has not yet been viewed
        self.windowdict = {}
        self.last_change = time.time()

        self.errorlogfile = "tracker-error-log.txt"

        self.idle_time_threshold = 60 * 2 # 2 minutes threshold for idle
        self.last_active_time = time.time()
        self.is_idle = False

    def get_new_log_entries(self):
        entries = self.windowlog[self.logposition:]
        self.logposition = len(self.windowlog)
        return entries # formatting into a string is done in the LanguageModel function add_log_entries
    
    def get_aggregated_log_entries(self):
        aggregated_entries = []
        for window_name, time_spent in self.windowdict.items():
            minutes_spent = time_spent / 60
            aggregated_entries.append(f"{window_name}: {minutes_spent:.2f} minutes")
        self.windowdict.clear() # Reset the dictionary? I should save the entries somewhere first.
        return aggregated_entries

    def check_user_activity(self):
        # Get the time of the last input event (in milliseconds)
        idle_time = (win32api.GetTickCount() - win32api.GetLastInputInfo()) / 1000.0
        if idle_time > self.idle_time_threshold and not self.is_idle:
            self.is_idle = True
            self.last_active_time = time.time() - idle_time
            print("Idle now.")
            #self.log_idle_period()
            #self.current_window = "Idle period"
        elif idle_time < self.idle_time_threshold and self.is_idle: # idle period should end
            self.is_idle = False
            #self.poll_foreground_window_title()
            #self.log_idle_period() # no need to log this, the active window will show up in the log instead.

    def poll_foreground_window_title(self):
        self.check_user_activity()
        #print(self.is_idle, self.current_window)
        prevname = self.current_window
        # Check if focus window has changed, if so record the time spent on the last one
        try:
            winname = self.getForegroundWindowTitle()
        except:
            winname = "Unreadable window name"
        #try:
        if winname is None:
            #print("window None, idle ", self.is_idle)
            winname = "None"
        if self.is_idle:
            winname = "Idle Period"
        if winname != prevname:
            t = time.time()
            if prevname not in self.windowdict:
                print(prevname, t, self.last_change)
                self.windowdict[prevname] = 0
            self.windowdict[prevname] += t - self.last_change
            self.last_change = t
            self.windowlog.append({"time": datetime.now(), "window": winname})
            self.current_window = winname
        #except:
        #    with open(self.errorlogfile, 'a') as logfile:
        #        logfile.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " \t" + "Error 1 in: " + winname.encode("ascii", "ignore").decode() + "\n")

    def log_idle_period(self):
        current_time = time.time()
        idle_log_entry = {
        "time": datetime.now(),
        "window": "Idle Period Start"
        }
        self.windowlog.append(idle_log_entry)
        self.last_active_time = current_time

    def start(self):
        self.start_time = time.time()

    def stop(self):
        self.end_time = time.time()

    def get_elapsed_time(self):
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0
    
    def getForegroundWindowTitle(self):
        hWnd = windll.user32.GetForegroundWindow()
        length = windll.user32.GetWindowTextLengthW(hWnd)
        buf = create_unicode_buffer(length + 1)
        windll.user32.GetWindowTextW(hWnd, buf, length + 1)
        if buf.value:
            return buf.value
        else:
            return None