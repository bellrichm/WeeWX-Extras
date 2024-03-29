#! /bin/bash
if [ -z "$1" ]
then
    WEEWX=weewx4
else
    WEEWX=$1
fi

# Note, the value for $WEEWX can be relative. For example ../weewx-source/weewx-3.7.1

echo "Running python $PYENV_VERSION weewx $WEEWX"


PYTHONPATH=bin:../$WEEWX/bin python -m pylint ./bin/user -d duplicate-code
PYTHONPATH=bin:../$WEEWX/bin python -m pylint ./bin/user/tests/*.py -d duplicate-code
