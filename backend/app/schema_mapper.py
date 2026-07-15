from .analysis import Schema
from .models import SchemaTable, SchemaColumn


def schema_to_tables(schema: Schema) -> list[SchemaTable]:
    return [
        SchemaTable(
            name=table_name,
            columns=[
                SchemaColumn(
                    name=column_name,
                    type=str(column.get("type", "")),
                    isPrimaryKey=bool(column.get("is_primary_key", False)),
                    isIndexed=bool(column.get("is_indexed", False)),
                )
                for column_name, column in columns.items()
            ],
        )
        for table_name, columns in schema.items()
    ]
