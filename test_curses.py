import curses
import random
import time

window = curses.initscr()

try:
    (h, w) = window.getmaxyx()

    while True:
        x = int(random.random() * w)
        y = int(random.random() * h)
        window.move(y, x)
        window.addch("*")
        window.refresh()
        time.sleep(0.05)
except KeyboardInterrupt:
    pass
finally:
    curses.endwin()
