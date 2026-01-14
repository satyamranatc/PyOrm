from Orm import connect, Model, StringField, IntField, ForeignKeyField, session

# 1. Connect to Database
connect(password="satyamrana", database="test")

# 2. Define Models
class User(Model):
    name = StringField(required=True)
    age = IntField(default=18)

class Post(Model):
    title = StringField(required=True)
    author = ForeignKeyField(User)

# 3. Synchronize
User.init_table()
Post.init_table()

# --- 4. VERIFICATION TESTS ---

import time

print("\n--- TEST: Object Identity (Identity Map) ---")
unique_name = f"User_{int(time.time())}"
u_new = User(name=unique_name, age=30).save()

print(f"Created User: {u_new.name} (ID: {u_new.id})")

# 1. Fetch by ID
u_fetch1 = User.find_by_id(u_new.id)
print(f"u_new is u_fetch1: {u_new is u_fetch1}")

# 2. Fetch by query
u_fetch2 = User.find_one(name=unique_name)
print(f"u_new is u_fetch2: {u_new is u_fetch2}")

print("\n--- TEST: Dirty Tracking (Partial Updates) ---")
u_fetch1.age = 35
print(f"Dirty fields (age changed): {u_fetch1._dirty_fields}")
u_fetch1.save()
print(f"Dirty fields after save: {u_fetch1._dirty_fields}")

print("\n--- TEST: Relationships (Lazy Loading) ---")
unique_title = f"Post_{int(time.time())}"
p = Post(title=unique_title, author=u_new).save()
# Check raw ID in dictionary
print(f"Post author ID (from __dict__): {p.__dict__['author']}")

# Fetch post from DB again to test lazy load
p_fetch = Post.find_one(title=unique_title)
print("Accessing author (triggering lazy load)...")
author = p_fetch.author
print(f"Author Name: {author.name} (ID: {author.id})")
print(f"Author is same instance as u_new: {author is u_new}")

print("\nAll Phase 2 tests complete.")