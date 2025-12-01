"""Unit tests for prompts/utils.py - Pydantic model to prompt conversion."""

from enum import Enum
from typing import Literal

import pytest
from pydantic import BaseModel, Field

from cdm.prompts.utils import pydantic_to_prompt


class TestPydanticToPrompt:
    """Test suite for pydantic_to_prompt function."""

    @pytest.fixture
    def simple_model(self):
        """Create a simple Pydantic model with basic field types."""

        class Person(BaseModel):
            name: str
            age: int
            email: str | None = None

        return Person

    @pytest.fixture
    def model_with_descriptions(self):
        """Create a Pydantic model with field descriptions."""

        class Patient(BaseModel):
            name: str = Field(description="Patient's full name")
            age: int = Field(description="Patient's age in years")
            diagnosis: str = Field(description="Primary diagnosis")

        return Patient

    @pytest.fixture
    def model_with_enum(self):
        """Create a Pydantic model with enum fields."""

        class AnimalType(str, Enum):
            CAT = "Cat"
            DOG = "Dog"
            BIRD = "Bird"

        class Pet(BaseModel):
            name: str
            animal_type: AnimalType

        return Pet

    @pytest.fixture
    def model_with_literal(self):
        """Create a Pydantic model with Literal type."""

        class Medication(BaseModel):
            name: str
            type: Literal["Medication"]
            dosage: str

        return Medication

    @pytest.fixture
    def model_with_list(self):
        """Create a Pydantic model with list fields."""

        class Prescription(BaseModel):
            medications: list[str]
            dosages: list[int]

        return Prescription

    @pytest.fixture
    def nested_model(self):
        """Create Pydantic models with nested submodels."""

        class Address(BaseModel):
            street: str
            city: str
            zipcode: str

        class Person(BaseModel):
            name: str
            age: int
            address: Address

        return Person

    @pytest.fixture
    def model_with_list_of_submodels(self):
        """Create a Pydantic model with list of nested submodels."""

        class Medication(BaseModel):
            name: str
            dosage: str

        class Prescription(BaseModel):
            patient_name: str
            medications: list[Medication]

        return Prescription

    @pytest.fixture
    def model_with_id_field(self):
        """Create a Pydantic model with an 'id' field."""

        class Record(BaseModel):
            id: int
            name: str
            description: str

        return Record

    @pytest.fixture
    def model_with_optional_types(self):
        """Create a Pydantic model with optional/union types."""

        class Patient(BaseModel):
            name: str
            age: int | None
            diagnosis: str | None = None

        return Patient

    # Ground truth outputs for each model
    @pytest.fixture
    def simple_model_expected(self):
        """Expected output for simple_model with default parameters."""
        return """{
  name: str,
  age: int,
  email: str or null
}"""

    @pytest.fixture
    def model_with_descriptions_expected(self):
        """Expected output for model_with_descriptions with default parameters."""
        return """{
  // Patient's full name
  name: str,
  // Patient's age in years
  age: int,
  // Primary diagnosis
  diagnosis: str
}"""

    @pytest.fixture
    def model_with_enum_expected(self):
        """Expected output for model_with_enum with default parameters."""
        return """{
  name: str,
  animal_type: 'CAT' or 'DOG' or 'BIRD'
}"""

    @pytest.fixture
    def model_with_literal_expected(self):
        """Expected output for model_with_literal with default parameters."""
        return """{
  name: str,
  type: 'Medication',
  dosage: str
}"""

    @pytest.fixture
    def model_with_list_expected(self):
        """Expected output for model_with_list with default parameters."""
        return """{
  medications: list[str],
  dosages: list[int]
}"""

    @pytest.fixture
    def nested_model_expected(self):
        """Expected output for nested_model with default parameters."""
        return """{
  name: str,
  age: int,
  address: Address
}
**JSON Subtypes:**
Address: {
  street: str,
  city: str,
  zipcode: str
}"""

    @pytest.fixture
    def model_with_list_of_submodels_expected(self):
        """Expected output for model_with_list_of_submodels with default parameters."""
        return """{
  patient_name: str,
  medications: list[Medication]
}
**JSON Subtypes:**
Medication: {
  name: str,
  dosage: str
}"""

    @pytest.fixture
    def model_with_id_field_expected(self):
        """Expected output for model_with_id_field with exclude_id=True (default)."""
        return """{
  name: str,
  description: str
}"""

    @pytest.fixture
    def model_with_id_field_expected_with_id(self):
        """Expected output for model_with_id_field with exclude_id=False."""
        return """{
  id: int,
  name: str,
  description: str
}"""

    @pytest.fixture
    def model_with_optional_types_expected(self):
        """Expected output for model_with_optional_types with default parameters."""
        return """{
  name: str,
  age: int or null,
  diagnosis: str or null
}"""

    # Test methods
    def test_simple_model_default_params(self, simple_model, simple_model_expected):
        """Test pydantic_to_prompt with a simple model using default parameters."""
        result = pydantic_to_prompt(simple_model)
        assert result == simple_model_expected

    def test_model_with_descriptions(
        self, model_with_descriptions, model_with_descriptions_expected
    ):
        """Test that field descriptions are correctly formatted as comments."""
        result = pydantic_to_prompt(model_with_descriptions)
        assert result == model_with_descriptions_expected

    def test_model_with_enum(self, model_with_enum, model_with_enum_expected):
        """Test that enum fields are formatted with 'or' separated quoted values."""
        result = pydantic_to_prompt(model_with_enum)
        assert result == model_with_enum_expected

    def test_model_with_literal(self, model_with_literal, model_with_literal_expected):
        """Test that Literal types are formatted as quoted strings."""
        result = pydantic_to_prompt(model_with_literal)
        assert result == model_with_literal_expected

    def test_model_with_list(self, model_with_list, model_with_list_expected):
        """Test that list fields are formatted as list[type]."""
        result = pydantic_to_prompt(model_with_list)
        assert result == model_with_list_expected

    def test_nested_model(self, nested_model, nested_model_expected):
        """Test that nested models include JSON Subtypes section."""
        result = pydantic_to_prompt(nested_model)
        assert result == nested_model_expected

    def test_model_with_list_of_submodels(
        self, model_with_list_of_submodels, model_with_list_of_submodels_expected
    ):
        """Test that list of submodels includes JSON Subtypes section."""
        result = pydantic_to_prompt(model_with_list_of_submodels)
        assert result == model_with_list_of_submodels_expected

    def test_model_with_optional_types(
        self, model_with_optional_types, model_with_optional_types_expected
    ):
        """Test that optional/union types are formatted with 'or null'."""
        result = pydantic_to_prompt(model_with_optional_types)
        assert result == model_with_optional_types_expected

    def test_exclude_id_true(self, model_with_id_field, model_with_id_field_expected):
        """Test that id field is excluded when exclude_id=True (default)."""
        result = pydantic_to_prompt(model_with_id_field, exclude_id=True)
        assert result == model_with_id_field_expected

    def test_exclude_id_false(self, model_with_id_field, model_with_id_field_expected_with_id):
        """Test that id field is included when exclude_id=False."""
        result = pydantic_to_prompt(model_with_id_field, exclude_id=False)
        assert result == model_with_id_field_expected_with_id

    def test_add_curls_false(self, simple_model):
        """Test that curly braces are omitted when add_curls=False."""
        result = pydantic_to_prompt(simple_model, add_curls=False)
        expected = """  name: str,
  age: int,
  email: str or null"""
        assert result == expected

    def test_add_comma_false(self, simple_model):
        """Test that commas are omitted when add_comma=False."""
        result = pydantic_to_prompt(simple_model, add_comma=False)
        expected = """{
  name: str
  age: int
  email: str or null
}"""
        assert result == expected

    def test_all_params_custom(self, model_with_id_field):
        """Test with all custom parameters: exclude_id=False, add_curls=False, add_comma=False."""
        result = pydantic_to_prompt(
            model_with_id_field, exclude_id=False, add_curls=False, add_comma=False
        )
        expected = """  id: int
  name: str
  description: str"""
        assert result == expected
