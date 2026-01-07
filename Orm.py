import mysql.connector

con = ""
cursor = ""

def connect(**args):
    global con
    global cursor
    host = args.get('host','localhost')
    user = args.get("user",'root')
    password = args.get('password')
    database = args.get('database')
    try:
        con = mysql.connector.connect(
       host = host,
       user = user,
       password = password,
       db = database
    )
        print("Connected to database...")
        cursor = con.cursor()
    except Exception as e:
        print("Connection failed...",e)
    

preTableName = ""
fun = ""
def pre(func,tableName):
    global preTableName
    global fun
    
    preTableName = tableName
    fun = func
    
    
    

DataTypes = {
            "int": "int",
            "string": "varchar(255)",
            "float": "float",
            "date": "date"
        }   

ColNames = ()
def createTable(TName,**cols):
    global ColNames
    query = f"create table if not exists {TName} ( id int primary key auto_increment," 
    for colName,j in cols.items():
       if colName == "id" or colName == "Id":
           continue
       dType = DataTypes[j]
       query += f"{colName} {dType},"
       ColNames += (colName,)
        
    query = query[:-1]
    query += ");"
    try:
        cursor.execute(query)
        con.commit()
        print("Table created successfully...")
    except Exception as e:
        print("Table creation failed...",e)
    
    

def insertOne(TName,*values):    
    query = f"insert into {TName} ({','.join(ColNames)}) values {values};"
    if preTableName == TName:
        fun(values[0])
    try:
        cursor.execute(query)
        con.commit()
        print("Record inserted successfully...")
    except Exception as e:
        print("Record insertion failed...",e)

    
def findAll(TName):
    query = f"select * from {TName}"
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        for row in result:
            print(row)
    except Exception as e:
        print("Query failed...",e)
    
def findById(TName,id):
    query = f"select * from {TName} where id = {id}"
    try:
        cursor.execute(query)
        result = cursor.fetchall()
        for row in result:
            print(row)
    except Exception as e:
        print("Query failed...",e)