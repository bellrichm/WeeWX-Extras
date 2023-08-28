#!/bin/env python3
#-----------------------------------------------------------------------------------------------------------------------------------
# Routine Name: s3upload.py
# Author:       Mike Revitt
# Date:         18/03/2020
#------------------------------------------------------------------------------------------------------------------------------------
# Revision History    Push Down List
# -----------------------------------------------------------------------------------------------------------------------------------
# Date        | Name        | Description
# ------------+-------------+--------------------------------------------------------------------------------------------------------
#             |             |
# 18/03/2020  | M Revitt    | Initial version
#-------------+-------------+--------------------------------------------------------------------------------------------------------
# Description:  Reads the CPU Temperature and populates the extraTemp1 variable with this data
#               Converts all data into Celcius first
#
# Issues:       None
#
# ***********************************************************************************************************************************
# Copyright 2020 Mike Revitt <mike@cougar.eu.com>. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# ***********************************************************************************************************************************
"""For uploading files to a remote server via S3"""

import logging
import os
import sys
import time
import mimetypes
import boto3

from    weewx.reportengine  import ReportGenerator
from    weeutil.weeutil     import to_bool
from    six.moves           import cPickle
from    datetime            import datetime
from    botocore.exceptions import ClientError
from    botocore.exceptions import ParamValidationError
from    botocore.exceptions import ProfileNotFound

log = logging.getLogger(__name__)

# =============================================================================
#                    Class S3Upload
# =============================================================================
class S3Upload(object):
    
    def __init__(self,
                 bucket,
                 profile,
                 region,
                 weewx_root,
                 html_root,
                 cache_control  = 120,
                 name           = "S3",
                 max_tries      = 3,
                 debug          = 0,
                 secure_data    = True):
                 
        self.bucket         = bucket
        self.profile        = profile
        self.region         = region
        self.weewx_root     = weewx_root
        self.html_root      = html_root
        self.cache_control  = cache_control
        self.name           = name
        self.max_tries      = max_tries
        self.debug          = debug
        self.secure_data    = secure_data

    def run(self):
        # Get the timestamp and members of the last upload:
        (timestamp, fileset)    = self.getLastUpload()
        n_uploaded              = 0
        
        try:
            session = boto3.Session(profile_name=self.profile, region_name=self.region)
            s3      = session.resource('s3')
        
        except ProfileNotFound as e:
            log.error("Failed to connect to resource S3: using profile '%s'" %(self.profile))
            exit(40)
    
        # Add some logging information
        log.debug("S3Upload started at: " + datetime.now().strftime('%d-%m-%Y %H:%M:%S') + "\n")
        
        # Walk the local directory structure
        for (dirpath, unused_dirnames, filenames) in os.walk(self.html_root):
            
            local_rel_dir_path  = dirpath.replace(self.html_root, '')
            s3_bucket_path      = local_rel_dir_path.lstrip( '/')
            
            if self._skipThisDir(local_rel_dir_path):
                continue

            # Now iterate over all members of the local directory:
            for filename in filenames:

                full_local_path = os.path.join(dirpath, filename)
                remote_object   = os.path.join( s3_bucket_path, filename )
                
                log.debug(remote_object)
                # See if this file can be skipped:
                if self._skipThisFile(timestamp, fileset, full_local_path):
                    continue
                
                # Retry up to max_tries times:
                for count in range(self.max_tries):

                    try:
                        mimetype, fileEncoding = mimetypes.guess_type(filename)
                        if mimetype is None:
                            mimetype = "text/plain"

                        log.debug("\nresponse=s3.meta.client.upload_file("+full_local_path+','+self.bucket+','+remote_object+')')
                        log.debug("\t\tExtraArgs={'CacheControl': %s" % ( self.cache_control ))
                        log.debug("\t\t\tContentType' : %s" % ( mimetype ))
                        
                        response = s3.meta.client.upload_file(full_local_path , self.bucket, remote_object,
                                                              ExtraArgs={'CacheControl': "%s" % ( self.cache_control ),
                                                                         'ContentType' : "%s" % ( mimetype ),
                                                                         'ACL'         : 'public-read' })

                    except IOError as e:
                        log.error("Attempt #%d. Failed uploading %s to %s/%s. \n\tReason: %s" %
                                  (count + 1, full_local_path, self.bucket, remote_object, e))

                    except ClientError as e:
                        log.error("Attempt #%d. Failed uploading %s to %s/%s. \n\tReason: %s" %
                                  (count + 1, full_local_path, self.bucket, remote_object, e))
                        break

                    except ParamValidationError as e:
                        log.error("Attempt #%d. Failed uploading %s to %s/%s. \n\tReason: %s" %
                                  (count + 1, full_local_path, self.bucket, remote_object, e))
                        break

                    except () as e:
                        log.error("Attempt #%d. Failed uploading %s to %s/%s. \n\tUnknown error occured $s" %
                                  (count + 1, full_local_path, self.bucket, remote_object, e ))
                        break

                    else:
                        # Success. Log it, break out of the loop
                        n_uploaded += 1
                        fileset.add(full_local_path)
                        log.debug("Uploaded file %s" % remote_object )
                        break
    
        timestamp = time.time()
        self.saveLastUpload(timestamp, fileset)
        return n_uploaded

    def getLastUpload(self):
        """Reads the time and members of the last upload from the local root"""

        timeStampFile = os.path.join(self.weewx_root, "#%s.last" % self.name)

        # If the file does not exist, an IOError exception will be raised.
        # If the file exists, but is truncated, an EOFError will be raised.
        # Either way, be prepared to catch it.
        try:
            with open(timeStampFile, "rb") as f:
                timestamp = cPickle.load(f)
                fileset = cPickle.load(f)
        except (IOError, EOFError, cPickle.PickleError, AttributeError):
            timestamp = 0
            fileset = set()
            # Either the file does not exist, or it is garbled.
            # Either way, it's safe to remove it.
            try:
                os.remove(timeStampFile)
            except OSError:
                pass

        return (timestamp, fileset)

    def saveLastUpload(self, timestamp, fileset):
        """Saves the time and members of the last upload in the local root."""
        timeStampFile = os.path.join(self.weewx_root, "#%s.last" % self.name)
        with open(timeStampFile, "wb") as f:
            cPickle.dump(timestamp, f)
            cPickle.dump(fileset, f)

    def _skipThisDir(self, local_dir):

        return os.path.basename(local_dir) in ('.svn', 'CVS')

    def _skipThisFile(self, timestamp, fileset, full_local_path):

        filename = os.path.basename(full_local_path)
        if filename[-1] == '~' or filename[0] == '#':
            return True

        if full_local_path not in fileset:
            return False

        if os.stat(full_local_path).st_mtime > timestamp:
            return False
            
        # Filename is in the set, and is up to date.
        return True

# =============================================================================
#                    Class S3UploadGenerator
# =============================================================================
class S3UploadGenerator(ReportGenerator):
    
    def run(self):
        import user.s3upload
        
        # determine how much logging is desired
        log_success = to_bool(self.skin_dict.get('log_success', True))
        
        t1 = time.time()
        try:
            S3_upload = user.s3upload.S3Upload(bucket           = self.skin_dict['S3_BUCKET'],
                                               profile          = self.skin_dict['AWS_Profile'],
                                               region           = self.skin_dict['AWS_Region'],
                                               weewx_root       = self.config_dict['WEEWX_ROOT'],
                                               html_root        = self.config_dict['StdReport']['HTML_ROOT'],
                                               cache_control    = self.config_dict['StdArchive']['archive_interval'],
                                               name             = self.skin_dict['skin'])
        except KeyError:
            log.error("S3UploadGenerator: AWS upload not requested. Skipped.")
            return
        
        try:
            n = S3_upload.run()
        except () as e:
            log.error("S3UploadGenerator: Caught exception %s: %s" % (e))
            return
        
        if log_success:
            t2 = time.time()
            log.info("S3UploadGenerator: AWS-S3 copied %d files to S3 in %0.2f seconds" % (n, (t2 - t1)))

# =============================================================================
#                    Main
# =============================================================================
if __name__ == '__main__':
    import configobj

    import weewx
    import weeutil.logger

    weewx.debug = 1

    weeutil.logger.setup('S3upload', {})
    
    if len(sys.argv) < 2:
        print("""Usage: s3upload.py path-to-configuration-file [path-to-be-ftp'd]""")
        sys.exit(weewx.CMD_ERROR)

    try:
        config_dict = configobj.ConfigObj(sys.argv[1], file_error=True, encoding='utf-8')
    except IOError:
        print("Unable to open configuration file %s" % sys.argv[1])
        raise

    S3_upload = S3Upload(config_dict['StdReport']['AWS-S3']['S3_BUCKET'],
                         config_dict['StdReport']['AWS-S3']['AWS_Profile'],
                         config_dict['StdReport']['AWS-S3']['AWS_Region'],
                         config_dict['WEEWX_ROOT'],
                         config_dict['StdReport']['AWS-S3']['HTML_ROOT'],
                         config_dict['StdArchive']['archive_interval'],
                         config_dict['StdReport']['AWS-S3']['skin'])

    print("\n========================================================================================\n")
    print("\tS3Upload started at: " + datetime.now().strftime('%d-%m-%Y %H:%M:%S') + " with the following parameters\n")
    print("\tBucket\tProfile\tRegion\tWEEWX_ROOT\tHTML_ROOT\tCache\tSkin")
    print("\t",
          config_dict['StdReport']['AWS-S3']['S3_BUCKET'],
          config_dict['StdReport']['AWS-S3']['AWS_Profile'],
          config_dict['StdReport']['AWS-S3']['AWS_Region'],
          config_dict['WEEWX_ROOT'],
          config_dict['StdReport']['HTML_ROOT'],
          config_dict['StdArchive']['archive_interval'],
          config_dict['StdReport']['AWS-S3']['skin'])
    print("\n========================================================================================\n")

    S3_upload.run()
