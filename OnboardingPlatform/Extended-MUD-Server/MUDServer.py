
from flask import Flask, request, abort, send_file
from dotenv import load_dotenv
import json
import sys
import os

# Load environment variables from .env file
load_dotenv()

# Import shared authentication
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
shared_auth_path = os.path.join(parent_dir, 'shared_auth')
sys.path.insert(0, shared_auth_path)
from decorators import require_auth

app = Flask(__name__)

@app.route('/list',methods = ['GET'])
@require_auth
def getList(current_user):
    lst = os.listdir('./files')
    ret = []
    print(lst)
    for i in lst:
        if ".json" in i:
            ret.append(i.replace(".json",""))
    print(ret)
    print(json.dumps(ret))
    return json.dumps(ret)

@app.route('/<hash>', methods = ['GET'])
@require_auth
def getThreatMudFile(hash, current_user):
    print("hash ", hash)
    splited = hash.split(".")
    if len(splited) == 1:
        try:
            file = open("./files/{}.json".format(hash))
            threat_mud_file = json.load(file)
            return json.dumps(threat_mud_file)
        except:
            #return "No Threat-MUD File related to threat {}".format(hash)
            abort(404)
    #check extension correcta***
    elif splited[1] == "p7s":
        try:
            return send_file("./files/{}".format(hash))
        except:
            #return "No Threat-MUD Signature related to threat {}".format(hash)
            abort(404)
    else:
        abort(404)

@app.route("/signature", methods = ['GET'])
@require_auth
def getSignature(current_user):
    return "signature"

if __name__ == "__main__":
    #app.run(debug=True, port=5050)
    app.run(debug=True, host="0.0.0.0", port=8091)
