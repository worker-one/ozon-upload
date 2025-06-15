import pytest
from your_module import extract_quantity_in_pack  # Replace 'your_module' with the actual module name

@pytest.mark.parametrize("offer_name,expected", [
    ("К-Т Секретные Колесные Гайки 4Шт. С Ключом", 4),
    ("Гайки 10 шт", 10),
    ("Гайки 8 шт. в упаковке", 8),
    ("Гайки 2шт", 2),
    ("Гайки комплект", 1),
    ("Гайки 5х20 6 шт", 6),
    ("Гайки 3ШТ", 3),
    ("4 шт гайки", 4),
])
def test_extract_quantity_in_pack(offer_name, expected):
    assert extract_quantity_in_pack(offer_name) == expected
