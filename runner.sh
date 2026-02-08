
python3 -m coverage run --omit="**/tests/*,config.py" -m unittest discover
python3 -m coverage html
python3 -m coverage report --fail-under=100

# To view the coverage manually
# python3 -m http.server
