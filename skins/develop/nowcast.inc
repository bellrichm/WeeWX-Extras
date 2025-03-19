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

NOWCAST aggregation is not yet supported<br>
nowcast not_null:  $day($days_ago=$ago).pm2_5_aqi_nowcast.not_null
nowcast count:     $day($days_ago=$ago).pm2_5_aqi_nowcast.count
nowcast sum:       $day($days_ago=$ago).pm2_5_aqi_nowcast.sum
nowcast avg:       $day($days_ago=$ago).pm2_5_aqi_nowcast.avg
nowcast min:       $day($days_ago=$ago).pm2_5_aqi_nowcast.min
nowcast max:       $day($days_ago=$ago).pm2_5_aqi_nowcast.max
nowcast mintime:   $day($days_ago=$ago).pm2_5_aqi_nowcast.mintime
nowcast maxtime:   $day($days_ago=$ago).pm2_5_aqi_nowcast.maxtime
nowcast first:     $day($days_ago=$ago).pm2_5_aqi_nowcast.first
nowcast last:      $day($days_ago=$ago).pm2_5_aqi_nowcast.last
nowcast firsttime: $day($days_ago=$ago).pm2_5_aqi_nowcast.firsttime
nowcast lasttime:  $day($days_ago=$ago).pm2_5_aqi_nowcast.lasttime
<br>

pm2_5 series data for $test_date
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
