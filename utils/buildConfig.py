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
        elif not self_config.comments[key] and key in indict.comments and indict.comments[key]:
            self_config.comments[key] = indict.comments[key]

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

if __name__ == '__main__': # pragma: no cover
    USAGE = ""
    def main():
        """ Run it."""
        print("start")
        parser = argparse.ArgumentParser(usage=USAGE)

        parser.add_argument("--template", type=str, dest="template_config_file",
                            help="The base WeeWX configuration file.")
        parser.add_argument("--add", type=config_list, dest="configs",
                            help="Additional customizations.")
        parser.add_argument("--dir", type=str, dest="customizations_dir",
                            default="",
                            help="The directory containing the customizations.")
        parser.add_argument("--config", dest="server_config_file",
                            help="The configuration file for a server.")
        parser.add_argument("--secrets", dest="secrets_config_file",
                            help="The secrets file (password, API keys, etc).")
        parser.add_argument("--no-backup", action="store_true", default=False,
                            help="When updating the WeeWX configuration (--conf), do not back it up.")
        parser.add_argument("config_file")

        options = parser.parse_args()
        if not options.template_config_file:
            print("The base WeeWX configuration file (--template) is required.")
            return 4

        customization_config = configobj.ConfigObj({}, indent_type='    ', encoding='utf-8', interpolation=False)
        template_config = configobj.ConfigObj(options.template_config_file, encoding='utf-8', interpolation=False, file_error=True)

        if options.configs:

            for config in options.configs:
                section_file = options.customizations_dir + '/' + config
                section_config = configobj.ConfigObj(section_file, encoding='utf-8', interpolation=False, file_error=True)
                merge_config(customization_config, section_config)

        # Merging into the customization config provides more control over the order of keys
        # By default any keys only in template_config will be at the end.
        # If the need to be earlier, placeholders can be added to template_config
        conditional_merge(customization_config, template_config)
        customization_config.initial_comment = template_config.initial_comment
        patch_config(customization_config, template_config)

        if options.server_config_file:
            server_config = configobj.ConfigObj(options.server_config_file, encoding='utf-8', interpolation=False, file_error=True)
            merge_config(customization_config, server_config)

        if options.secrets_config_file:
            secrets_config = configobj.ConfigObj(options.secrets_config_file, encoding='utf-8', interpolation=False, file_error=True)
            merge_config(customization_config, secrets_config)

        first_key = list(customization_config)[1]
        customization_config.comments[first_key].insert(0,
                                                        f"Built with {' '.join(sys.argv)}")
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

        print("done")

    main()
