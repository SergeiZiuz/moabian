import socket
import sqlite3
from sqlite3 import Error

from azure.data.tables import TableServiceClient, UpdateMode
from azure.core.exceptions import ResourceExistsError

def getHostIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('1.1.1.1', 1))
    local_ip = s.getsockname()[0]
    return local_ip

class Ball:
    __moab_local_ip = None
    __local_ip = None
    __product = None
    __status_of_ball = None
    __ball = None

    def __init__(self) -> None:
        self.__local_ip = getHostIP()
        self.__moab_local_ip = str(self.__local_ip).replace(".", "")
        self.__product = u'ball detect'
        self.__status_of_ball = False
        self.__ball = {
            u'PartitionKey': self.__moab_local_ip,
            u'RowKey': self.__product,
            u'IP': self.__local_ip,
            u'STATUS': self.__status_of_ball
        }

    def getEntity(self, status_of_ball):
        self.__ball["STATUS"] = status_of_ball
        return self.__ball

class Send:
    __connection_string = None
    __table_service_client = None
    __table_name = None

    def __init__(self) -> None:
        self.__table_name = "BALL"
        self.__connection_string = ""
        self.__table_service_client = TableServiceClient.from_connection_string(conn_str=self.__connection_string).get_table_client(table_name=self.__table_name)
        self.createRow({
            u'PartitionKey': str(getHostIP()).replace(".", ""),
            u'RowKey': u'ball detect',
            u'IP': getHostIP(),
            u'STATUS': False
        })
    
    def sendStatusOfBall(self, ball):
        try:
            self.__table_service_client.update_entity(mode=UpdateMode.MERGE, entity=ball)
        except ResourceExistsError as e:
            print (e)
    
    def createRow(self, ball):
        try:
            entity = self.__table_service_client.create_entity(entity=ball)
        except ResourceExistsError as e:
            print("Moab is registreted at Azure table")

