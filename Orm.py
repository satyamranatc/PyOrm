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
    
    

DataTypes = {
            "int": "int",
            "string": "varchar(255)",
            "float": "float",
            "date": "date"
        }   


def createTable(TName,**cols):
    query = f"create table if not exists {TName} ("
    for colName,j in cols.items():
        dType = DataTypes[j]
        query += f"{colName} {dType},"
        
    query = query[:-1]
    query += ");"
    print(query)
    cursor.execute(query)
    con.commit()
    