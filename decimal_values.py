"""Exact decimal comparisons; numeric text stays intact in files and SQLite."""
from decimal import Decimal
import json
import sqlite3


class ExactDecimal(Decimal):
    def __new__(cls, text):
        instance = super().__new__(cls, text)
        instance.literal = str(text)
        return instance

    def __str__(self):
        return self.literal


def decimal_default(value):
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(type(value).__name__)


def dumps(value, **kwargs):
    return json.dumps(value, default=decimal_default, **kwargs)


def configure(db):
    db.create_collation('DECIMAL_ORDER', lambda a, b: (Decimal(a) > Decimal(b)) - (Decimal(a) < Decimal(b)))
    return db


sqlite3.register_adapter(Decimal, str)
sqlite3.register_adapter(ExactDecimal, str)
