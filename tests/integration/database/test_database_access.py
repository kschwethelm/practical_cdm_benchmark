"""
Integration tests for database access permissions.

Tests that the PostgreSQL account specified in .env has SELECT access
to all tables defined in database/README.md across all schemas:
- cdm_hosp: Hospital data tables
- cdm_note: Clinical notes tables
- cdm_note_extract: Extracted structured data tables
"""

import pytest
from loguru import logger

from cdm.database.connection import db_cursor

# Define all tables by schema as documented in database/README.md
SCHEMA_TABLES = {
    "cdm_hosp": [
        "admissions",
        "patients",
        "diagnoses_icd",
        "procedures_icd",
        "drgcodes",
        "labevents",
        "microbiologyevents",
        "prescriptions",
        "pharmacy",
        "emar",
        "emar_detail",
        "poe",
        "poe_detail",
        "hcpcsevents",
        "services",
        "transfers",
        "omr",
        # Dictionary/Reference tables
        "d_hcpcs",
        "d_icd_diagnoses",
        "d_icd_procedures",
        "d_labitems",
        "provider",
    ],
    "cdm_note": [
        "discharge",
        "discharge_detail",
        "radiology",
        "radiology_detail",
    ],
    "cdm_note_extract": [
        "admissions",
        "discharge_diagnosis",
        "allergies",
        "chief_complaint",
        "procedures",
        "past_medical_history",
        "physical_exam",
        "discharge_free_text",
    ],
}


@pytest.fixture(scope="module")
def all_tables():
    """
    Fixture providing a list of all (schema, table) tuples.

    Returns:
        list[tuple[str, str]]: List of (schema_name, table_name) tuples
    """
    tables = []
    for schema, table_list in SCHEMA_TABLES.items():
        for table in table_list:
            tables.append((schema, table))
    return tables


def test_database_connection():
    """Test that we can establish a database connection using library functions."""
    with db_cursor() as cur:
        cur.execute("SELECT 1")
        result = cur.fetchone()
        assert result == (1,), "Database connection test query failed"


@pytest.mark.parametrize(
    "schema,table",
    [(schema, table) for schema, tables in SCHEMA_TABLES.items() for table in tables],
)
def test_table_access(schema, table):
    """
    Test SELECT access to a specific table.

    Args:
        schema: Database schema name
        table: Table name within the schema

    Raises:
        AssertionError: If SELECT query fails
    """
    with db_cursor() as cur:
        try:
            # Attempt a simple SELECT query to verify read access
            query = f"SELECT 1 FROM {schema}.{table} LIMIT 1"
            logger.debug(f"Testing access to {schema}.{table}")
            cur.execute(query)

            # If table is not empty, verify we got a result
            _ = cur.fetchone()
            # Result can be None (empty table) or (1,) - both are valid
            logger.success(f"Access verified for {schema}.{table}")

        except Exception as e:
            pytest.fail(
                f"Failed to access {schema}.{table}: {e}\n"
                f"Check that the database user has SELECT privileges on this table."
            )


def test_all_schemas_exist():
    """Test that all expected schemas exist in the database."""
    expected_schemas = set(SCHEMA_TABLES.keys())

    with db_cursor() as cur:
        cur.execute("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name IN ('cdm_hosp', 'cdm_note', 'cdm_note_extract')
        """)
        existing_schemas = {row[0] for row in cur.fetchall()}

    missing_schemas = expected_schemas - existing_schemas
    assert not missing_schemas, (
        f"Missing schemas: {missing_schemas}\n"
        f"Expected schemas: {expected_schemas}\n"
        f"Found schemas: {existing_schemas}"
    )


def test_table_row_counts():
    """
    Test that key tables contain data.

    Verifies that primary tables are not empty (according to README.md counts).
    """
    expected_populated_tables = [
        ("cdm_hosp", "admissions", 2333),  # Should have exactly 2,333 rows
        ("cdm_hosp", "patients", 2320),  # Should have 2,320 unique patients
        ("cdm_note", "discharge", 2333),  # One discharge note per admission
    ]

    with db_cursor() as cur:
        for schema, table, expected_count in expected_populated_tables:
            cur.execute(f"SELECT COUNT(*) FROM {schema}.{table}")
            count = cur.fetchone()[0]

            logger.info(f"{schema}.{table}: {count} rows (expected: {expected_count})")

            assert count == expected_count, (
                f"Table {schema}.{table} has {count} rows, expected {expected_count}. "
                f"Database may not be properly loaded or filtered."
            )
