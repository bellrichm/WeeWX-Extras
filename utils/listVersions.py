#
import subprocess
repos_dir = '/home/richbell/weewx_code/'
weewx_dir = '/home/richbell/weewx'
repos = ['weewx-gw1000',  'weewx-aqi-xtype', 'WeeWX-Extras', 'weewx-healthchecks', 'weewx-jas', 'weewx-mqttpublish', 'WeeWX-MQTTSubscribe', 'weewx-pushover', 'vds-weewx-v3-mem-extension', 'weewx-cmon', 'configs', 'secrets']

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

