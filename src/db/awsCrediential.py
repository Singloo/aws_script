from .mongo import Mongo



class AwsCrediential(Mongo):
    def __init__(self):
        super().__init__()
        self.col = self.get_collection('awsCrediential')
    

