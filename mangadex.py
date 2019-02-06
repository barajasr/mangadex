#! /usr/bin/env python3
#
# Author: Richard Barajas
# Email : barajasr89@gmail.com
# Date  : 2018.05.29
#

import argparse
import bs4
import os.path
import subprocess
import urllib3

from urllib.parse import urljoin
from collections import namedtuple

root = 'https://www.mangadex.org/'
Option = namedtuple('Option', ['value', 'title'])

parser = argparse.ArgumentParser()
parser.add_argument('-a', '--all',
                    action='store_true',
                    help='Archive all chapters relating to manga of given url.')
parser.add_argument('-c', '--clean',
                    action='store_true',
                    help='Set to clean up images no longer needed after archiving.')
parser.add_argument('-r', '--rar',
                    default='',
                    type=str,
                    help='Archive manga chapter with target filename.')
parser.add_argument('url',
                    type=str,
                    help='Url of the first page of chapter requesting.')

def allChapters(url):
    http = urllib3.PoolManager()
    resp = http.request('GET', url)
    soup = bs4.BeautifulSoup(resp.data.decode(), 'lxml')

    # Find all listed chapters in series
    selectList = soup.find('select', id='jump_chapter').find_all('option')
    chapters = [Option(option['value'], option.text.replace(' ','_') + '.cbr') for option in selectList]
    for chapter in chapters[::-1]:
        print('*'*25)
        print(chapter.title)
        url = urljoin(root, 'chapter/' + chapter.value)
        singleChapter(url, chapter.title, True)

def archiveChapter(filenames, archiveName, clean=False):
    if not all([os.path.isfile(page) for page in filenames]):
        print('Aborting archive')
        for page in filenames:
            print('Missing:', page)
        return

    command = 'rar a {} {}'.format(archiveName, ' '.join(filenames))
    subprocess.call(command.split())

    if clean:
        command = 'rm {}'.format(' '.join(filenames))
        subprocess.call(command.split())

def archiveExists(filename):
    exists = False
    if os.path.isfile(filename):
        print("Archive '" + filename + "' already exists.")
        exists = True
    return exists

def downloadImages(firstPage, numberToDownload):
    pos = firstPage.rfind('/')
    baseUrl = firstPage[:pos+1]
    filename = firstPage[pos+1:]
    prefix = filename.rsplit('1', 1)[0]
    imageTypes = ['png', 'jpg', 'jpeg']
    filenames = []

    # We already the full url of the first page but merged here to
    # avoid two seperate blocks of downloading.
    command = 'wget -q --show-progress '
    print('Pages to download:', numberToDownload)
    for page in range(1, numberToDownload + 1):
        downloaded = False
        for imageType in imageTypes:
            filename = '{}{}.{}'.format(prefix, page, imageType)
            if not os.path.isfile(filename):
                url = baseUrl + filename
                try:
                    subprocess.check_call((command + url).split())
                except:
                    continue
            else:
                print(filename, '\tAlready exists')
            # Reaches here if already exists or just downloaded
            downloaded = True
            filenames.append(filename)
            break
        if not downloaded:
            # Fail loudly
            raise ValueError('Image not found, possibly of another filetype.')

    return filenames

def getFirstPageAndCount(url):
    http = urllib3.PoolManager()
    resp = http.request('GET', url)
    soup = bs4.BeautifulSoup(resp.data.decode(), 'lxml')

    # Find current page one image
    img = soup.find('img', id='current_page')
    firstPage = img['src']

    # Assumes that all images are stored in same directory
    # Otherwise, requires parse each page for image src
    # Find dropdown menu for number of pages to request
    pages = len(soup.find('div', {'class': 'col-md-2'}).find_all('option'))

    return firstPage, pages

def singleChapter(url, archiveName='', clean=False):
    if archiveName and archiveExists(archiveName):
        return

    firstPage, pages = getFirstPageAndCount(url)
    filenames = downloadImages(firstPage, pages)
    
    if archiveName:
        archiveChapter(filenames, archiveName, clean)

def main():
    args = parser.parse_args()

    if not args.all:
        singleChapter(args.url, args.rar, args.clean)
    else:
        allChapters(args.url)

if __name__ == '__main__':
    main()

