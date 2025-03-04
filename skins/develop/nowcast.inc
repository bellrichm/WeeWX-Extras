##    Copyright (c) 2025 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your full rights.

#import datetime

Using the following 'current' timestamp, just because that is when I started to prototype testing SQL statements.<br>
#set $timestamp=1740168300

timestamp: $current(timestamp=$timestamp).dateTime.raw<br>
date: $current(timestamp=$timestamp).dateTime<br><br>

#set test_date = datetime.datetime(2025, 2, 21)
#set $ago = (datetime.datetime.now() - $test_date).days
I want the date to be 2/21, so set 'ago' to (current date - $test_date): $ago <br>
<br>

current pm2_5:   $current(timestamp=$timestamp).pm2_5<br>
current nowcast: $current(timestamp=$timestamp).pm2_5_aqi_nowcast<br>
<br>

Day Minimum:<br> 
NOWCAST aggregation is not yet supported<br>
nowcast: $day($days_ago=$ago).pm2_5_aqi_nowcast.min<br>
<br>

Day average:<br>
NOWCAST aggregation is not yet supported<br>
nowcast: $day($days_ago=$ago).pm2_5_aqi_nowcast.avg<br>
<br>

pm2_5 data for $test_date
<pre>
##$day($days_ago=$ago).pm2_5.series
</pre>
<br>

day nowcast (series) - not yet supported
    <pre>
$day($days_ago=$ago).pm2_5_aqi_nowcast.series
    </pre>
<br>

day nowcast (min aggregate series) - not yet supported
    <pre>
##$day($days_ago=$ago).pm2_5_aqi_nowcast.series(aggregate_type='min', aggregate_interval=3600)
    </pre>
<br>
