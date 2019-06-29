import requests
import time
import pandas as pd
import datetime
import os
import atexit


'''
Author: Jonathan Chow
Date Modified: 2018-11-01
Python Version: 3.7

General IO functions to be used by both production and development scripts
'''


recordsDirs = {'intermediate': 'APIBackup/Intermediate/',
               'permanent': 'APIBackup/Permanent/',
               'temporary': 'APIBackup/Temporary/'}
path = str(os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))) + '/'


def getNHLURL(**kwargs):
    urlAttributes = {'baseURL': 'https://statsapi.web.nhl.com/api/v1/'}
    urlAttributes.update(kwargs)

    try:
        url = urlAttributes['baseURL'] + '/'.join(urlAttributes['sArgs'])

        if 'qArgs' in urlAttributes:
            url += '?' + '&'.join(urlAttributes['qArgs'])

        return url
    except KeyError as ex:
        print(str(datetime.datetime.now()) + ': Invalid URL attribute ' + str(ex))
        exit()


def readJson(fileName):
    return pd.read_json(path + fileName + '.json')


def readDataFrame(fileName, isMultiIndex):
    dataFile = open(path + fileName + '.csv', mode='r')

    if isMultiIndex:
        data = pd.read_csv(dataFile, encoding='utf-8', index_col=[0, 1])
        data.index = [data.index.get_level_values(0).astype(str), data.index.get_level_values(1)]
    else:
        data = pd.read_csv(dataFile, encoding='utf-8', index_col=0)
        data.index = data.index.astype(str)

    dataFile.close()

    return data


def writeDataFrame(data, fileName):
    dataFile = open(path + fileName + '.csv', mode='w')
    data.to_csv(dataFile, encoding='utf-8', index=True)
    dataFile.close()


def writeLog(message):
    # Fatal errors will print to screen, but any other get put in the log file
    logFile = open(path + 'Strategies/log.txt', mode='a')
    logFile.write(message)
    logFile.close()


def readTxt(fileName):
    try:
        return 0, open(path + fileName + '.txt', mode='r', encoding='utf-8').read()
    except FileNotFoundError:
        return -1, ''


def writeTxt(fileName, message):
    txtFile = open(path + fileName + '.txt', mode='w', encoding='utf-8')
    txtFile.write(message)
    txtFile.close()


def inPermanent(url):
    localUrl = url.replace(':', '-').replace('/', '-')
    status, webText = readTxt(recordsDirs['permanent'] + localUrl)

    return True if status == 0 else False


def accessAPI(url, searchIn):
    localUrl = url.replace(':', '-').replace('/', '-')

    if searchIn == 'intermediate':
        # Intermediate data is best to be pulled each time, but can be reused if API is offline
        status, webText = httpHandler(url, 1)

        if status == 0:
            writeTxt(recordsDirs[searchIn] + localUrl, webText)
            return status, webText
        else:
            writeLog(str(datetime.datetime.now()) + ': Unable to update ' + url + '\n')
            return readTxt(recordsDirs[searchIn] + localUrl)
    else:
        try:
            # Attempt to first pull local copy of permanent and temporary data
            status, webText = readTxt(recordsDirs[searchIn] + localUrl)

            if status == -1:
                status, webText = httpHandler(url, 1)

                if status == 0:
                    writeTxt(recordsDirs[searchIn] + localUrl, webText)

            return status, webText
        except KeyError as ex:
            print(str(datetime.datetime.now()) + ': Invalid save type (permanent/intermediate/temporary) ' + str(ex))
            exit()


def httpHandler(url, attempts):
    if attempts > 5:
        writeLog(str(datetime.datetime.now()) + ': Attempt limit exceeded to ' + url + '\n')
        return -1, ''
    else:
        try:
            request = requests.get(url)

            if 200 <= request.status_code < 300:
                # Success
                status = 0
                webText = request.text
            elif request.status_code == 429:
                # Sent too many requests too quickly
                writeLog(str(datetime.datetime.now()) + ': Too many requests to ' + url + '\n')
                time.sleep(900)
                status, webText = httpHandler(url, attempts + 1)
            else:
                writeLog(str(datetime.datetime.now()) + ': Received HTTP response code ' +
                         str(request.status_code) + ' from ' + url + '\n')
                time.sleep(300)
                status, webText = httpHandler(url, attempts + 1)
        except ConnectionResetError:
            writeLog(str(datetime.datetime.now()) + ': Connection to ' + url + ' reset by peer\n')
            status, webText = httpHandler(url, attempts + 1)
        except ConnectionAbortedError:
            writeLog(str(datetime.datetime.now()) + ': Connection to ' + url + ' aborted (likely lost power in Icon)\n')
            time.sleep(3600)
            status, webText = httpHandler(url, attempts + 1)

        return status, webText


def clearTemporaryBackup():
    for removeFile in os.listdir(path + recordsDirs['temporary']):
        if removeFile.endswith('.txt'):
            os.remove(os.path.join(path + recordsDirs['temporary'], removeFile))


########################################################################################################################
atexit.register(clearTemporaryBackup)
