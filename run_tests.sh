export PYTHONPATH=$PYTHONPATH:$PWD/src
poetry run pytest "$@"