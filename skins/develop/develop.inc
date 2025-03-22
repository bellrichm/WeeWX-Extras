##    Copyright (c) 2025 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your full rights.

Use this to develop/test, keeping other include files 'pristine'

#import datetime

#*
$week.pm2_5.min
<br>
$week.pm2_5.series($aggregate_interval='day', $aggregate_type='min')
<br>

$week.pm2_5_aqi.min
<br>
$week.pm2_5_aqi.series($aggregate_interval='day', $aggregate_type='min')
<br>

$week.pm2_5_aqi_nowcast.min
<br>
##$week.pm2_5_aqi_nowcast.series($aggregate_interval='day', $aggregate_type='min')
<br>

$yesterday.pm2_5_aqi_nowcast.series($aggregate_interval='hour', $aggregate_type='min')
<br>
$yesterday.pm2_5_aqi_nowcast.series($aggregate_interval='hour', $aggregate_type='max')
<br>

$yesterday.pm2_5_aqi_nowcast.series($aggregate_interval=7200, $aggregate_type='max')
<br>
*#

#set test_date = datetime.datetime(2025, 2, 21)
#set $ago = (datetime.datetime.now() - $test_date).days
I want the date to be 2/21, so set 'ago' to (current date - $test_date): $ago <br>
<br>
$day($days_ago=$ago).pm2_5_aqi_nowcast.series($aggregate_type='max', $aggregate_interval=10800)
