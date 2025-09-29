#!/usr/bin/env python

import subprocess
repos_dir = '/home/richbell/weewx_code/'
weewx_dir = '/home/richbell/weewx'
repos = ['weewx-gw1000',  'weewx-extensions/aqi-xtype', 'WeeWX-Extras', 'weewx-extensions/healthchecks', 'weewx-extensions/jas', 'weewx-mqtt/publish', 'WeeWX-MQTTSubscribe', 'weewx-extensions/pushover', 'vds-weewx-v3-mem-extension', 'weewx-cmon', 'configs', 'secrets']

command = ['git', 'fetch', '--quiet']
print(f'\nRunning command: {" ".join(command)}')
try:
    process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd=weewx_dir)
    output, unused_err = process.communicate()
    print(f'weewx: {output.decode("utf-8")}')
except FileNotFoundError:
    print(f'{weewx_dir} does not exist')

for repo in repos:
    try:
        cwd = f'{repos_dir}{repo}'
        process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd=cwd)
        output, unused_err = process.communicate()
        print(f'{repo}: {output.decode("utf-8")}')
    except FileNotFoundError:
        print(f'{repo} does not exist')

command = ['git', 'status', '--branch', '-uno', '--null']
#command = ['git', 'log', 'HEAD..origin/master']
print(f'\nRunning command: {" ".join(command)}')
try:
    process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd=weewx_dir)
    output, unused_err = process.communicate()
    print(f'weewx: {output.decode("utf-8")}')
except FileNotFoundError:
    print(f'{weewx_dir} does not exist')

for repo in repos:
    try:
        cwd = f'{repos_dir}{repo}'
        process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd=cwd)
        output, unused_err = process.communicate()
        print(f'{repo}: {output.decode("utf-8")}')
    except FileNotFoundError:
        print(f'{repo} does not exist')

command = ['git', 'log', '--format=format:"%ci %h %d %s"', '-n 1']
#command = ['git', 'log', 'HEAD..origin', '--format=format:"%ci %h %d %s"']
print(f'\nRunning command: {" ".join(command)}')
try:
    process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd=weewx_dir)
    output, unused_err = process.communicate()
    print(f'weewx: {output.decode("utf-8")}')
except FileNotFoundError:
    print(f'{weewx_dir} does not exist')

for repo in repos:
    try:
        cwd = f'{repos_dir}{repo}'
        process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd=cwd)
        output, unused_err = process.communicate()
        print(f'{repo}: {output.decode("utf-8")}')
    except FileNotFoundError:
        print(f'{repo} does not exist')

print("\nFor more information run the following commands from the repository directory.")
print('  git log HEAD..origin --format="format:%ci %h %d %s"')
print('  git diff HEAD...origin/master')
