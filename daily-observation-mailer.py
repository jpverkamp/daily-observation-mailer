#!/usr/bin/env python3

import datetime
import dateutil.relativedelta
import email.mime.text
import logging
import smtplib
import tarfile
import os
import sys

ROOT = os.path.expanduser('~/Dropbox/Observations')
DEBUG_MODE = '--debug' in sys.argv

if DEBUG_MODE:
    logging.basicConfig(level = logging.DEBUG)


def get_content(years_ago):
    logging.info('Fetching content for {} years ago'.format(years_ago))

    date = (
        datetime.datetime.now()
        - dateutil.relativedelta.relativedelta(years = years_ago)
    )

    content = None
    ymstr = date.strftime('%Y-%m')
    datestr = date.strftime('%Y-%m-%d.txt')

    logging.info('Target ymstr: {}, datestr: {}'.format(ymstr, datestr))

    # We haven't archived a year ago yet
    path = os.path.join(ROOT, ymstr, datestr)
    if os.path.exists(path):
        with open(path, 'r') as fin:
            logging.info('Loaded content directly from file')
            content = fin.read()

    # We have archived it
    else:
        path = os.path.join(ROOT, date.strftime('%Y.tgz'))
        if os.path.exists(path):
            with tarfile.open(path, 'r') as tf:
                for ti in tf.getmembers():
                    # Skip mac files
                    if '._' in ti.name:
                        continue

                    # We found the individual date
                    if ti.name.endswith(datestr):
                        fin = tf.extractfile(ti)
                        content = fin.read().decode('utf-8', 'replace')
                        logging.info('Loaded content from individual file')
                        fin.close()

                    # Found another tarball with the month
                    elif ymstr in ti.name and ti.name.endswith('tgz'):
                        logging.info('Detected nested tarball')
                        with tf.extractfile(ti) as tf2_fin:
                            with tarfile.open(path, 'r') as tf2:
                                for ti2 in tf2.getmembers():
                                    if ti2.name.endswith(datestr):
                                        fin = tf2.extractfile(ti2)
                                        content = fin.read().decode('utf-8', 'replace')
                                        logging.info('Loaded content from nested tarball')
                                        fin.close()

                    if content:
                        break

    return content

def naturals(i = 0):
    while True:
        yield i
        i += 1

content = ''
for years_ago in naturals(1):
    year_content = get_content(years_ago)
    if year_content:
        content += '\n=== {year} ===\n\n{content}\n'.format(
            year = datetime.datetime.now().year - years_ago,
            content = year_content
        )
    else:
        break

if DEBUG_MODE:
    print(content)
    sys.exit(0)

# Generate a plaintext email and send it
msg = email.mime.text.MIMEText(content, _charset = 'utf-8')
msg['Subject'] = 'Daily observations'
msg['From'] = os.environ['EMAIL_TO']
msg['To'] = os.environ['EMAIL_TO']

smtp = smtplib.SMTP_SSL(os.environ['EMAIL_HOST'], int(os.environ['EMAIL_PORT']))
smtp.ehlo()
smtp.login(os.environ['EMAIL_USER'], os.environ['EMAIL_PASS'])
smtp.sendmail(os.environ['EMAIL_TO'], [os.environ['EMAIL_TO']], msg.as_string())
smtp.quit()


