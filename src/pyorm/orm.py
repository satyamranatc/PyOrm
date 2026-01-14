import mysql.connector
from mysql.connector import pooling
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PyOrm")

class Database:
    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def connect(self, **kwargs):
        try:
            db_config = {
                "host": kwargs.get('host', 'localhost'),
                "user": kwargs.get("user", 'root'),
                "password": kwargs.get('password'),
                "database": kwargs.get('database'),
                "pool_name": "pyorm_pool",
                "pool_size": 5,
            }
            self._pool = pooling.MySQLConnectionPool(**db_config)
            logger.info("Connected to database pool...")
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            raise

    def get_connection(self):
        if not self._pool:
            raise Exception("Database not connected. Call connect() first.")
        return self._pool.get_connection()

    def execute(self, query, params=None, commit=False):
        conn = self.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            if commit:
                conn.commit()
                return cursor.lastrowid
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

class Session:
    def __init__(self):
        self.identity_map = {}

    def get(self, model_cls, pk):
        key = (model_cls, pk)
        return self.identity_map.get(key)

    def add(self, instance):
        if instance.id:
            key = (instance.__class__, instance.id)
            self.identity_map[key] = instance

    def remove(self, instance):
        if instance.id:
            key = (instance.__class__, instance.id)
            if key in self.identity_map:
                del self.identity_map[key]

# Global session for simplicity, similar to a thread-local session in production ORMs
session = Session()

db = Database()

def connect(**kwargs):
    db.connect(**kwargs)

class Field:
    def __init__(self, data_type, required=False, default=None, primary_key=False, auto_increment=False):
        self.data_type = data_type
        self.required = required
        self.default = default
        self.primary_key = primary_key
        self.auto_increment = auto_increment
        self.name = None

    def to_sql(self):
        sql = f"{self.data_type}"
        if self.primary_key:
            sql += " PRIMARY KEY"
        if self.auto_increment:
            sql += " AUTO_INCREMENT"
        if self.required:
            sql += " NOT NULL"
        elif self.default is not None:
            if isinstance(self.default, str):
                sql += f" DEFAULT '{self.default}'"
            else:
                sql += f" DEFAULT {self.default}"
        return sql

class StringField(Field):
    def __init__(self, length=255, **kwargs):
        super().__init__(data_type=f"VARCHAR({length})", **kwargs)

class IntField(Field):
    def __init__(self, **kwargs):
        super().__init__(data_type="INT", **kwargs)

class FloatField(Field):
    def __init__(self, **kwargs):
        super().__init__(data_type="FLOAT", **kwargs)

class DateField(Field):
    def __init__(self, **kwargs):
        super().__init__(data_type="DATE", **kwargs)

class ForeignKeyField(Field):
    def __init__(self, related_model, **kwargs):
        super().__init__(data_type="INT", **kwargs)
        self.related_model = related_model

    def __get__(self, instance, owner):
        if instance is None:
            return self
        
        # The actual ID value stored in this instance
        val = instance.__dict__.get(self.name)
        if val is None:
            return None
        
        # Cache the fetched object on the instance to avoid repeated queries
        cache_name = f"_{self.name}_cache"
        if not hasattr(instance, cache_name):
            related_obj = self.related_model.find_by_id(val)
            setattr(instance, cache_name, related_obj)
        
        return getattr(instance, cache_name)

    def __set__(self, instance, value):
        if isinstance(value, Model):
            if not value.id:
                raise Exception("Cannot set relationship with unsaved model.")
            instance.__dict__[self.name] = value.id
            setattr(instance, f"_{self.name}_cache", value)
        else:
            instance.__dict__[self.name] = value
            if hasattr(instance, f"_{self.name}_cache"):
                delattr(instance, f"_{self.name}_cache")
        
        # Mark as dirty
        if not getattr(instance, '_loading', False):
            instance._dirty_fields.add(self.name)

class ModelMeta(type):
    def __new__(cls, name, bases, attrs):
        if name == "Model":
            return super().__new__(cls, name, bases, attrs)

        fields = {}
        for key, value in attrs.items():
            if isinstance(value, Field):
                value.name = key
                fields[key] = value
        
        attrs['_fields'] = fields
        attrs['_table_name'] = attrs.get('__tablename__', name.lower())
        
        # Ensure id field exists if not defined
        if 'id' not in fields:
            id_field = IntField(primary_key=True, auto_increment=True)
            id_field.name = 'id'
            fields['id'] = id_field
            attrs['id'] = None

        return super().__new__(cls, name, bases, attrs)

class Model(metaclass=ModelMeta):
    def __init__(self, **kwargs):
        self._dirty_fields = set()
        self._loading = True # Flag to avoid marking fields dirty during initial load
        
        for field_name, field in self._fields.items():
            value = kwargs.get(field_name, field.default)
            # Use normal setattr to allow descriptors (like ForeignKeyField) to work
            setattr(self, field_name, value)
        
        self._loading = False
        if self.id:
            session.add(self)

    def __setattr__(self, name, value):
        if name in self._fields and not getattr(self, '_loading', False):
            # Use __dict__.get to avoid triggering descriptors (like ForeignKey lazy load)
            old_value = self.__dict__.get(name)
            if old_value != value:
                self._dirty_fields.add(name)
        super().__setattr__(name, value)

    @classmethod
    def init_table(cls):
        cols = []
        for field in cls._fields.values():
            cols.append(f"{field.name} {field.to_sql()}")
        
        query = f"CREATE TABLE IF NOT EXISTS {cls._table_name} ({', '.join(cols)});"
        db.execute(query, commit=True)
        logger.info(f"Table '{cls._table_name}' synchronized.")

    def save(self):
        if not self.id:
            # Insert - use all fields except auto-incrementing id
            fields = []
            placeholders = []
            values = []
            for field_name, field in self._fields.items():
                if field.auto_increment and getattr(self, field_name) is None:
                    continue
                fields.append(field_name)
                placeholders.append("%s")
                # Use raw ID/value from __dict__ for SQL
                values.append(self.__dict__.get(field_name))
            
            query = f"INSERT INTO {self._table_name} ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
            last_id = db.execute(query, tuple(values), commit=True)
            object.__setattr__(self, 'id', last_id)
            session.add(self)
            self._dirty_fields.clear()
        else:
            # Update - only dirty fields
            if not self._dirty_fields:
                logger.debug(f"No changes to save for {self}")
                return self
            
            update_parts = []
            update_values = []
            for field_name in self._dirty_fields:
                if field_name == 'id': continue
                update_parts.append(f"{field_name} = %s")
                update_values.append(self.__dict__.get(field_name))
            
            update_values.append(self.id)
            query = f"UPDATE {self._table_name} SET {', '.join(update_parts)} WHERE id = %s"
            db.execute(query, tuple(update_values), commit=True)
            self._dirty_fields.clear()
        
        return self

    @classmethod
    def find(cls, **kwargs):
        return QuerySet(cls).where(**kwargs)

    @classmethod
    def find_one(cls, **kwargs):
        return QuerySet(cls).where(**kwargs).limit(1).exec_one()

    @classmethod
    def find_by_id(cls, id):
        # Check Identity Map first
        cached = session.get(cls, id)
        if cached:
            return cached
        return cls.find_one(id=id)

    def delete(self):
        if self.id:
            query = f"DELETE FROM {self._table_name} WHERE id = %s"
            db.execute(query, (self.id,), commit=True)
            session.remove(self)
            object.__setattr__(self, 'id', None)

class QuerySet:
    def __init__(self, model_cls):
        self.model_cls = model_cls
        self._where = {}
        self._sort = None
        self._limit = None
        self._offset = None

    def where(self, **kwargs):
        self._where.update(kwargs)
        return self

    def sort(self, field):
        self._sort = field
        return self

    def limit(self, n):
        self._limit = n
        return self

    def offset(self, n):
        self._offset = n
        return self

    def _build_query(self):
        query = f"SELECT * FROM {self.model_cls._table_name}"
        params = []
        
        if self._where:
            where_clauses = []
            for key, value in self._where.items():
                if "__" in key:
                    field, op = key.split("__")
                    operators = {"gt": ">", "lt": "<", "gte": ">=", "lte": "<=", "contains": "LIKE"}
                    sql_op = operators.get(op, "=")
                    if op == "contains":
                        value = f"%{value}%"
                    where_clauses.append(f"{field} {sql_op} %s")
                else:
                    where_clauses.append(f"{key} = %s")
                params.append(value)
            query += " WHERE " + " AND ".join(where_clauses)
            
        if self._sort:
            order = "ASC"
            field = self._sort
            if field.startswith("-"):
                order = "DESC"
                field = field[1:]
            query += f" ORDER BY {field} {order}"
            
        if self._limit:
            query += f" LIMIT {self._limit}"
            if self._offset:
                query += f" OFFSET {self._offset}"
        
        return query, tuple(params)

    def exec(self):
        query, params = self._build_query()
        results = db.execute(query, params)
        final_results = []
        for row in results:
            pk = row.get('id')
            cached = session.get(self.model_cls, pk)
            if cached:
                # Update cached object with fresh data from DB? 
                # For now, just return the cached one, but don't overwrite dirty fields
                final_results.append(cached)
            else:
                instance = self.model_cls(**row)
                final_results.append(instance)
        return final_results

    def exec_one(self):
        results = self.exec()
        return results[0] if results else None