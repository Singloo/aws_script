from .mongo import Mongo
from bson import objectid


class AwsCrediential(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('awsCrediential')
    

    def insert(self,doc):
        res = self.col.insert_one(doc)
    
    def delete_with_id(self,object_id:str):
        self.col.delete_one({
            '_id':objectid(objectid)
        })