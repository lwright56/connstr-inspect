# connstr

A command line tool for parsing database connection strings and showing
their parts: host, port, database, user, and so on, without pasting the
whole string somewhere just to eyeball whether the port is right.

It handles the two shapes that show up in practice:

- URL style, e.g. `postgres://user:pass@host:5432/dbname?sslmode=require`
- keyword/value style, e.g. `Server=tcp:host,1433;Database=db;User ID=user;Password=pass;`
  (the ADO.NET / ODBC form used by SQL Server and some MySQL drivers)

Passwords are redacted by default in both output modes, because connection
strings get pasted into terminals, issue trackers, and Slack more often than
anyone would like.

## Usage

```
$ connstr "postgres://appuser:s3cret@db.internal:5432/billing?sslmode=require"
format:   url
scheme:   postgres
user:     appuser
password: ********
host:     db.internal
port:     5432
database: billing
params:
  sslmode: require
```

Show the password instead of redacting it:

```
$ connstr --reveal "postgres://appuser:s3cret@db.internal:5432/billing"
...
password: s3cret
...
```

JSON output, for piping into `jq` or another tool:

```
$ connstr --json "postgres://appuser:s3cret@db.internal:5432/billing"
{
  "format": "url",
  "scheme": "postgres",
  "user": "appuser",
  "password": "********",
  "host": "db.internal",
  "port": 5432,
  "database": "billing",
  "params": {}
}
```

Keyword-style strings work the same way:

```
$ connstr --json "Server=tcp:sql.internal,1433;Database=billing;User ID=svc;Password=s3cret;Encrypt=true;"
{
  "format": "keyword",
  "scheme": null,
  "user": "svc",
  "password": "********",
  "host": "sql.internal",
  "port": 1433,
  "database": "billing",
  "params": {
    "encrypt": "true"
  }
}
```

If you don't pass the string as an argument, `connstr` reads it from stdin,
which is handy for piping from a secrets manager without it ever showing up
in your shell history.

## Install

No package is published yet. Clone the repo and run it in place:

```
$ python -m connstr.cli "postgres://user:pass@localhost/db"
```

## Requirements

Python 3.9+. No third-party dependencies.

## Tests

```
$ python -m unittest discover
```
