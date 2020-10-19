import os
import socket
import time
import select
import logging
import sys
import xml.etree.ElementTree as ET
import datetime
from datetime import timezone
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
import email.encoders
import ftputil
from enum import Enum

def send_mail(status, text):
    flag = True
    filepath = os.path.dirname(os.path.abspath(sys.argv[0])) + '\\server.log'
    basename = os.path.basename(filepath)
    try:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(filepath, "rb").read())
        email.encoders.encode_base64(part)
    except FileNotFoundError:
        flag = False
    part.add_header('Content-Disposition', 'attachment; filename="%s"' % basename)
    addr_from = "email@email.ru"
    addr_to = "email@email.ru"
    addr_cc = ""
    password = "pass"
    msg = MIMEMultipart()
    msg['From'] = addr_from
    msg['To'] = addr_to
    msg['cc'] = addr_cc
    msg['Subject'] = status
    body = text
    msg.attach(MIMEText(body, 'plain'))
    if flag == True:
        msg.attach(part)
    server = smtplib.SMTP('mx.url.ru')
    server.starttls()
    server.login(addr_from, password)
    server.send_message(msg)
    server.quit()


flag = False
detla = 0
period_con = 60
period_lost = 3600
start_time = time.time()
reconn_time = 0
reconn_time_start = 0
start_ftp = 0
check_break = True

tree = ET.parse('''C:\Program Files (x86)\CRP\CM\\StreamServer\config.xml''')
doc = tree.getroot()
log = doc.find('.//converter/ftp/login').text
port = doc.find('.//converter/ftp/port').text
pas = doc.find('.//converter/ftp/password').text
url = doc.find('.//converter/ftp/streamUrl').text
url = '/stream000447/'
ip = "ftp.url.ru"


def chekFTP():
    global flag
    global reconn_time_start
    global ftp_check_time
    global check_break
    try:
        host = ftputil.FTPHost(ip, log, pas)
        flag = True
        host.listdir(url)
        if check_break == True:
            list = []
            for datecreate in host.listdir(url):
                date_sort = host.path.getmtime(os.path.join(url, datecreate))
                list.append(date_sort)
                if start_ftp == 0 or time.time - start_ftp >= period_con:
                    list_sort = sorted(list, key=float, reverse=True)
                    i = 0
                    list_send = []
                    while i < len(list_sort) - 1:
                        if list_sort[i] - list_sort[i + 1] >= period_lost:
                            x = datetime.datetime.fromtimestamp(list_sort[i]).replace(tzinfo=timezone.utc).astimezone(tz=None)
                            y = datetime.datetime.fromtimestamp(list_sort[i + 1]).replace(tzinfo=timezone.utc).astimezone(tz=None)
                            list_send.append(x.strftime('%d/%m/%Y %H:%M:%S') + '  -  ' + y.strftime('%d/%m/%Y %H:%M:%S'))
                        i = i + 1
            if time.time() - list_sort[0] >= period_lost:
                list_send.append(time.strftime('%d/%m/%Y %H:%M:%S') + '  -  ' + datetime.datetime.utcfromtimestamp(list_sort[0]).strftime('%d/%m/%Y %H:%M:%S'))
            if list_send != []:
                send_mail('Detected interrupts in uploading process', '\n'.join(list_send))
            check_break = False
        ftp_check_time = time.time() + period_con
        if reconn_time_start == 1:
            send_mail('Reconnection before long lost', datetime.datetime.now())
            reconn_time_start = 0
            check_break = True
    except ftputil.error.FTPOSError:
        print('Error')
        if flag == False:
            ftp_check_time = time.time() + period_con
        else:
            send_mail('Connection long lost', datetime.datetime.now())
            ftp_check_time = time.time() + period_con
            reconn_time_start = 1


def chekFTPhour():
    host = ftplib.FTP(ip)
    host.login(log, pas)
    flag_mail = True
    entries = list(host.mlsd(url))
    entries.sort(key=lambda entry: entry[1]['modify'], reverse=True)
    latest_time = entries[0][1]['modify']
    latest_timeunix = datetime.strptime(latest_time, '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc).timestamp()
    if time.time() - latest_timeunix >=period_lost and flag_mail == True:
        send_mail('No unloading more than an hour from FTP', 'Last upload from FTP to ' + datetime.strptime(latest_time, '%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M:%S'))
        flag_mail = False


logging.basicConfig(filename="server.log", filemode='w', level=logging.INFO, format='%(asctime)s %(message)s')


class ConnectionState(Enum):
    NOT_CONNECTED = 0
    WAIT_CONNECTION = 1
    CONNECTED = 2


connectionState = ConnectionState.WAIT_CONNECTION
timeout = 600

last_ping = time.time()

sock = None

sock = socket.socket()
sock.bind(('127.0.0.1', 39990))
print('Wait connection...')
sock.settimeout(30)
sock.listen(0)

def chek():
    global connectionState
    global last_ping
    global sock
    global timeout
    if connectionState == ConnectionState.WAIT_CONNECTION:
        if time.time() - last_ping >= timeout:
            last_ping = time.time()
            print("NOT_CONNECTED")
            connectionState = ConnectionState.NOT_CONNECTED
            logging.error("NOT_CONNECTED")
            send_mail('Disconnected from object', datetime.datetime.now())


while True:
    chek_hour = time.time()
    try:
        chek()
        chekFTP()
        if chek_hour - time.time() >= period_lost:
            chekFTPhour()
            chek_hour = time.time()
        if connectionState is ConnectionState.NOT_CONNECTED or connectionState is ConnectionState.WAIT_CONNECTION:
            read_list = [sock]
            readable, writable, exceptional = select.select(read_list, [], [], 10)
            if not (readable or writable or exceptional):
                print("CONNECTION_TIMEOUT")
                if time.time() >= ftp_check_time:
                    start_time = time.time()
                continue
            conn, addr = sock.accept()
            conn.settimeout(15)
            print("CONNECTED")
            chekFTP()
            connectionState = ConnectionState.CONNECTED
            logging.info("CONNECTED")
            send_mail('Connected from Vavilova', datetime.datetime.now())
        data = conn.recv(1024).decode()
        print(data)
        res = ''
        if data == 'ping':
            res = 'pong'
            last_ping = time.time()
            conn.send(res.encode())
            logging.info("PING")
            if time.time() >= ftp_check_time:
                start_time = time.time()
            continue
        else:
            conn.close()
            connectionState = ConnectionState.WAIT_CONNECTION
    except (ConnectionResetError, socket.timeout) as error:
        connectionState = ConnectionState.WAIT_CONNECTION
        logging.info('WAIT_CONNECTION')
sock.close()