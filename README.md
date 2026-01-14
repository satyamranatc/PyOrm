# PyOrm-SQL

A lightweight, Mongoose-inspired SQL ORM for Python with a focus on developer experience, safety, and modern architectural patterns.

## Features

- **Declarative Schema**: Define models as Python classes.
- **Mongoose-like Queries**: Chainable query builder with double-underscore operators (`age__gt=20`).
- **Identity Map (Session)**: Ensures object uniqueness across queries.
- **Dirty Tracking**: Optimized `UPDATE` queries that only send modified fields.
- **Lazy Loading**: Automatic relationship fetching via `ForeignKeyField`.
- **Connection Pooling**: Built-in support for MySQL connection pooling.

## Installation

```bash
pip install pyorm-sql
```

## Quick Start

```python
from pyorm import connect, Model, StringField, IntField

# 1. Connect
connect(host="localhost", user="root", password="your_password", database="test_db")

# 2. Define
class User(Model):
    name = StringField(required=True)
    age = IntField(default=18)

# 3. Synchronize
User.init_table()

# 4. Use
u = User(name="Satyam", age=25).save()
print(f"Created user with ID: {u.id}")

# Query
user = User.find_one(name="Satyam")
user.age = 26
user.save() # Performs partial update
```

## License

MIT
