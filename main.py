import hashlib,bisect

class StorageNode:
    def __init__(self, name, host):
        self.name = name
        self.host = host
    def add_node(self, node:StorageNode):
        if len(self._keys) == total_slots:
            raise Exception("Hash space is full")
        
        key = hash_fn(node.host)
        
        idx = bisect(self._keys, key)
        
storage_nodes = [
    StorageNode(name='A', host='10.131.213.12'),
    StorageNode(name='B', host='10.131.217.11'),
    StorageNode(name='C', host='10.131.142.46'),
    StorageNode(name='D', host='10.131.114.17'),
    StorageNode(name='E', host='10.131.189.18'),    
]


def hash_fn(key,total_slots):
    hsh = hashlib.sha256() 
    hsh.update(bytes(key.encode('utf-8')))
    
    return int(hsh.hexdigest(),16) % total_slots
    
    # return sum(bytearray(key.encode('utf-8')))%7

def upload(path):
    index = hash_fn(path)
    node = storage_nodes[index]
    
    return node.put_file(path)

def fetch(path):
    index = hash_fn(path)
    node = storage_nodes[index]
    
    return node.fetch_file(path)

if __name__ == "__main__":
    files = ["f1.txt","f2.txt","f3.txt","f4.txt","f5.txt"]
    for file in files:
        print(hash_fn(file))