# MIGRATION CONFLICT FIX
# Run these commands in order to resolve the migration numbering conflict

# Step 1 - Check current migration state
python manage.py showmigrations scanpipe

# Step 2 - Check for conflicts
python manage.py migrate --check

# Step 3 - If conflict exists, find the latest migration number
# Look at scanpipe/migrations/ folder and note the highest number (e.g. 0085)

# Step 4 - Recreate your migration with the correct number
python manage.py makemigrations scanpipe --name origin_curation_fields

# Step 5 - Apply migrations
python manage.py migrate

# Step 6 - Run tests locally to verify
python manage.py test scanpipe.tests.test_origin_models
python manage.py test scanpipe.tests.test_origin_propagation
python manage.py test scanpipe.tests.test_origin_api
python manage.py test scanpipe.tests.test_curation_models
python manage.py test scanpipe.tests.test_curation_utils
python manage.py test scanpipe.tests.test_curation_schema
python manage.py test scanpipe.tests.test_curation_commands
python manage.py test scanpipe.tests.test_curation_pipelines

# Step 7 - Run all tests together
python manage.py test scanpipe.tests

# Step 8 - Commit with sign-off and push
git add .
git commit -s -m "test: add origin curation and propagation test suite"
git push origin fix/code-genetics-origin-curation
