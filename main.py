from Orm import *

connect(password = "satyamrana",database = "test")

createTable("User",name = "string",age = "int")


def greet(name):
    print(f"Hello {name}")
    print("How are you?")
    print("Hope you are doing well")
    print("------------------------")

# insertOne("User","Satyam",20)
# insertOne("User","Rana",21)
# insertOne("User","Rohit",22)

pre(greet,"User")


insertOne("User","Om",22)
# findAll("User")
# findById("User",1)