#!/usr/bin/env python
#
#    Copyright (c) 2023-2025 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#
"""Merge config files"""

import argparse
import datetime
import os
import shutil
import sys
import time

import configobj

VERSION = '2.0.0'

USAGE = "usage"
DESCRIPTION = "--add, --add-services, --add-stdreport, --server, --template, --config, --secrets"
EPILOG=""

def config_list(arg):
    ''' An argparse user defined type. '''
    return arg.split(',')

def merge_config(self_config, indict):
    """Merge and patch a config file"""

    self_config.merge(indict)
    patch_config(self_config, indict)

def patch_config(self_config, indict):
    """Transfer over parentage and comments."""
    for key in self_config:
        if isinstance(self_config[key], configobj.Section) \
                and key in indict and isinstance(indict[key], configobj.Section):
            self_config[key].parent = self_config
            self_config[key].main = self_config.main
            if not self_config.comments[key]:
                self_config.comments[key] = indict.comments[key]
            if not self_config.inline_comments[key]:
                self_config.inline_comments[key] = indict.inline_comments[key]
            patch_config(self_config[key], indict[key])
        if not self_config.comments[key] and key in indict.comments and indict.comments[key]:
            self_config.comments[key] = indict.comments[key]
        if not self_config.inline_comments[key] and key in indict.inline_comments and indict.inline_comments[key]:
            self_config.inline_comments[key] = indict.inline_comments[key]

def conditional_merge(a_dict, b_dict):
    """Merge fields from b_dict into a_dict, but only if they do not yet
    exist in a_dict"""
    # Go through each key in b_dict
    for k in b_dict:
        if isinstance(b_dict[k], dict):
            if k not in a_dict:
                # It's a new section. Initialize it...
                a_dict[k] = {}
            conditional_merge(a_dict[k], b_dict[k])
        elif k not in a_dict:
            # It's a scalar. Transfer over the value...
            a_dict[k] = b_dict[k]

def get_options():
    """Get the program options."""
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description=DESCRIPTION, epilog=EPILOG)

    parser.add_argument('--version', action='version', version=f'%(prog)s {VERSION}')

    parser.add_argument("--dir", type=str, dest="customizations_dir",
                        default="",
                        help="The directory containing the customizations.")

    parser.add_argument("--template", required=True, type=str, dest="template_config_file",
                        help="The base WeeWX configuration file.")

    parser.add_argument("--add", type=config_list, dest="configs",
                        help="Additional customizations.")

    parser.add_argument("--add-service", type=config_list, dest="services_configs",
                        help="Services customizations.")

    parser.add_argument("--add-stdreport", type=config_list, dest="stdreport_configs",
                        help="StdReport customizations.")

    parser.add_argument("--server", required=True, type=str, dest="server",
                        help=("The server this configuration is for.\n"
                                "test2")
                        )

    parser.add_argument("--secrets", dest="secrets_config_file",
                        help="The secrets file (password, API keys, etc).")

    parser.add_argument("--no-backup", action="store_true", default=False,
                        help="When updating the WeeWX configuration (--conf), do not back it up.")
    parser.add_argument("config_file")

    return parser.parse_args()

if __name__ == '__main__': # pragma: no cover
    def main():
        """ Run it."""
        #print("start")
        service_dir = '/service/'
        stdreport_dir = '/stdreport/'
        server_dir = '/server/'

        options = get_options()

        #customization_config = configobj.ConfigObj({}, indent_type='    ', encoding='utf-8', interpolation=False)

        customization_config = configobj.ConfigObj(options.template_config_file, encoding='utf-8', interpolation=False, file_error=True)

        #conditional_merge(customization_config, template_config)
        #customization_config.initial_comment = template_config.initial_comment
        #patch_config(customization_config, template_config)

        if options.configs:
            for config in options.configs:
                section_file = options.customizations_dir + '/' + config
                section_config = configobj.ConfigObj(section_file, encoding='utf-8', interpolation=False, file_error=True)
                merge_config(customization_config, section_config)

        if options.services_configs:
            for config in options.services_configs:
                section_file = options.customizations_dir + service_dir + config
                section_config = configobj.ConfigObj(section_file, encoding='utf-8', interpolation=False, file_error=True)
                merge_config(customization_config, section_config)

        if options.stdreport_configs:
            for config in options.stdreport_configs:
                section_file = options.customizations_dir + stdreport_dir + config
                section_config = configobj.ConfigObj(section_file, encoding='utf-8', interpolation=False, file_error=True)
                merge_config(customization_config, section_config)

        server_config_dir = options.customizations_dir + server_dir + options.server
        server_config_files = os.listdir(server_config_dir)
        for server_config_file in server_config_files:
            server_config = configobj.ConfigObj(server_config_dir +
                                                '/' +
                                                server_config_file, encoding='utf-8', interpolation=False, file_error=True)
            merge_config(customization_config, server_config)

        if options.secrets_config_file:
            secrets_config = configobj.ConfigObj(options.secrets_config_file, encoding='utf-8', interpolation=False, file_error=True)
            merge_config(customization_config, secrets_config)

        first_key = list(customization_config)[1]
        customization_config.comments[first_key].insert(0,
                                                        f"Built with {' '.join(sys.argv)}")
        customization_config.comments[first_key].insert(0,
                                                        f"Built {options.config_file}")        
        customization_config.comments[first_key].insert(0,
                                                        f"Built on {datetime.date.today()} at {datetime.datetime.now().strftime('%H:%M:%S')}.")
        customization_config.comments[first_key].insert(0, '')

        if not options.no_backup:
            if os.path.exists(options.config_file + ".bkup"):
                shutil.move(options.config_file + ".bkup", options.config_file + time.strftime(".bkup%Y%m%d%H%M%S"))

            if os.path.exists(options.config_file):
                shutil.move(options.config_file, options.config_file + ".bkup")

        customization_config.filename = options.config_file
        customization_config.write()

        #print("done")

    main()
