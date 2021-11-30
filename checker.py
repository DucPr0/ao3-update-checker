from random import betavariate
from sys import maxsize
from tkinter.constants import BOTH
from bs4 import BeautifulSoup
from urllib import request
import mysql.connector
from mysql.connector import errorcode
from mysql.connector import errors
from functools import partial
import tkinter as tk


fic_list_file = open("fics.txt", "r")
fic_list = fic_list_file.read().splitlines()
# ficExport = open("ficexport.txt", "w")
# cachedFic = open("ficcache.txt", "w")
# cachedFic = open("ficcache.txt", "r")

def proc_chapter_count(text: str) -> int:
    return int(text.split('/')[0])

def proc_word_count(text: str) -> int:
    return int(text.replace(",", ""))

def proc_comments_count(text: str) -> int:
    return int(text)

def pull_property(soup: BeautifulSoup, tag_type: str, classes: list, output_handler) -> int:
    for tag in soup.find_all(tag_type):
        tag: BeautifulSoup
        if tag.has_attr("class") and tag["class"] == classes:
            return output_handler(tag.get_text())

def get_fic_html(fic_url: str):
    fic_request = request.urlopen(fic_url)
    if fic_request.getcode() != 200:
        print("Request to " + fic_url + " failed")
        quit()
    return str(fic_request.read())

pull_chapter_count = partial(pull_property, tag_type = "dd", classes = ["chapters"], output_handler = proc_chapter_count)
pull_word_count = partial(pull_property, tag_type = "dd", classes = ["words"], output_handler = proc_word_count)
pull_comments_count = partial(pull_property, tag_type = "dd", classes = ["comments"], output_handler = proc_comments_count)

def get_stored_chapter_count(fic_url: str, chapter_counts_lines):
    for line in chapter_counts_lines:
        url, chapter_count = line.split()
        if url == fic_url:
            return int(chapter_count)
    return -1


def get_fic_name(fic_soup: BeautifulSoup):
    for h2 in fic_soup.find_all("h2"):
        h2: BeautifulSoup
        if h2.has_attr("class") and h2["class"] == ["title", "heading"]:
            return h2.get_text().replace("\\n", "\n").strip()
    # hack for content warning wall
    for div in fic_soup.find_all("div"):
        div: BeautifulSoup
        if div.has_attr("class") and div["class"] == ["header", "module"]:
            return div.h4.a.get_text()


try:
    cnx = mysql.connector.connect(user = "admin", password = "iamaverybigboy", database = "ao3checker")
except mysql.connector.Error as err:
    if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
        print("Something is wrong with your user name or password")
    elif err.errno == errorcode.ER_BAD_DB_ERROR:
        print("Database does not exist")
    else:
        print(err)


def create_table(tablename: str):
    try:
        cnx._execute_query("CREATE TABLE " + tablename + "(\
            ficurl varchar(100) NOT NULL,\
            chapters int NOT NULL,\
            wordcount int NOT NULL,\
            comments int NOT NULL);")
    except errors.ProgrammingError:
        pass


tablename = "stats"
create_table(tablename)


def format_string(str: str):
    return "\"" + str + "\""

def get_soup_from_url(fic_url: str) -> BeautifulSoup:
    fic_html = get_fic_html(fic_url)
    fic_soup = BeautifulSoup(fic_html, "html.parser")
    return fic_soup

def compare_stats(fic_url: str, fic_soup: BeautifulSoup):
    # obtain stored stats
    cursor = cnx.cursor()
    cursor.execute("SELECT * FROM " + tablename + " WHERE ficurl = " + format_string(fic_url) + ";")
    stored_chapters = 0
    stored_comments = 0
    stored_word_count = 0
    for (ficurl, chapters, wordcount, comments) in cursor:
        # expected 1. if no stats are stored everything defaults to 0
        stored_chapters = chapters
        stored_word_count = wordcount
        stored_comments = comments

    # pull new stats
    pulled_chapters = pull_chapter_count(fic_soup)
    pulled_comments = pull_comments_count(fic_soup)
    pulled_wordcount = pull_word_count(fic_soup)
    fic_name = get_fic_name(fic_soup)
    
    updated = False

    if stored_chapters != pulled_chapters:
        print(fic_name + " received an update of " + str(pulled_wordcount - stored_word_count) + " new words!")
        updated = True
    if stored_comments != pulled_comments:
        print(fic_name + " got " + str(pulled_comments - stored_comments) + " new comments!")
        updated = True

    if updated:
        # update data in database
        cnx._execute_query("DELETE FROM " + tablename + " WHERE ficurl = " + format_string(fic_url) + ";")
        cnx._execute_query("INSERT INTO " + tablename + " VALUES\
            (" + format_string(fic_url) + ", " + str(pulled_chapters) + ", " + str(pulled_wordcount) + ", "
            + str(pulled_comments) + ");")
        cnx.commit()

    return [updated, pulled_chapters - stored_chapters, pulled_wordcount - stored_word_count, pulled_comments - stored_comments]


def update_checker():
    any_updates = False
    for fic_url in fic_list:
        # print(fic_url)
        fic_soup = get_soup_from_url(fic_url)
        tmp = compare_stats(fic_url, fic_soup)
        if tmp[0]:
            any_updates = True

    if not any_updates:
        print("No updates detected.")


def window() -> tk.Tk:
    window = tk.Tk()
    window.title("AO3 update checker")
    return window

def frame(master) -> tk.Frame:
    frame = tk.Frame(master = master, bg = "#656565")
    frame.pack(fill = BOTH)
    return frame

def label(master, text) -> tk.Label:
    label = tk.Label(
        master = master,
        text = text,
        fg = "white",
        bg = "#656565",
        font = ("Courier", 30, "bold")
    )
    label.pack(fill = BOTH)
    return label

def button(master, text, command, side) -> tk.Button:
    button = tk.Button(
        master = master,
        text = text,
        font = ("Courier", 20, "bold"),
        bg = "#656565",
        fg = "white",
        cursor = "hand2",
        command = command
    )
    button.pack(side = side, fill = BOTH)
    return button

def label_grid(master, text, gridx, gridy, padx = 0, pady = 0) -> tk.Label:
    label = tk.Label(
        master = master,
        text = text,
        fg = "white",
        bg = "#656565",
        font = ("Courier", 30, "bold")
    )
    label.grid(row = gridx, column = gridy, padx = padx, pady = pady)
    return label

def mainstuff():
    window: tk.Tk
    window = window()
    title_frame = frame(window)
    title_text = label(title_frame, "Update Checker")

    fic_frame = frame(window)
    headers = ["Name", "New Chapters", "New Words", "New Comments"]
    for i in range(0, 4):
        label_grid(fic_frame, headers[i], 0, i, padx = 30, pady = 10)
    for i in range(0, 4):
        fic_url = fic_list[i]
        fic_soup = get_soup_from_url(fic_url)
        fic_url_label = label_grid(fic_frame, get_fic_name(fic_soup), i + 1, 0)

    window.mainloop()

update_checker()
