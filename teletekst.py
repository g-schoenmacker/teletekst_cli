#!/usr/bin/env python3

import curses
import requests
import html

def next_token(html_in, idx):
  """"
  Returns the length and type of the next token in the buffer
  Possible types are: 'iso', 'newline', 'tag_open', 'tag_close', 'str'
  """

  l = len(html_in)
  
  # iso chars are their own token
  if ord(html_in[idx]) > 1000:
    return 1, 'iso'

  # newlines are their own token
  if html_in[idx] == '\n': 
    return 1, 'newline'

  # html tags are their own token
  if html_in[idx] == '<':
    end_pos = html_in.find('>', idx) + 1
    return end_pos - idx if end_pos > 0 else l - idx, 'tag_close' if html_in[idx+1] == '/' else 'tag_open'
  start = idx

  # text strings are their own token
  while idx < l:
    if ord(html_in[idx]) > 1000 or html_in[idx] == '<' or html_in[idx] == '\n':
      return idx - start, 'str'
    idx = idx + 1
    
  # oed
  return l - start, 'str'

def html_to_curses(window, html_in):
  """
  Transforms HTML to curses commands, dealing with colour
  """
  
  html_in = html.unescape(html_in) # process html escape codes
  l = len(html_in)
  idx = 0
  row, col = 1, 0
  color = curses.color_pair(2) # default font

  while idx < l:
    token_len, token_type = next_token(html_in, idx)
    token_end = idx + token_len
    
    # HTML tags deal with font (colour) changes
    if token_type == "tag_open":
      tag = html_in[idx:token_end]
      if tag.find("red") > 0:
        color = curses.color_pair(1)
      if tag.find("green") > 0:
        color = curses.color_pair(2)
      elif tag.find("yellow") > 0:
        color = curses.color_pair(4)
      elif tag.find("bg-blue") > 0:
        color = curses.color_pair(6)
      elif tag.find("bg-white") > 0:
        color = curses.color_pair(7)
      elif tag.find("blue") > 0:
        color = curses.color_pair(3)
      elif tag.find("cyan") > 0:
        color = curses.color_pair(5)
      else:
        pass # empty span and a tags

    # HTML span close tags reset the font to the default
    elif token_type == "tag_close":
      tag = html_in[idx:token_end]
      if tag.find("span") > 0:
        color = curses.color_pair(2)
    
    # Strings are text that needs to be displayed in the current font
    elif token_type == 'str':
      window.addstr(row, col, html_in[idx:token_end], color)
      col += token_len
    
    # Newlines move the curses buffer
    elif token_type == 'newline':
      row += 1
      col = 0
      
    # ISO characters are used for lines/decoration; we handle a subset
    elif token_type == 'iso':
      cn = ord(html_in[idx])
      if cn == 61475 or cn == 61472: # black
        window.addstr(row, col, ' ', curses.color_pair(2))
      else: # blue
        window.addstr(row, col, ' ', curses.color_pair(6))
      col += 1
    
    # Move buffer idx
    idx = token_end

def main_curses(stdscr):
  
  # Set up curses
  curses.curs_set(0)
  curses.start_color()
  curses.init_pair(1, curses.COLOR_RED, curses.COLOR_BLACK)
  curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
  curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_BLACK)
  curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
  curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)
  curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)
  curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_WHITE)

  stdscr.clear()
  stdscr.refresh()

  # Test and set up screen size
  height, width = stdscr.getmaxyx()
  if height < 27 or width < 41:
    return # window too small
  win = curses.newwin(27, 41, 0, 0)
  stdscr.refresh()
  
  # Fetch TT index page 101
  resp = requests.get(url='https://teletekst-data.nos.nl/json/101-1')
  page_buffer = "" # filled when user types numbers to change TT page

  while True:
    
    if resp.status_code == 200:
      data = resp.json()
    else:
      data['content'] = data['content'][:page_number_pos] + "..." + data['content'][page_number_pos + 3:]

    # Bit of juggling with data['content'] to update top right when user types page number
    page_number_pos = 116 # magic position of current page number
    if len(page_buffer) == 1:
      data['content'] = data['content'][:page_number_pos] + page_buffer + ".." + data['content'][page_number_pos + 3:]
    elif len(page_buffer) == 2:
      data['content'] = data['content'][:page_number_pos] + page_buffer + "." + data['content'][page_number_pos + 3:]

    # Update screen
    html_to_curses(win, data['content'])
    win.border()
    win.refresh()
    
    # Wait for user input: blocking
    c = stdscr.getch()

    # Quit
    if chr(c) == 'q':
      return
    
    # Previous page
    elif c == 260 and data['prevPage']: # arrow right
      resp = requests.get(url='https://teletekst-data.nos.nl/json/' + data['prevPage'] + '-1')
      page_buffer = ""
    
    # Next page
    elif c == 261 and data['nextPage']: # arrow left
      resp = requests.get(url='https://teletekst-data.nos.nl/json/' + data['nextPage'] + '-1')
      page_buffer = ""
    
    # Delete number from buffer
    elif c == 263: # backspace
      page_buffer = page_buffer[:-1]
    
    # Add number to buffer
    elif c >= ord('0') and c <= ord('9'): # any number
      page_buffer += chr(c)
      if len(page_buffer) == 3:
        # Go to page
        resp = requests.get(url='https://teletekst-data.nos.nl/json/' + page_buffer + '-1')
        page_buffer = ""
    
    # On window resize, make sure minimum is met
    elif c == curses.KEY_RESIZE:
      height, width = stdscr.getmaxyx()
      if height < 27 or width < 41:
        return # window too small

def main():
  curses.wrapper(main_curses)

if __name__ == "__main__":
  main()
