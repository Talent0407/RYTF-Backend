# Ryft

Backend API for Ryft

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

## Settings

Moved to [settings](http://cookiecutter-django.readthedocs.io/en/latest/settings.html).

## Basic Commands

### Setting Up Your Users

-   To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

-   To create a **superuser account**, use this command:

        $ python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### Type checks

Running type checks with mypy:

    $ mypy ryft

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    $ coverage run -m pytest
    $ coverage html
    $ open htmlcov/index.html

#### Running tests with pytest

    $ pytest

### Live reloading and Sass CSS compilation

Moved to [Live reloading and SASS compilation](https://cookiecutter-django.readthedocs.io/en/latest/developing-locally.html#sass-compilation-live-reloading).

### Celery

This app comes with Celery.

To run a celery worker:

``` bash
cd ryft
celery -A config.celery_app worker -l info
```

Please note: For Celery's import magic to work, it is important *where* the celery commands are run. If you are in the same folder with *manage.py*, you should be right.

### Sentry

Sentry is an error logging aggregator service. You can sign up for a free account at <https://sentry.io/signup/?code=cookiecutter> or download and host it yourself.
The system is set up with reasonable defaults, including 404 logging and integration with the WSGI application.

You must set the DSN url in production.

## Deployment

The following details how to deploy this application.

### Docker

See detailed [cookiecutter-django Docker documentation](http://cookiecutter-django.readthedocs.io/en/latest/deployment-with-docker.html).

### Postgres Backups

We're using the dbbackup package and running a cronjob every hour to backup the database directly to our S3 bucket.

To restore a database locally:

1. Download the psql bin file from the S3 storage
2. Create the new database with `createdb ryft_postgres_production --owner=ryft_postgres_production_user` **You must give it the same name as the old database. The user credentials must also be the same as the production user credentials**
3. Grant postgres group to user: `GRANT postgres TO ryft_postgres_production_user;`
4. Run the `python manage.py migrate` command
5. Run the restore command `python manage.py dbrestore -i default-crn...psql.bin`

### 502 Errors

Too many DB connections could be causing it. Links for research:

[Too Many Connections](https://stackoverflow.com/questions/14592729/django-mysql-too-many-connections)
[How to close idle connections](https://stackoverflow.com/questions/12391174/how-to-close-idle-connections-in-postgresql-automatically)
[Idle session timeout](https://www.postgresql.org/docs/14/runtime-config-client.html#GUC-IDLE-SESSION-TIMEOUT)
[Working with idle session timeout](https://www.depesz.com/2021/01/12/waiting-for-postgresql-14-add-idle_session_timeout/)
[How to kill a postgres session connection](https://stackoverflow.com/questions/5108876/kill-a-postgresql-session-connection)
[Querying hanging in ClientRead and blocking](https://dba.stackexchange.com/questions/251937/query-hanging-in-clientread-and-blocking-all-others)
[Debugging a hanging session-lock](https://dba.stackexchange.com/questions/248484/debugging-a-hanging-session-lock)

### SQL Commands

```sql
select max_conn,used,res_for_super,max_conn-used-res_for_super res_for_normal
from
  (select count(*) used from pg_stat_activity) t1,
  (select setting::int res_for_super from pg_settings where name=$$superuser_reserved_connections$$) t2,
  (select setting::int max_conn from pg_settings where name=$$max_connections$$) t3;

SELECT * FROM pg_stat_activity;

select * from pg_settings where name = 'idle_session_timeout';

update pg_settings
SET setting = 10000
WHERE name = 'idle_session_timeout';

select pg_reload_conf();
```

### Celery Tasks and API calls

Basically, most of the wallet data is fetched from Alchemy, and most of the
collection data is fetched from Mnemomic with some from NFTPort

- 12AM: Fetch RYFT NFT owners (Alchemy) (1 per day)
- 12AM: Fetch Collection Metrics (NFTPort) (1 per contract)
- 3AM: Fetch Collection Transfers (Mnemonic) (1 per contract)
- 4AM: Fetch Trending Collections (Mnemonic) (3)
- 5AM: Fetch Collection Price History (Mnemonic) (1 per contract)
- 6AM: Fetch Collection Owners History (Mnemonic) (1 per contract)

#### NFTPort

- Limit of 150000 per month

1 API call per contract per day = 1500 per day = 45000 per month

#### Mnemonic

- Limit of 500000 per month

3 API calls per contract per day = 4500 per day = 135000 per month
1 API call per wallet per 500 NFTs * 2000 wallets with average
of 1000 NFTs = 4000 API calls per month
1 API call per wallet to fetch ENS domain = 1000 API calls

#### Alchemy

- Limit of 300 CUPS per second

Fetch RYFT contract owners every day = 1 per day
Fetch Collection NFTs (once off) = 100 API calls per collection (avg)
Fetch Wallet Transfers = 1000 transfers per API call = avg 3 API calls per wallet
