import unittest

from connstr.parser import REDACTED, parse


class UrlFormatTests(unittest.TestCase):
    def test_full_url(self):
        info = parse("postgres://appuser:s3cret@db.internal:5432/billing?sslmode=require")
        self.assertEqual(info.format, "url")
        self.assertEqual(info.scheme, "postgres")
        self.assertEqual(info.user, "appuser")
        self.assertEqual(info.password, "s3cret")
        self.assertEqual(info.host, "db.internal")
        self.assertEqual(info.port, 5432)
        self.assertEqual(info.database, "billing")
        self.assertEqual(info.params, {"sslmode": "require"})

    def test_url_without_password(self):
        info = parse("mysql://appuser@db.internal/billing")
        self.assertEqual(info.user, "appuser")
        self.assertIsNone(info.password)

    def test_url_without_credentials(self):
        info = parse("mysql://db.internal:3306/billing")
        self.assertIsNone(info.user)
        self.assertIsNone(info.password)
        self.assertEqual(info.port, 3306)

    def test_url_without_port(self):
        info = parse("postgres://user:pass@db.internal/billing")
        self.assertIsNone(info.port)

    def test_url_root_path_has_no_database(self):
        info = parse("postgres://user:pass@db.internal/")
        self.assertIsNone(info.database)

    def test_url_without_path_has_no_database(self):
        info = parse("postgres://user:pass@db.internal")
        self.assertIsNone(info.database)

    def test_url_decodes_percent_encoded_credentials(self):
        info = parse("postgres://us%40er:p%40ss@db.internal/billing")
        self.assertEqual(info.user, "us@er")
        self.assertEqual(info.password, "p@ss")

    def test_url_repeated_query_param_keeps_last_value(self):
        info = parse("postgres://db.internal/billing?opt=one&opt=two")
        self.assertEqual(info.params, {"opt": "two"})

    def test_url_query_param_with_blank_value(self):
        info = parse("postgres://db.internal/billing?sslmode=")
        self.assertEqual(info.params, {"sslmode": ""})


class KeywordFormatTests(unittest.TestCase):
    def test_basic_keyword_string(self):
        info = parse("Server=sql.internal;Database=billing;User ID=svc;Password=s3cret;")
        self.assertEqual(info.format, "keyword")
        self.assertEqual(info.host, "sql.internal")
        self.assertEqual(info.database, "billing")
        self.assertEqual(info.user, "svc")
        self.assertEqual(info.password, "s3cret")

    def test_keys_are_case_insensitive(self):
        info = parse("SERVER=sql.internal;DATABASE=billing;user id=svc;PASSWORD=s3cret;")
        self.assertEqual(info.host, "sql.internal")
        self.assertEqual(info.database, "billing")
        self.assertEqual(info.user, "svc")
        self.assertEqual(info.password, "s3cret")

    def test_sql_server_tcp_prefixed_host_with_port(self):
        info = parse("Server=tcp:sql.internal,1433;Database=billing;")
        self.assertEqual(info.host, "sql.internal")
        self.assertEqual(info.port, 1433)

    def test_host_with_port_but_no_tcp_prefix(self):
        info = parse("Server=sql.internal,1433;Database=billing;")
        self.assertEqual(info.host, "sql.internal")
        self.assertEqual(info.port, 1433)

    def test_explicit_port_key(self):
        info = parse("Server=sql.internal;Port=5433;Database=billing;")
        self.assertEqual(info.port, 5433)

    def test_non_numeric_port_falls_back_to_params(self):
        info = parse("Server=sql.internal;Port=auto;Database=billing;")
        self.assertIsNone(info.port)
        self.assertEqual(info.params.get("port"), "auto")

    def test_unrecognized_keys_land_in_params(self):
        info = parse("Server=sql.internal;Database=billing;Encrypt=true;")
        self.assertEqual(info.params, {"encrypt": "true"})

    def test_blank_segments_and_missing_equals_are_ignored(self):
        info = parse("Server=sql.internal;;Database=billing; ;Encrypt")
        self.assertEqual(info.host, "sql.internal")
        self.assertEqual(info.database, "billing")
        self.assertNotIn("encrypt", info.params)

    def test_empty_value_becomes_none(self):
        info = parse("Server=sql.internal;Password=;Database=billing;")
        self.assertIsNone(info.password)

    def test_data_source_alias_for_host(self):
        info = parse("Data Source=sql.internal;Initial Catalog=billing;Uid=svc;Pwd=s3cret;")
        self.assertEqual(info.host, "sql.internal")
        self.assertEqual(info.database, "billing")
        self.assertEqual(info.user, "svc")
        self.assertEqual(info.password, "s3cret")


class JdbcFormatTests(unittest.TestCase):
    def test_jdbc_postgresql_url_style(self):
        info = parse("jdbc:postgresql://appuser:s3cret@db.internal:5432/billing?ssl=true")
        self.assertEqual(info.format, "jdbc")
        self.assertEqual(info.scheme, "postgresql")
        self.assertEqual(info.user, "appuser")
        self.assertEqual(info.password, "s3cret")
        self.assertEqual(info.host, "db.internal")
        self.assertEqual(info.port, 5432)
        self.assertEqual(info.database, "billing")
        self.assertEqual(info.params, {"ssl": "true"})

    def test_jdbc_mysql_url_style_without_credentials(self):
        info = parse("jdbc:mysql://db.internal:3306/billing")
        self.assertIsNone(info.user)
        self.assertIsNone(info.password)
        self.assertEqual(info.host, "db.internal")
        self.assertEqual(info.port, 3306)
        self.assertEqual(info.database, "billing")

    def test_jdbc_sqlserver_semicolon_properties(self):
        info = parse(
            "jdbc:sqlserver://sql.internal:1433;databaseName=billing;user=svc;password=s3cret;encrypt=true"
        )
        self.assertEqual(info.format, "jdbc")
        self.assertEqual(info.scheme, "sqlserver")
        self.assertEqual(info.host, "sql.internal")
        self.assertEqual(info.port, 1433)
        self.assertEqual(info.database, "billing")
        self.assertEqual(info.user, "svc")
        self.assertEqual(info.password, "s3cret")
        self.assertEqual(info.params, {"encrypt": "true"})

    def test_jdbc_sqlserver_without_explicit_port(self):
        info = parse("jdbc:sqlserver://sql.internal;databaseName=billing")
        self.assertEqual(info.host, "sql.internal")
        self.assertIsNone(info.port)
        self.assertEqual(info.database, "billing")

    def test_jdbc_without_authority_keeps_driver_name_only(self):
        info = parse("jdbc:h2:mem:testdb")
        self.assertEqual(info.format, "jdbc")
        self.assertEqual(info.scheme, "h2")
        self.assertIsNone(info.host)
        self.assertIsNone(info.database)

    def test_jdbc_password_is_redacted_by_default(self):
        info = parse("jdbc:postgresql://user:s3cret@db.internal/billing")
        self.assertEqual(info.to_dict()["password"], REDACTED)


class RedactionTests(unittest.TestCase):
    def test_password_redacted_by_default(self):
        info = parse("postgres://user:s3cret@db.internal/billing")
        self.assertEqual(info.to_dict()["password"], REDACTED)

    def test_password_revealed_when_requested(self):
        info = parse("postgres://user:s3cret@db.internal/billing")
        self.assertEqual(info.to_dict(reveal=True)["password"], "s3cret")

    def test_missing_password_is_not_redacted(self):
        info = parse("postgres://user@db.internal/billing")
        self.assertIsNone(info.to_dict()["password"])


if __name__ == "__main__":
    unittest.main()
