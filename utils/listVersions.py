#
import subprocess
repos_dir = '/home/pi/weewx_code/'
repos = ['weewx-gw1000',  'weewx-aqi-xtype', 'WeeWX-Extras', 'weewx-healthchecks', 'weewx-jas', 'weewx-mqttpublish', 'WeeWX-MQTTSubscribe', 'weewx-pushover', 'vds-weewx-v3-mem-extension', 'weewx-cmon', 'configs', 'secrets']

command = ['git', 'fetch', '--quiet']
process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd='/home/pi/weewx')
output, unused_err = process.communicate()
print(f'\nweewx: {output.decode("utf-8")}')

for repo in repos:
    try:
        cwd = f'{repos_dir}{repo}'
        process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd=cwd)
        output, unused_err = process.communicate()
        print(f'{repo}: {output.decode("utf-8")}')
    except FileNotFoundError:
        print(f'{repo} does not exist')

command = ['git', 'status', '--branch', '-uno', '--null']
process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd='/home/pi/weewx')
output, unused_err = process.communicate()
print(f'\nweewx: {output.decode("utf-8")}')

for repo in repos:
    try:
        cwd = f'{repos_dir}{repo}'
        process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd=cwd)
        output, unused_err = process.communicate()
        print(f'{repo}: {output.decode("utf-8")}')
    except FileNotFoundError:
        print(f'{repo} does not exist')

command = ['git', 'log', '--format=format:"%ci %h %d %s"', '-n 1']
process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd='/home/pi/weewx')
output, unused_err = process.communicate()
print(f'\nweewx: {output.decode("utf-8")}')

for repo in repos:
    try:
        cwd = f'{repos_dir}{repo}'
        process = subprocess.Popen(command, stdout=subprocess.PIPE, cwd=cwd)
        output, unused_err = process.communicate()
        print(f'{repo}: {output.decode("utf-8")}')
    except FileNotFoundError:
        print(f'{repo} does not exist')

