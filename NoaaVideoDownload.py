#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
@Description: 
@Author: wk
@Email: 1195041339@qq.com
@Github: https://github.com//wwwonekey
@LastEditors: wk
@Date: 2019-03-31 20:11:01
@LastEditTime: 2019-04-01 14:24:10
'''
import os
import sys
import time
import threading
from bs4 import BeautifulSoup
import urllib.request
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import urllib.error
requests.packages.urllib3.disable_warnings()
class HttpDataDownloader():

    def __init__(self, dl_url=None, output_dir=None, threads=10, mirror=True, verbose=False, debug=False):

        if not dl_url:
            self.clear_screen()
            print('[x] ERROR: Please Provide Download URL and Try Again')
            time.sleep(3)
            sys.exit()

        self.download_url = dl_url
        self.verbose = verbose
        self.debug = debug
        self.threads = threads
        self.mirror = mirror
        self.file_count_lock = threading.Lock()
        self.file_count = 0

        if os.name == 'nt':
            self.host_os = 'windows'
        elif os.name == 'posix':
            self.host_os = 'posix'

        self.clear_screen()

        # Validate The Initial URL
        try:
            urllib.request.urlopen(dl_url)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print('[x] ERROR: Failed to open URL: ', dl_url)
            # print('[x] Error Msg: ', e.reason)
            print('\n[x] Please Check URL And Try Again')
            time.sleep(5)
            sys.exit()

        if not output_dir:
            print('[!] No output directory given.  CWD will be used. ')
            # response = input('[?] Do You Wish To Proceed? (y/n)')
            if response.lower() == 'n' or response.lower() == 'no':
                # print('[!] Please use --output to specify output directory')
                time.sleep(4)
                sys.exit()
            else:
                self.output_dir = os.getcwd()
        else:
            self.output_dir = output_dir

    def run(self):
        """
        This method executes the actual download.  It calls the parse_remote_dir_tree method and waits for
        it to return.  Once it returns it waits until all download threads have finishes.  Prior to threads
        finishing it prints a list of the files currently being downloaded
        :return:
        """

        print('[+] Starting Parse And Download Of ' + self.download_url)
        if self.output_dir:
            print('[+] Output Directory is: ' + self.output_dir + '\n')

        self.parse_remote_dir_tree(self.download_url, '')

        if self.verbose:
            print('[!] All Download Threads Launched.\n')

        last_active = 0
        # while threading.active_count() > 6:
        #     if last_active != threading.active_count():
        #         self.clear_screen()
        #         print('---------- ACTIVE DOWNLOAD THREADS ----------')
        #         print('The Following ', threading.active_count() - 1, ' files are still downloading')
        #         for thrd in threading.enumerate():
        #             if thrd.name.lower() == 'mainthread':
        #                 continue
        #             print('[+] ', thrd.name)
        #     last_active = threading.active_count()
        #     time.sleep(1)

        self.clear_screen()
        print('[!] Success: ' + str(self.file_count) + ' Files Have Been Downloaded')
        time.sleep(5)
        self.clear_screen()

    def parse_remote_dir_tree(self, url, mydir, path='', previous=None):
        """
        Crawl a directory listing of a URL and find all files.  Each call of the function builds a
        list of all files and directories at the current level.  It then calls _threaded_download()
        for each file.  It then calls itself again for each directory.
        :param url: The URL to parse. Starts with base url and recursivly calls deeper URL
        :param dir: Current dir at time of calling function. Used to build of new URL
        :param path: Builds of the path of folders crawled into.  Used to build of URL
        :param previous:
        :return:
        """
        dirs = []
        files = []

        if path == '/':
            path = path + mydir
        else:
            path = path + '/' + mydir

        # TODO This is failing on Linux for some dumb reason.
        try:
            response = urllib.request.urlopen(url)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print('[x] ERROR: Failed to open URL: ', url)
            # print('[x] Error Msg: ', e.reason)
            return

        parsed_page = BeautifulSoup(response,features="html.parser")

        for link in parsed_page.find_all('a'):

            # Avoid climbing back to previous level
            if(link.string == 'Parent Directory' or link.string == 'Name' 
            or link.string == 'Last modified' or link.string == 'Size' or link.string == 'Description'):
                if self.verbose:
                    print('[+] Skipping ' + link.string)
                continue

            if not link.string:
                self.clear_screen()
                print('[x] ERROR: No Links Found On Given URL')
                time.sleep(5)
                return

            # Get file name and extension.  If directory ext will be None
            name, ext = os.path.splitext(link.string)

            if ext:
                if self.verify_url_directory(url + '/' + link.string):
                    files.append(link.string)
                else:
                    dirs.append(link.string)
            else:
                dirs.append(link.string)

        for file in files:
            replace_file = file.replace(" ","%20")
            download_url = url + '/' + replace_file

            while threading.active_count() > self.threads:
                print('[x] Max download threads reached.  Waiting for threads to decrease')
                time.sleep(2)

            output_file = '/' + file

            time.sleep(0.02)
            if self.verbose:
                print('[+] New Thread URL: ' + download_url)
                print('[+] New Thread File: ' + output_file)
            # orifin_output_file = output_file
            # output_file.replace(" ","%20")
            # print(output_file)
            t = threading.Thread(target=self._threaded_download, name=os.path.basename(output_file),
                                 args=(download_url, output_file, path,))
            t.start()

        for folder in dirs:
            # First entry can be blank. Skip Iteration
            folder = folder.replace(" ","%20")
            if not folder:
                continue
            # TODO Don't think this check is needed. Verify. Remove from args if not needed
            if folder == previous:
                continue

            # TODO Hackish?
            # Add trailing slash
            if url[-1:] != '/':
                url += '/'

            if self.verbose:
                print('[+] Calling parse_remote_dir_tree with URL: ' + url + folder)

            next_url = url + folder

            self.parse_remote_dir_tree(next_url, folder, path=path, previous=dir)
    
    # 断点续传
    def download(self,url, file_path,local_file_size,remote_file_size):
        session = requests.session()
        session.keep_alive = False 
        retry = Retry(connect=5, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)
        total_size = remote_file_size
        temp_size = local_file_size
        # 核心部分，这个是请求下载时，从本地文件已经下载过的后面下载
        headers = {'Range': 'bytes=%d-' % temp_size,'Connection': 'close','User-Agent':'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'}  
        # 重新请求网址，加入新的请求头的
        r = session.get(url, stream=True, verify=False, headers=headers,timeout=5)
        # 下面写入文件也要注意，看到"ab"了吗？
        # "ab"表示追加形式写入文件
        with open(file_path, "ab") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    temp_size += len(chunk)
                    f.write(chunk)
                    f.flush()

    def _threaded_download(self, download_url, output_file, path):
        """
        Download the passed in file and output to the global output dir.
        :param download_url: The URL to download
        :param output_file: The file name and path of the local file
        :return: None
        """

        if self.host_os == 'windows':
            output_file = output_file.replace(r'/', '\\')
            path = path.replace('/', '\\')

        # Don't append path if we're currently dealing with a file in the root
        if path == '\\':
            final_output_file = self.output_dir + output_file
        else:
            final_output_file = self.output_dir + path + output_file

        # Make output dir if it does not exists
        if not os.path.exists(os.path.dirname(final_output_file)):
            os.makedirs(os.path.dirname(final_output_file))

        # Comment
        try:
            with urllib.request.urlopen(download_url) as response:
                # If mirror is enabled and file exists check if remote file is newer than local.
                if os.path.isfile(final_output_file) and self.mirror:
                    # local_last_modified = self.get_local_timestamp(final_output_file)
                    local_file_size = self.get_local_filesize(final_output_file)
                    # remote_last_modified = self.get_remote_timestamp(response.info()['Content-Length'])
                    remote_file_size = self.get_remote_filesize(response.info()['Content-Length'])

                    # This func call may not be needed but may add more checks later
                    # if self.mirror_compare_time(local_last_modified, remote_last_modified):
                    if self.mirror_compare_size(local_file_size, remote_file_size):
                        if self.debug:
                            print('[+] Continue Downloading File: ', output_file)
                        self.download(download_url,final_output_file,local_file_size,remote_file_size)
                        if self.verbose:
                            print('[+] MIRROR: Remote File Is Newer: ' + output_file)
                    else:
                        if self.verbose:
                            print('[+] MIRROR: Remote File Not Newer: ' + output_file)
                        return
                else:
                    if self.debug:
                        print('[+]  Downloading File: ', output_file)
                    out_file = open(final_output_file.rstrip(), 'wb')
                    data = response.read()
                    out_file.write(data)
                    out_file.close()

                try:
                    self.file_count_lock.acquire()
                    self.file_count += 1
                finally:
                    self.file_count_lock.release()

        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print('[x] ERROR: Failed to download: ', download_url)
            # print('[x] ERROR MSG: ' + e.msg)

        if self.verbose:
            print('[!] Thread Ending: ', output_file)

    def mirror_compare_time(self, local_file, remote_file):
        if self.debug:
            print('[?] Local File Size: ' + str(local_file))
            print('[?] Remote File Size: ' + str(remote_file))
        return True if remote_file > local_file else False
    
    def mirror_compare_size(self, local_filesize, remote_filesize):
        if self.debug:
            print('[?] Local File Size: ' + str(local_filesize))
            print('[?] Remote File Size: ' + str(remote_filesize))
        return True if remote_filesize > local_filesize else False

    def get_remote_timestamp(self, last_modified):
        """
        Convert the Last-Modified header time into epoch time
        :param last_modified: Last-Modified header timestamp
        :return: epoch time
        """
        if self.debug:
            print('[+] get_remote_timestamp called with: ' + last_modified)
        temp_time = time.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z")
        #return time.mktime(time.strptime(last_modified, "%a, %d %b %Y %I:%M:%S %Z"))
        return round(time.mktime(temp_time))
    
    def get_remote_filesize(self, last_modified):
        """
        Convert the Last-Modified header time into epoch time
        :param last_modified: Last-Modified header timestamp
        :return: epoch time
        """
        if self.debug:
            print('[+] get_remote_timestamp called with: ' + last_modified)
        # temp_time = time.strptime(last_modified, "%a, %d %b %Y %H:%M:%S %Z")
        #return time.mktime(time.strptime(last_modified, "%a, %d %b %Y %I:%M:%S %Z"))
        return int(last_modified)

    def get_local_timestamp(self, local_file):
        # TODO Sort out local timzone.  + 18000 is a temp fix for time difference
        return round(os.path.getmtime(local_file) + 18000)
    
    def get_local_filesize(self, local_file):
        return round(os.path.getsize(local_file))
    
    def clear_screen(self):
        """
        Clear the screen.  Issue the correct command for OS running this script
        :return:
        """
        if self.host_os == 'windows':
            os.system('cls')
        elif self.host_os == 'posix':
            os.system('clear')

        print('\n')

    def verify_url_directory(self, url):
        """
        Test if the given URL is actually a directory.  This prevents folders with a . in the name from being treated
        as files.
        The request will return a 404 if it's actually a file due to the trailing slash
        :param url:
        :return:
        """
        try:
            urllib.request.urlopen(url + "/")
            return False
        except urllib.error.HTTPError:
            return True

def main():
    dl_url = "https://data.nodc.noaa.gov/oer/video/Biolum2009/Imagery/"
    output_dir = "F:\\海洋所\\NOAA数据"
    downloader = HttpDataDownloader(dl_url=dl_url, output_dir=output_dir,verbose = True)
    try:
        downloader.run()
    except KeyboardInterrupt:
        print('[!] Keyboard Quit Detected')

if __name__ == '__main__':
    main()