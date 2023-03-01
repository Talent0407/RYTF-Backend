check-env-file:
	@bash -c " \
		if [ ! -f .env ]; then \
			cp .env.example .env; \
		fi; \
	"

base: check-env-file

# Tasks

# SSH (bash) into server container.
# Useful for running Django shell commands.
bash: base
	docker-compose -f local.yml exec django bash

# SSH (bash) into database container.
# Useful for running commands directly against database.
bashdb: base
	docker-compose -f local.yml exec postgres bash

# SSH (postgres shell) into database container.
# Useful for running postgres commands.
dbshell: base
	docker-compose -f local.yml exec postgres psql -U postgres

# Drop the local database.
cleandb: base
	docker-compose -f local.yml exec postgres psql -h db -U postgres -c "DROP DATABASE IF EXISTS ryft"

# Build docker containers. Pass --no-cache to force re-downloading of images.
# See build --help for additional info
python-build:
	docker-compose -f local.yml build $(ARGS)

# Start docker containers.
# See up --help for additional info
python-start:
	docker-compose -f local.yml up $(ARGS)

# Stop docker containers.
python-stop:
	docker-compose -f local.yml stop

# Remove docker containers (if they exist)
# Run this with --rmi all to remove the mysql image too
python-clean:
	docker-compose -f local.yml down --rmi local

# SSH (bash) into server container.
# Useful for running Django shell commands.
python-shell: base
	docker-compose -f local.yml run --rm django python manage.py shell

# SSH (bash) into server container.
# Useful for running Django shell commands.
python-command: base
	docker-compose -f local.yml run --rm django python manage.py $(ARGS)

# Lint server code automatically with black and autoflake
# WARNING: This updates files in-place.
python-lint: base
	docker-compose -f local.yml exec -T django black ./
	docker-compose -f local.yml exec -T django isort ./
	#docker-compose -f local.yml exec -T django autoflake ./ --exclude venv --in-place --recursive --remove-all-unused-imports --remove-duplicate-keys --remove-unused-variables
	@bash -c "\
		if ! git diff-index --quiet HEAD --; then\
			echo 'Changes made. See git diff';\
			exit 1;\
		fi;\
	"

# Check server code automatically with black and autoflake
# WARNING: This updates files in-place.
python-lint-check: base
	docker-compose -f local.yml run --rm django black ./
	docker-compose -f local.yml run --rm django isort --check-only ./
	@bash -c "\
		if ! git diff-index --quiet HEAD --; then\
			echo 'Changes made. See git diff';\
			exit 1;\
		fi;\
	"

python-flake8-and-manage-py-check: base
	docker-compose -f local.yml run --rm django flake8 ./
	docker-compose -f local.yml run --rm django python manage.py check

# Security vulnerability checks
# Check packages
python-security-check: base
	docker-compose -f local.yml exec -T django python manage.py check --deploy --fail-level ERROR
	# Check files, except tests. See also server/.bandit config
	docker-compose -f local.yml exec -T django bandit -r server

# Run database migrations.
python-makemigrations: base
	docker-compose -f local.yml run --rm django python manage.py makemigrations $(ARGS)

# Migrate database.
python-migrate: base
	docker-compose -f local.yml run --rm django python manage.py migrate $(ARGS)

# Run database migrations.
python-migrations-and-fixtures: base
	docker-compose -f local.yml run --rm django python manage.py migrate
	docker-compose -f local.yml run --rm django python manage.py makemigrations --check

# Run backend tests
python-test: base
	echo "Running tests with cache (use --cache-clear otherwise)..."
	docker-compose -f local.yml run --rm django pytest $(ARGS)

python-coverage: base
	echo "Running coverage of tests"
	docker-compose -f local.yml run --rm django coverage run --omit='*/venv/*' -m pytest

help:
	@echo  ''
	@echo  ' Targets:'
	@echo  ''
	@echo  '  bash           			- SSH (bash) into server container.'
	@echo  '  bashdb                	- SSH (bash) into database container.'
	@echo  '  dbshell    				- SSH (postgres shell) into database container.'
	@echo  '  cleandb      				- Drop the local database.'
	@echo  '  python-build      		- Build docker containers. Pass --no-cache to force re-downloading of images.'
	@echo  '  python-start				- Start docker containers.'
	@echo  '  python-stop     			- Stop docker containers.'
	@echo  '  python-clean    			- Remove docker containers (if they exist)'
	@echo  '  python-shell     			- SSH (bash) into server container.'
	@echo  '  python-install-venv		- Install package, e.g. make python-install-venv ARGS="--dev django_extensions"'
	@echo  '  python-lint				- Lint server code automatically with black and autoflake'
	@echo  '  python-lint-check			- Check server code automatically with black and autoflake'
	@echo  '  python-security-check		- Security vulnerability checks'
	@echo  '  python-makemigrations		- Run database migrations.'
	@echo  '  python-migrate			- Migrate database.'
	@echo  '  python-test				- Run backend tests'
