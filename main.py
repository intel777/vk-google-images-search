import vk
import requests
import json
import random
import os
import threading
import shutil
import datetime
import sys
import traceback
import imghdr

print('[GoogleImageSearch]Starting up...')
boot_ts = datetime.datetime.now()

cx = ''
googleApiKey = ''
vkToken = ''
searchUrl = 'https://www.googleapis.com/customsearch/v1?&cx=' + cx + '&key=' + googleApiKey + '&cx=' + cx + '&num=10&searchType=image&q='

print('[GoogleImageSearch]Initializing VK API')
api = vk.API(vk.AuthSession(access_token=vkToken), v=5.95)

print('[GoogleImageSearch]Initializing filesystem...')
if not os.path.exists('logs'):
    os.makedirs('logs')

log_path = 'logs/' + str(datetime.date.today()) + '_' + boot_ts.strftime('%H-%M-%S') + '.log'
if os.path.exists(log_path):
    os.remove(log_path)
open(log_path, 'w').close()

print('[GoogleImageSearch]Declarating functiions...')


def write_to_log(message):
    with open(log_path, 'a') as logfile:
        logfile.write(message)


def log_traceback(module_name, traceback_data):
    write_to_log('''
    [{}, TS: {}]
    {}
    '''.format(module_name, get_time_date_string(), traceback_data))


def get_time_date_string():
    now_time = datetime.datetime.now()
    current_time = now_time.strftime('%H-%M-%S')
    current_date = now_time.strftime('%d.%m.%y')
    return '{} {}'.format(current_date, current_time)


def tx(peer, text=None, images=None):
    if not text and not images:
        print('[{}][TX][Warn]: TX func called with no arguments'.format(get_time_date_string()))
        write_to_log('[{}][WARN][TX]TX function called with no arguments'.format(get_time_date_string()))
    else:
        api.messages.send(peer_id=peer, message=text, attachment=images, random_id=random.randint(1, 99999999999999999))


def search(query):
    response = []
    search_results = requests.get(searchUrl + query, timeout=10)
    print(search_results.text)
    try:
        search_results = json.loads(search_results.text)['items']
        for image in search_results:
            response.append(image['link'])
    except Exception:
        pass
    return response


def long_poll_refresh():
    print('[LongPollProvider]Refreshing longpoll...')
    longpoll_data = api.groups.getLongPollServer(group_id=)
    longpoll_key = longpoll_data['key']
    longpoll_server = longpoll_data['server']
    longpoll_ts = longpoll_data['ts']
    return longpoll_key, longpoll_server, longpoll_ts


class Uploader:
    result = []

    def __init__(self):
        self.result = []

    def image_uploader(self, file):
        retry_count = 0
        while retry_count < 2:
            try:
                print('[ImageUploader]Trying to upload image, try no.: {}'.format(retry_count))
                data = api.photos.getMessagesUploadServer()
                print('[ImageUploader]Data from VK received, uploading...')
                response = requests.post(data['upload_url'], files={'photo': open(file, 'rb')})
                if response.status_code == requests.codes.ok:
                    response = response.json()
                    print('[ImageUploader]Image successfully uploaded, saving...')
                    parameters = {'server': response['server'], 'photo': response['photo'], 'hash': response['hash']}
                    vk_photo = api.photos.saveMessagesPhoto(**parameters)
                    self.result.append('photo-{}_{}'.format(data['group_id'], vk_photo[0]['id']))
                    break
                else:
                    print('[ImageUploader]Error while uploading image, retrying...')
                    raise Exception
            except Exception:
                print('[ImageUploader]Upload failed. Writing to log and retrying...')
                retry_count += 1
                exc_type, exc_value, exc_traceback = sys.exc_info()
                lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
                traceback_str = ''.join(line for line in lines)
                log_traceback('Image Uploader', traceback_str)
                print(traceback_str)

    def upload_images(self, files):
        threads = []
        for file in files:
            threads.append(threading.Thread(target=self.image_uploader, args=(file,)))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return self.result


print('[GoogleImageSearch]Declarating classes...')


class Downloader:
    downloaderId = random.randint(1, 100000000)
    result = []

    def __init__(self):
        while os.path.exists(self.downloaderId):
            self.downloaderId = random.randint(1, 100000000)
        self.result = []
        os.makedirs(str(self.downloaderId))

    def download(self, link, filename):
        print('[Downloader]Downloading image...')
        image = requests.get(link, timeout=60)
        if image.status_code == requests.codes.ok:

            temp_name = '{}/temp_{}'.format(self.downloaderId, random.randint(1, 9999999999))
            with open(temp_name, 'wb') as temp_file:
                temp_file.write(image.content)
            image_type = imghdr.what(temp_name)
            os.remove(temp_name)

            image_name = '{}/{}.{}'.format(self.downloaderId, filename, image_type)
            with open(image_name, 'wb') as ImageFile:
                ImageFile.write(image.content)
            self.result.append(image_name)

    def get(self, links):
        i = 0
        threads = []
        for link in links:
            threads.append(threading.Thread(target=self.download, args=(link, i)))
            i += 1
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return self.result

    def destroy(self):
        shutil.rmtree(str(self.downloaderId))


print('[GoogleImageSearch]Declarating Threads...')


def long_poll_handler():
    print('[{}][LongPollHandler]Started'.format(get_time_date_string()))
    print('[{}][LongPollHandler]Getting LongPoll data...'.format(get_time_date_string()))
    long_poll_key, long_poll_server, long_poll_ts = long_poll_refresh()
    while True:
        try:
            response = requests.get(
                '{}?act=a_check&key={}&ts={}&wait=25'.format(long_poll_server, long_poll_key, long_poll_ts))
            long_poll_response = json.loads(response.text)
            try:
                long_poll_ts = long_poll_response['ts']
            except KeyError:
                print('[LongPollListner]LongPoll Error, initializing refreshment...')
                long_poll_key, long_poll_server, long_poll_ts = long_poll_refresh()
                continue
            for update in long_poll_response['updates']:
                print('[{}][LongPollHandler]Message received, processing'.format(get_time_date_string()))
                message_peer = update['object']['peer_id']
                message_from = update['object']['from_id']
                message_text = update['object']['text']
                if message_text:
                    print(
                        '[{}][LongPollHandler]Request received from: {}, peer: {}, q: {}'.format(get_time_date_string(),
                                                                                                message_from,
                                                                                                message_peer,
                                                                                                message_text))
                    if '[' in message_text and ']' in message_text:
                        begin = message_text.find('[')
                        end = message_text.find(']', begin) + 2
                        message_text = message_text[:begin] + message_text[end:]
                    search_results = search(message_text)
                    if search_results:
                        downloader = Downloader()
                        image_files = downloader.get(search_results)
                        uploader = Uploader()
                        vk_photos = uploader.upload_images(image_files)
                        downloader.destroy()
                        tx(message_peer, images=vk_photos)
                    else:
                        tx(message_peer,
                           text='По вашему запросу ничего не найдено, попробуйте его изменить и попробовать еще раз')
                else:
                    print(' [LongPollHandler]No text found. Ignoring')
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            traceback_str = ''.join(line for line in lines)
            log_traceback('Longpoll Listner', traceback_str)
            print(traceback_str)


print('[GoogleImageSearch]Starting threads...')
threading.Thread(target=long_poll_handler).start()
print('[{}]Boot complete in: {}'.format(get_time_date_string(), datetime.datetime.now() - boot_ts))
