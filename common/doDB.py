"""Helper module for MySQL database functions

(doDB.py)
Receives MySQL server parameters, SQL to execute and an optional list 
of dictionary items to execute with MySQL database

Parameters
__________
serverparams : dictionary
    MySQL server parameters (eg. hostname, username, password, database 
    name)
sql : string
    SQL statement to execute, SELECT, UPDATE, INSERT, DELETE, etc
sql_values : list of dictionarys, optional
    items reflecting device parameters to be updated/inserted into
    MySQL; needed with UPDATE and some INSERT statements using 
    execmany(); not needed with SELECT and DELETE type SQL statements 
    using exec() or fetchall()

Returns
-------
int
    row count added/updated/deleted (for exec() and execmany())
list of dictionaries
    results of SQL query (for fetchall())

Examples
--------
serverparams = {
    "host": "mysql-server.local",
    "username": "dba",
    "password": "mysecret",
    "database": "my_database"
}

sql = '''SELECT * FROM table'''
results = fetchall(serverparams, sql)

insertsql = '''INSERT INTO table
(column1, column2, column3)
VALUES (%s, %s)
'''
values = [
    ("Value1", "Value2", 5),
    ("Value3", "Value4", 10)
]
rowcount = execmany(serverparams, insertsql, values)
"""

"""Version log
v1   2023-0725  Initial dev based on insertUpdateMySQL v4 combined
    with SelectFromMySQL
v2   2023-0906  Updated docs and packaging for github
"""

# Credits:
__version__ = '2'
__author__ = 'Jason Davis - jadavis@cisco.com'
__license__ = "Cisco Sample Code License, Version 1.1 - https://developer.cisco.com/site/license/cisco-sample-code-license/"

# Imports
import sys
import MySQLdb

# Global Variables

# Functions
def execmany(serverparams, sql, sql_values):
    """Execute Many statements into MySQL database
    
    Receives server parameters, sql and values to process with database
    
    :param serverparams: dictionary containing settings of the MySQL server [eg. host, database name, username, password,  etc.]
    :param sql: SQL statement to process (SELECT, INSERT, INSERT UPDATE...)
    :param sql_values: list of dictionary entries
    :returns: None
    """
    try:
        db=MySQLdb.connect(host=serverparams["host"],
                           user=serverparams["username"],
                           passwd=serverparams["password"],
                           db=serverparams["database"])
    except MySQLdb.OperationalError as e:
        print("OperationalError")
        print(e)
        sys.exit(f'Check optionsconfig.yaml file for misconfiguration')
    except:
        sys.exit("Unknown error occurred")

    cursor=db.cursor()
    
    try:
        cursor.executemany(sql, sql_values)
    except MySQLdb.DataError as e:
        # DataError: MySQLdb throws this error when there is problem in the data processing, like division by zero, numeric value of of range.
        sys.exit(f'DataError - {str(e)}')
    except MySQLdb.InternalError as e:
        # InternalError: This exception is raised when there is some internal error in MySQL database itself. For e.g invalid cursor, transaction out of sync etc.
        sys.exit(f'InternalError - {str(e)}')
    except MySQLdb.IntegrityError as e:
        # IntegrityError: This exception is raised when foreign key check fails.
        sys.exit(f'IntegrityError - {str(e)}')
    except MySQLdb.OperationalError as e:
        # OperationalError: This exception is raised for things that are not in control of the programmer. For e.g unexpected disconnect, error in memory allocation etc, selected database not exists.
        sys.exit(f'OperationalError - {str(e)}')
    except MySQLdb.NotSupportedError as e:
        # NotSupportedError: This exception is raised when there is method or api that is not supported.
        sys.exit(f'NotSupportedError - {str(e)}')
    except MySQLdb.ProgrammingError as e:
        # ProgrammingError: This exception is raised of programming errors. For e.g table not found, error in mysql syntax, wrong number of parameters specified etc.
        sys.exit(f'ProgrammingError - {str(e)}')
    except:
        sys.exit('Unknown error occurred')
    finally:
        #print(f'Number of database records affected: {str(cursor.rowcount)}')
        db.commit()
        cursor.close()
        db.close()
        return cursor.rowcount


def exec(serverparams, sql):
    """Execute single statement into MySQL database
    
    Receives server parameters, and sql to process with database
    
    :param serverparams: dictionary containing settings of the MySQL server [eg. host, database name, username, password,  etc.]
    :param sql: SQL statement to process (SELECT, INSERT, INSERT UPDATE...)
    :returns: None
    """
    try:
        db=MySQLdb.connect(host=serverparams["host"],
                           user=serverparams["username"],
                           passwd=serverparams["password"],
                           db=serverparams["database"])
    except MySQLdb.OperationalError as e:
        print("OperationalError")
        print(e)
        sys.exit(f'Check optionsconfig.yaml file for misconfiguration')
    except:
        sys.exit("Unknown error occurred")

    cursor=db.cursor()
    
    try:
        cursor.execute(sql)
    except MySQLdb.DataError as e:
        # DataError: MySQLdb throws this error when there is problem in the data processing, like division by zero, numeric value of of range.
        sys.exit(f'DataError - {str(e)}')
    except MySQLdb.InternalError as e:
        # InternalError: This exception is raised when there is some internal error in MySQL database itself. For e.g invalid cursor, transaction out of sync etc.
        sys.exit(f'InternalError - {str(e)}')
    except MySQLdb.IntegrityError as e:
        # IntegrityError: This exception is raised when foreign key check fails.
        sys.exit(f'IntegrityError - {str(e)}')
    except MySQLdb.OperationalError as e:
        # OperationalError: This exception is raised for things that are not in control of the programmer. For e.g unexpected disconnect, error in memory allocation etc, selected database not exists.
        sys.exit(f'OperationalError - {str(e)}')
    except MySQLdb.NotSupportedError as e:
        # NotSupportedError: This exception is raised when there is method or api that is not supported.
        sys.exit(f'NotSupportedError - {str(e)}')
    except MySQLdb.ProgrammingError as e:
        # ProgrammingError: This exception is raised of programming errors. For e.g table not found, error in mysql syntax, wrong number of parameters specified etc.
        sys.exit(f'ProgrammingError - {str(e)}')
    except:
        sys.exit('Unknown error occurred')
    finally:
        #print(f'Number of database records affected: {str(cursor.rowcount)}')
        db.commit()
        cursor.close()
        db.close()
        return cursor.rowcount


def fetchall(serverparams, sql):
    """Execute single SELECT statement and fetch all results from MySQL database
    
    Receives server parameters, and sql to process with database
    
    :param serverparams: dictionary containing settings of the MySQL server [eg. host, database name, username, password,  etc.]
    :param sql: SQL statement to process (SELECT, INSERT, INSERT UPDATE...)
    :returns: SQL query results
    """
    try:
        db=MySQLdb.connect(host=serverparams["host"],
                           user=serverparams["username"],
                           passwd=serverparams["password"],
                           db=serverparams["database"])
    except MySQLdb.OperationalError as e:
        print("OperationalError")
        print(e)
        sys.exit(f'Check optionsconfig.yaml file for misconfiguration')
    except:
        sys.exit("Unknown error occurred")

    cursor=db.cursor()
    
    try:
        cursor.execute(sql)
    except MySQLdb.DataError as e:
        # DataError: MySQLdb throws this error when there is problem in the data processing, like division by zero, numeric value of of range.
        sys.exit(f'DataError - {str(e)}')
    except MySQLdb.InternalError as e:
        # InternalError: This exception is raised when there is some internal error in MySQL database itself. For e.g invalid cursor, transaction out of sync etc.
        sys.exit(f'InternalError - {str(e)}')
    except MySQLdb.IntegrityError as e:
        # IntegrityError: This exception is raised when foreign key check fails.
        sys.exit(f'IntegrityError - {str(e)}')
    except MySQLdb.OperationalError as e:
        # OperationalError: This exception is raised for things that are not in control of the programmer. For e.g unexpected disconnect, error in memory allocation etc, selected database not exists.
        sys.exit(f'OperationalError - {str(e)}')
    except MySQLdb.NotSupportedError as e:
        # NotSupportedError: This exception is raised when there is method or api that is not supported.
        sys.exit(f'NotSupportedError - {str(e)}')
    except MySQLdb.ProgrammingError as e:
        # ProgrammingError: This exception is raised of programming errors. For e.g table not found, error in mysql syntax, wrong number of parameters specified etc.
        sys.exit(f'ProgrammingError - {str(e)}')
    except:
        sys.exit('Unknown error occurred')
    finally:
        #print(f'Number of database records affected: {str(cursor.rowcount)}')
        results = cursor.fetchall()
        cursor.close()
        db.close()
        return results
