import os
import sys
import time
try:
    import colorama
except ImportError:
    raise ImportError("Please install the colorama package.\nYou can do pip install colorama on the command line.")
colorama.init()




# Modules
def cls():
    """ Clears the Screen """
    os.system("cls")

def printpos(text,posy):
    """ Goes to the line [posy] and writes the text there """
    sys.stdout.write("\033["+str(posy)+";1H")
    sys.stdout.write(text)
    sys.stdout.flush()

def title(text):
    """ Sets the title """
    #cls()
    sys.stdout.write("\033[1;1H")
    long = 80
    left = int(int(long - int(len(text))) / 2)
    right = int(int(long - int(len(text))) / 2)
    left = left * " "
    right = right * " "
    sys.stdout.write(cl(left+text+right,"grey","on_white"))
    if str(float(float(len(left+text+right)) / float(2.0)))[-1] == "0":
        None
    else:
        sys.stdout.write(cl(" ","grey","on_white"))
    sys.stdout.flush()


def entry(_title="TITLE",question="QUESTION",clear=True):
    """ Creates an input window. title=window title  question=prompt clear=[True|False] Clear Window before asking(recommended)"""
    if clear:
        cls()
    title(_title)
    lns = len(question.split("\n"))
    middle = 12
    long = 80
    posy = middle - lns
    if lns > 1:
        temp = question.split("\n")[0]
    else:
        temp = question
    posx = int(int(int(long)-int(len(temp))) / 2)
    sys.stdout.write(posy*"\n"+str(posx*" ")+question)
    sys.stdout.flush()
    sys.stdout.write(cl("\n"+str(long*" "),"grey","on_yellow"))
    sys.stdout.write(cl(" ","grey","on_yellow")+str(int(long-2)*" ")+cl(" ","grey","on_yellow"))
    sys.stdout.write(cl(str(long*" "),"grey","on_yellow"))
    sys.stdout.write("\033["+str(posy+lns+3)+";2H")
    sys.stdout.flush()
    ret = raw_input("-> ")
    cls()
    return ret
    
def waitenter(msg="Please Press Enter ->"):
    """ Entry function like press enter message """
    height = 25
    long = 80
    long = long - 1
    sys.stdout.write("\033["+str(height)+";1H")
    sys.stdout.write(cl(str(long*" "),"grey","on_red"))
    r()
    sys.stdout.write(cl(str(msg),"grey","on_red"))
    raw_input()

ATTRIBUTES = dict(
        list(zip([
            'bold',
            'dark',
            '',
            'underline',
            'blink',
            '',
            'reverse',
            'concealed'
            ],
            list(range(1, 9))
            ))
        )
del ATTRIBUTES['']


HIGHLIGHTS = dict(
        list(zip([
            'on_grey',
            'on_red',
            'on_green',
            'on_yellow',
            'on_blue',
            'on_magenta',
            'on_cyan',
            'on_white'
            ],
            list(range(40, 48))
            ))
        )


COLORS = dict(
        list(zip([
            'grey',
            'red',
            'green',
            'yellow',
            'blue',
            'magenta',
            'cyan',
            'white',
            ],
            list(range(30, 38))
            ))
        )


RESET = '\033[0m'


def colored(text, color=None, on_color=None, attrs=None):
    """Colorize text.

    Available text colors:
        red, green, yellow, blue, magenta, cyan, white.

    Available text highlights:
        on_red, on_green, on_yellow, on_blue, on_magenta, on_cyan, on_white.

    Available attributes:
        bold, dark, underline, blink, reverse, concealed.

    Example:
        colored('Hello, World!', 'red', 'on_grey', ['blue', 'blink'])
        colored('Hello, World!', 'green')
    """
    if os.getenv('ANSI_COLORS_DISABLED') is None:
        fmt_str = '\033[%dm%s'
        if color is not None:
            text = fmt_str % (COLORS[color], text)

        if on_color is not None:
            text = fmt_str % (HIGHLIGHTS[on_color], text)

        if attrs is not None:
            for attr in attrs:
                text = fmt_str % (ATTRIBUTES[attr], text)

        text += RESET
    return text

def r():
    sys.stdout.write("\r")
    sys.stdout.flush()

returnpos = r
raw_input = input

def cprint(text, color=None, on_color=None, attrs=None, **kwargs):
    """Print colorize text.

    It accepts arguments of print function.
    """

    print((colored(text, color, on_color, attrs)), **kwargs)


cprint("hallo","red","on_white")
cl = colored

if __name__ == "__main__":
    os.system('clear')
    title("Hello")
    cprint("That is an example window dialog.\nPython is cool\nWe like it\nIt is so cool.\nIt is awesome.","yellow")
    waitenter()
    os.system('clear')
    title("Now Welcome!")
    cprint("In 10 Seconds you are going to see a dialog...","green",end="\r")
    cntr = 2
    for i in range(2):
        r()
        cntr = cntr - 1
        time.sleep(1)
        print(colored("In "+str(cntr)+" Seconds you are going to see a dialog...","green",None,None),end="\r")
    you = entry("Your favourite?","What is your favourite number?")
    os.system('clear')
    title("Your favourite number is...")
    cprint(str(you),"magenta")

    waitenter("Please Press Enter to exit -> ")
