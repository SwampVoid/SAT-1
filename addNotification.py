import requests

url = "http://127.0.0.1:5001/notifications"

def addNotf():
    new_notification = {
    "type": "Motion",
    "location": "Back Yard",
    "img": "/Icons/backyardPicture.jpg"
    }
    
    response = requests.post(url, json=new_notification)
    
    if response.ok:
        print("Ok")
    else:
        print("Error")
        
