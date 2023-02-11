#!/usr/bin/python

import argparse
import configobj

if __name__ == '__main__': # pragma: no cover
    USAGE = ""
    def main():
        """ Run it."""
        print("start")
        parser = argparse.ArgumentParser(usage=USAGE)
        parser.add_argument("--secrets", required=True, dest="secrets_config_file",
                            help="The secrets file (password, API keys, etc).")
        parser.add_argument("--template", required=True, dest="template_config_file",
                            help="The template file.")
        parser.add_argument("--config", required=True, dest="config_file",
                            help="The WeeWX config file.")

        options = parser.parse_args()

        secrets_config = configobj.ConfigObj(options.secrets_config_file, encoding='utf-8', interpolation=False, file_error=True)
        template_config = configobj.ConfigObj(options.template_config_file, encoding='utf-8', interpolation=False, file_error=True)
        template_config.merge(secrets_config)

        template_config.filename = options.config_file
        template_config.write()

        print("done")

    main()
