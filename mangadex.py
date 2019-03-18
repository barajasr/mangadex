#! /usr/bin/env python3
#
# Author: Richard Barajas
# Email : barajasr89@gmail.com
# Date  : 2019.03.17
#

import argparse
import json
import os
import subprocess
import urllib3

from collections import namedtuple
from pick import pick
from selenium import webdriver
from urllib.parse import urljoin

parser = argparse.ArgumentParser()
parser.add_argument('-a', '--all', action='store_true',
                    help='''Archive all chapters relating to manga of given url.
Use title link as such: https://mangadex.org/title/12263''')
parser.add_argument('-c', '--clean', action='store_true',
                    help='Set to clean up images no longer needed after archiving.')
parser.add_argument('-d', '--directory',  default='./', type=str,
                    help='Directory to store images/archives. Default is working directory.'),
parser.add_argument('-r', '--rar', default='', type=str,
                    help='Archive manga chapter with target filename.')
parser.add_argument('url', type=str,
                    help='''Url of chapter requesting using link as such:\nhttps://mangadex.org/chapter/37770''')

class ChaptersJson:
    def __init__(self, jsonSource):
        if 'status' in jsonSource and jsonSource['status'] == 'OK':
            self.source = jsonSource
            self.chapters = jsonSource['chapter']
            self.mangaInfo = jsonSource['manga']

    def __str__(self):
        return jsonSource

    def chaptersList(self):
        chapters = []
        for key, value in self.chapters.items():
            if value['lang_code'] == 'gb':
                chapters.append(ChapterInfo(key,
                                            value['volume'],
                                            value['chapter'],
                                            value['title'],
                                            value['lang_code'],
                                            value['group_name']))
        return sorted(chapters, key=lambda chapterInfo: float(chapterInfo.chapterNumber))

ChapterInfo = namedtuple('ChapterInfo', 'chapterId volume chapterNumber title lang_code group_name')
ChapterPages = namedtuple('ChapterPages', 'volume chapter title server hashNumber pages')
MangaInfo = namedtuple('MangaInfo', 'artist author coverUrl description')

# Remove logging
browser = webdriver.PhantomJS(service_log_path=os.path.devnull)
browser.implicitly_wait(10)

def allChapters(url, directory='./'):
    if not url[-1].isdigit():
        # maybe passed in with trailing '/' or '/manga-title'
        url, _ = url.rsplit('/', 1)
    chapters = filterChapters(getChapters(url))
    total = len(chapters)
    count = 1
    print('{} chapters to download.'.format(total))
    for chapter in chapters:
        print('------'*15)
        print('chapter {} of {}'.format(count, total))
        singleChapter(chapter.chapterId, archive=True, clean=True, directory=directory)
        count += 1

def archiveChapter(filenames, archiveName, clean=True, directory='./'):
    if filenames == []:
        return
    if directory != './':
        makeDirectory(directory)
    archiveName = archiveName.replace(' ', '_')
    if archiveExists(archiveName):
        return

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

def downloadImages(chapterPages, directory='./'):
    if not chapterPages:
        return

    if directory != './':
        makeDirectory(directory)
    filenames = []
    print('Pages to download:', len(chapterPages.pages))

    for page in chapterPages.pages:
        filename = os.path.join(directory, page)
        url = '{}{}/{}'.format(chapterPages.server, chapterPages.hashNumber, page)
        if not os.path.isfile(filename):
            browser.set_window_size(4000,4000)
            browser.get(url)
            image = browser.find_element_by_tag_name('img')
            imageSize = image.size
            browser.set_window_size(imageSize['width'], imageSize['height'])
            if '.png' not in filename:
                filename = filename.rsplit('.', 1)[0] + '.png'
            print(filename, end='... ', flush=True)
            try:
                with open(filename, 'wb') as openFile:
                    openFile.write(image.screenshot_as_png)
            except IOError:
                print('failed to download.')
            print('saved.')
        else:
            print(filename, '\tAlready exists')
        filenames.append(filename)
    return filenames

def filterChapters(chapters):
    index = 0
    while index < len(chapters):
        current = chapters[index]
        testIndex = index + 1
        duplicates = []
        while testIndex < len(chapters) and chapters[testIndex].chapterNumber == current.chapterNumber:
            duplicates.append(chapters[testIndex])
            testIndex += 1

        if duplicates != []:
            duplicates.insert(0, current)
            _, optionIndex = pick(duplicates, 'Select chapter to download from among the scan groups:' )
            del duplicates[optionIndex]
            for duplicate in duplicates:
                chapters.remove(duplicate)

        index += 1

    return chapters

def getChapterPages(chapterId):
    url = 'http://mangadex.org/api/chapter/{}/'.format(chapterId)
    browser.get(url)
    jsonText = browser.find_element_by_tag_name('pre').text
    jsonText = json.loads(jsonText, encoding='utf-8')

    if 'status' in jsonText and jsonText['status'] == 'OK':
        mediaServer = jsonText['server']
        return ChapterPages(jsonText['volume'],
                            jsonText['chapter'],
                            jsonText['title'],
                            # Correct for /data/ case if needed
                            mediaServer if '/' != mediaServer[0] else urljoin('https://mangadex.org', mediaServer),
                            jsonText['hash'],
                            jsonText['page_array'])
    return None

def getChapters(url):
    chapters = []
    url = url.replace('title', 'api/manga')
    browser.get(url)
    jsonText = browser.find_element_by_tag_name('pre').text
    jsonText = json.loads(jsonText, encoding='utf-8')
    return ChaptersJson(jsonText).chaptersList()

def main():
    args = parser.parse_args()
    if not args.all:
        chapterId = args.url.split('chapter/')[1]
        singleChapter(chapterId, archiveName=args.rar, clean=args.clean, directory=args.directory)
    else:
        allChapters(args.url, args.directory)

def makeDirectory(path):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except:
            raise ValueError('Creation of path: {} failed'.format(path))

def singleChapter(chapterId, archiveName='', archive=True, clean=True, directory='./'):
    chapter = getChapterPages(chapterId)
    if archiveName == '':
        volumePrefix = '' if chapter.volume ==  '' else  'v' + chapter.volume
        chapterPrefix = '' if chapter.chapter ==  '' else  'c' + chapter.chapter
        titlePrefix = '' if chapter.title ==  '' else  ('-' + chapter.title).replace(' ', '_')
        archiveName = '{}{}{}.cbr'.format(volumePrefix, chapterPrefix, titlePrefix)
        archiveName = os.path.join(directory, archiveName)
    if archiveName and archiveExists(archiveName):
        return
    filenames = downloadImages(chapter, directory)
    if archive:
        archiveChapter(filenames, archiveName, clean, directory)

if __name__ == '__main__':
    main()

