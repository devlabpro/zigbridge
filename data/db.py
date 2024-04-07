import sqlite3,os

try:
    connection = sqlite3.connect("/config/database.db")
except:
    print("База данных не найдена, создаем новую")
    connection = sqlite3.connect("/config/database.db")

def create_database():
    init_request = """
    CREATE TABLE IF NOT EXISTS records(
    cluster_id INTEGER NOT NULL UNIQUE,
    device_id TEXT UNIQUE,
    status INTEGER DEFAULT 0,
    enabled INTEGER DEFAULT 0
    )
    """
    
    cursor = connection.cursor()
    cursor.execute(init_request)
    connection.commit()
    cursor.close()

def init():
    try:
        connection.cursor().execute("SELECT * FROM records LIMIT 1").close()
    except:
        create_database()

def get_devices():
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM records")
    data = cursor.fetchall()
    cursor.close()
    result = []
    for i in data:
        result.append({
            'cluster_id':i[0],
            'ha_device':i[1],
            'status':False if i[2] == 0 else True,
            'enabled':False if i[3] == 0 else True
        })
    return result

def delete_device(cluster_id):
    cursor = connection.cursor()
    cursor.execute("DELETE FROM records WHERE cluster_id={}".format(cluster_id))
    connection.commit()
    cursor.close()

def change_device(data):
    print(data)
    cursor = connection.cursor()
    print("UPDATE records(device_id,status,enabled) SET device_id='{}',status={},enabled={} WHERE cluster_id={}".format(data['ha_device'],1 if data['status'] else 0,1 if data['enabled'] else 0,data['cluster_id']))
    cursor.execute("UPDATE records SET device_id='{}',status={},enabled={} WHERE cluster_id={}".format(data['ha_device'],1 if data['status'] else 0,1 if data['enabled'] else 0,data['cluster_id']))
    connection.commit()
    cursor.close()

def add_device(data):
    cursor = connection.cursor()
    print("INSERT INTO records(cluster_id,device_id,status,enabled) VALUES ({},'{}',0,1)".format(data['cluster_id'],data['ha_device']))
    cursor.execute("INSERT INTO records(cluster_id,device_id,status,enabled) VALUES ({},'{}',0,1)".format(data['cluster_id'],data['ha_device']))
    connection.commit()
    cursor.close()
    return True
