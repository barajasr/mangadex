#! /usr/bin/env python3
#
# Author: Richard Barajas
# Email : barajasr89@gmail.com
# Date  : 2018.05.21
#

import argparse
import bs4
import os.path
import subprocess
import urllib3

parser = argparse.ArgumentParser()
parser.add_argument('url',
                    type=str,
                    help='Url of the first page of chapter requesting.')
parser.add_argument('-r', '--rar',
                  type=str,
                  default='',
                  help='Archive manga pages with target filename.')
parser.add_argument('-c', '--clean',
                    help='Set to clean up images no longer needed after archiving.',
                    action='store_true')

def archive(filenames, archiveName, clean=False):
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

def getImageList(url):
    http = urllib3.PoolManager()
    resp = http.request('GET', url)
    soup = bs4.BeautifulSoup(resp.data.decode(), 'lxml')

    # Find current page one image
    img = soup.find('img', id='current_page')
    source = img['src']
    # Some images have a prefix before page number
    position = source.rfind('1')
    base, post = source[:position], source[position+1:]

    # Assumes that all images are stored in same directory
    # Otherwise, requires parse each page for image src
    # Find dropdown menu for number of pages to request
    pages = len(soup.find('div', {'class': 'col-md-2'}).find_all('option'))
    return [base + str(i) + post for i in range(1, pages + 1)]

def downloadImages(imageUrls):
    print('Pages to download:', len(imageUrls))

    pos = imageUrls[0].rfind('/')
    for image in imageUrls:
        filename = image[pos + 1 :]
        if not os.path.isfile(filename):
            command = 'wget -q --show-progress {}'.format(image)
            subprocess.call(command.split())
        else:
            print(filename, '\tAlready exists.')

def main():
    args = parser.parse_args()
    if args.rar and os.path.isfile(args.rar):
        print("Archive '" + args.rar + "' already exists.")
        return

    pageUrls = getImageList(args.url)
    downloadImages(pageUrls)
    
    if args.rar:
        filenames = [filename[filename.rfind('/')+1:] for filename in pageUrls]
        archive(filenames, args.rar, args.clean)

if __name__ == '__main__':
    main()

