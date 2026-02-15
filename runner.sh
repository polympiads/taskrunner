
python3 manage.py makemigrations
python3 manage.py migrate

python3 -m coverage run --omit="**/tests/*,manage.py,taskrunner/telemetry.py,taskrunner/celery.py" manage.py test --verbosity 2
python3 -m coverage html
python3 -m coverage report --fail-under=100

# To view the coverage manually
# python3 -m http.server
