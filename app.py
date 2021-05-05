import os
import json
import re
from datetime import datetime, timezone, date
from pymongo import MongoClient
from flask import Flask, request, jsonify, render_template
from flask_cors import cross_origin
# from run_model import ELMo_Model
from baisser_model import Baisser_bert
from config_reader import ConfigReader
from api_file import Sent_Generation
from web_scraping import scraping
from database import mongo_connection
from snow_integration import Snow_inc
import numpy as np

import warnings
warnings.filterwarnings("ignore")


app = Flask(__name__)

# Load Config File
config_reader = ConfigReader()
configuration = config_reader.read_config()

# Calling API File
api_fun = Sent_Generation()

# Calling scraping file
scrape_data = scraping()

# Calling model
# model = ELMo_Model()
model = Baisser_bert()

# Connecting MongoDB
database_connection = mongo_connection()

# Service now integration
snow_inc = Snow_inc()

# defenitions for routing the chat flow
def check_value_exist(test_dict,issue_list):
  for ele in issue_list:  
    for ke,va in zip(test_dict.keys(),test_dict.values()):
        if ele in va:
            match_val = ke
            break
        else:
            match_val = "No Match"
    return match_val

def phone_issue_round_1(issue_dict,pred_issue_slots,solution_dict): # giving trouble shoot guides for intent == phone issue

  keys = check_value_exist(issue_dict,pred_issue_slots)

  if keys == "No Match":
      resp = "Understood that there is some issue with your device. Could you tell me little bit breif and clear, so that I can understand and help you."
  else:
      resp = solution_dict[keys]

  return resp # give T shoot as the 1st response



def phone_issue_round_2_yes(prev_slots_list,issue_ext,issue_room,issue_issue): ## initiate if user given yes for round 1
  try:
    extlist = [i for i in prev_slots_list[-2].keys() if i=="target_extension"]
    ext = prev_slots_list[-2][extlist[0]][0]
    roomlist = [i for i in prev_slots_list[-2].keys() if i=="room_no"]
    room = prev_slots_list[-2][roomlist[0]][0]
    issuelist = [i for i in prev_slots_list[-2].keys() if i=="issue"]
    iss = prev_slots_list[-2][issuelist[0]][0]
    issue_ext.append(ext)
    issue_room.append(room)
    issue_issue.append(iss)
    resp = "Okay.. so we are proceeding to open incident, before that let me check the details that you've given\
the user's extension number is {}, Room/Office loaction is {} and issue is / related to:'{}'.Confirm if its correct..".format(ext,room,iss)
  except:
    resp = "Sorry, you are missing some mandatory information to proceed this request further. Please provide\
 Phone extension, location/office/room number. I cannot open a ticket without these information."
  return resp # The extracted slots verification text or error message is produced at round 2



def phone_issue_round_2_no(): ## initiate when user given no for 1st round
  resp = "Glad that my troubleshoot steps has helped to solve your problem. Thank you and have a great day !!"
  return resp # give thankyou note since issue has resolved by Tshhot steps

def slot_collection_round(prev_slots_list,issue_ext,issue_room,issue_issue): ## initiates when 1st level extraction go wrong
  try:
    extlist = [i for i in prev_slots_list[-1].keys() if i=="target_extension"]
    ext = prev_slots_list[-1][extlist[0]][0]
    roomlist = [i for i in prev_slots_list[-1].keys() if i=="room_no"]
    room = prev_slots_list[-1][roomlist[0]][0]
    issuelist = [i for i in prev_slots_list[0].keys() if i=="issue"]
    iss = prev_slots_list[0][issuelist[0]][0]
    issue_ext.append(ext)
    issue_room.append(room)
    issue_issue.append(iss)
    resp = "Alright, so let me confirm the details that you've given \
the user's extension number is {}, and Room/Office loaction is {}. Please confirm if its correct..".format(ext,room)
  except:
    resp = "Sorry, you are again missing mandatory information to proceed this request further. Please provide\
 User's name, phone extension and location/office room number. Please input these information to continue.."
  return resp # The extracted slots verification text or error message is produced at round 2




def phone_issue_round_3_yes(user_name,prev_user_query_list,ext,room,iss): # initiates when user says yes on round 2
    
    ## create data in a dictionary that accepted by snow
    ## required data to make phone issue inc
    data_to_snow = {}

    data_to_snow["u_requested_for"] = user_name[0]
    data_to_snow["u_short_description"] = "user extension: {}, located in office/ Room: {} - {}".format(ext[0],room[0],iss[0])
    data_to_snow["u_description"] = prev_user_query_list[0]
    data_to_snow["u_incident_state"] = "2"
    data_to_snow["u_category"] = "Hardware"
    data_to_snow["u_sub_category"] = "phone"
    data_to_snow["u_urgency"] = "2"
    data_to_snow["u_impact"] = "2"
    data_to_snow["u_configuration_item"] = "voip phone"
    data_to_snow["u_assignment_group"] = "burbank-assg-voice"

    inc_no_resp = snow_inc.raise_inc(data_to_snow)
    return inc_no_resp



def phone_issue_round_3_no(): ## initiates when users says no on 2nd round
  resp = "Please just provide details of User extension, room no and device issue in 1 sentence to understand better."
  return resp



def phone_issue_lost_round(): ## initiates when all the rounds has failed
  resp = "I'm really Sorry, I feels like, there is some issue with my understanding capabilities which is very rarely used to occur, since I just started to learn your data, I can serve you better going\
 forward when I learn more and more. Now you can use this link to open Incident in service now with priority = 3 and Urgency = 2\
 and make the assignment group to Burbank area.  Once completed, one of our support team will be contacted you shortly."

  return resp

# home page

def pin_reset_round_1(prev_slots_list):
    try:
        extlist = [i for i in prev_slots_list[-1].keys() if i=="target_extension"]
        ext = prev_slots_list[-1][extlist[0]][0]
        issue_ext.append(ext)
        resp = "Okay, understood that you require a voice mail pin reset so we are proceeding to open incident, before that let me check the extension number of\
 the user which is {}.Confirm if its correct..".format(ext)
    except:
        resp = "I am not seeing any extension number that you've given for the pin reset"

    return resp

def pin_reset_round_2_no():

    resp = "Okay, then please tell me the extension number of user, which required Voicemail pin reset."
    return resp

def slot_collection_pin_reset(prev_slots_list,issue_ext):
  try:
    extlist = [i for i in prev_slots_list[-1].keys() if i=="target_extension"]
    ext = prev_slots_list[-1][extlist[0]][0]
    issue_ext.append(ext)

    resp = "Alright, so let me confirm the details that you've given \
the user's extension number is {}. Please confirm if its correct..".format(ext)
  except:
    resp = "Sorry, you are again missing mandatory information to proceed this pin reset request further. Please provide\
 User's phone extension number to continue.."
  return resp



def pin_reset_round_2_yes(user_name,prev_user_query_list,issue_ext):
    try:

        data_to_snow = {}

        data_to_snow["u_requested_for"] = user_name[0]
        data_to_snow["u_short_description"] = "Please reset voice mail pin for extension number {}".format(issue_ext[0])
        data_to_snow["u_description"] = prev_user_query_list[0]
        data_to_snow["u_incident_state"] = "2"
        data_to_snow["u_category"] = "Hardware"
        data_to_snow["u_sub_category"] = "phone"
        data_to_snow["u_urgency"] = "2"
        data_to_snow["u_impact"] = "2"
        data_to_snow["u_configuration_item"] = "voip phone"
        data_to_snow["u_assignment_group"] = "burbank-assg-voice"

        inc_no_resp = snow_inc.raise_inc(data_to_snow)
        return inc_no_resp
    except:
        return "issue with connecting to service now"



@app.route('/')
@cross_origin()
def home():
    return render_template("index.html")

# user details


@app.route('/api/userdetails', methods=['POST'])
@cross_origin()
def user_details():
  try:
    name = request.form['name']
    reqname = request.form['reqname']
    email = request.form['email']
    mobile = request.form['mobile']
    user = {
        "name": name,
        "reqname": reqname,
        "email": email,
        "mobile": mobile,
        "datetime": datetime.now(timezone.utc)
    }
    db_object, db_admin_object = database_connection.db_connection()
    user_details = db_object.userdetails.insert_one(user)
    response = {
        "message": "success",
        "status": "200"
    }
  except:
      response = {
          "message": "error",
          "status": "500"
      }
  return jsonify(response)

prev_slots_list = [] # contain dictionary of all the predicted slots at each round
prev_intent_list = [] #contain predicted intents at each round
prev_user_query_list =[] #contain user query
issue_ext = []
issue_room = []
issue_issue = []
user_name = []
# intent and slot prediction

@app.route('/api/prediction', methods=['POST'])
@cross_origin()
def prediction():
  try:
    query = request.form['query']
    #_, query = api_fun.anyLangtoEng(query)
    prev_user_query_list.append(query)

    result = model.predictions(query)
    print(result)

    # User conversation to Database
    # db_object, db_admin_object = database_connection.db_connection()

    name = api_fun.get_cookie('name')
    user_name.append(name)
    reqname = api_fun.get_cookie('reqname')
    email = api_fun.get_cookie('email')
    mobile = api_fun.get_cookie('mobile')
    # userchat = {
    #     "name": name,
    #     "requestor":reqname,
    #     "email": email,
    #     "mobile": mobile,
    #     "datetime": datetime.now(timezone.utc),
    #     "Content": query,
    #     "Predicted Intent": result["intent"],
    #     "Predicted Slots": result["slots"]
    # }
    # user_chat = db_object.UserChat.insert_one(userchat)

    # General/ Techincal Intent

    issue_dict = {"not_working":["not working","not responding","no response","dead","no power","no boot","booting","out"], 
                "blank_screen":["blank","no display", "display","white display","blank display","blank screen"],
                "no_softkey":["softkey", "no soft key", "no softkey"],
                  "no_dialtone":["no dialtone","dialtone","no dial","dial"],
                  "no_sound":["no sound","hear", "not hearing","no voice","voice"],
                  "not_ringing":["no ring","no rings","not ringing","no bell"],
                  "no_out_calls":["outgoing calls","outgoing","calls","call","outgoing call", "outside calls","no calls","no call"],
                  "no_in_calls":["incoming calls", "no incoming calls","incoming"],
                  "crack_sound":["cracking sound","crack calls","cracking voice","cracking","cracked","breaking","cracked sound","cracking calls"],
                "register_issues":["register issues","not registered","not registering"]}

    solution_dict = {"not_working": "if phone is completely down, it could be due to power failure. Please check your connected port, ethernet cable and \
    and check the if its PoE(Power over Ethernet), if its not you need to connect to powerbrick to turn it on. If you are connected via\
    power brick, please check if its working or not. If you tried all the above and still having issue, you probabily\
    require assistance from our support team.\n Would you like to open an Incident",
            "blank_screen": "if phone screen is blank and shows lights on speakers and dials, then you phone probably work with a\
    soft reset.Kill the power to the phone by removing the power adapter or network cable and then reconnect\
    after that press and hold # and wait to see the buttons begin to flash in sequence.\
    Next press 123456789*0# and wait for the phone to reload\
    If method is not working try same but this time use: 3491672850*#\
    The red line buttons should continue to scroll, After 60sec, this will change to green, and the phone should the boot up correctly\
    If still issue persists you may open one incident.\n Would you like to open incident?",
            "no_softkey":"if you are'nt seeing soft key you may recently configured additional softkeys and few softkey might be hidden\
    in the 'More' button. Or you may turn on speaker and go off hook and check the display to see desired softkey. If still\
    issue is there probably you need to do configuration which requires our support.\n would you like to open incident?",
            "no_dialtone":"check your reciever cable and connection port, if display is working as normal you may restart the phone by\
    unplug and plug the phone cable and check. Still issue persists, check whether you are able to make calls even without dialtone\
    and open an incident.\n Would you like to open incident?",
            "no_sound":"check the volume button and mute button of the phone and adjust it accordingly. Try restart the phone by unplugging and \
        plugging the cable.If you still have issues. Login to end user manager and go to straming statistics and check and note down the stream 1. Check the\
    stream status active or not, remote ip address, codec and open an incident. we need those information for the assistance.\n Would you like to open incident?",
            "not_ringing":"check the volume button and ajust it accordinglyby going to settings button -> phone settings -> sound settings-> volume -> ring/speaker/handset/headset -> select level -> Save\
    if still persist you can restart phone by unplug and plug cable and may proceed to open incident to support team.\n Would you like to open incident?",
            "no_out_calls":"seems like an call outgoing issue. if incoming calls is also not coming, probably it might be a registration issue. A quick restart by unplugging and plugging of port cable might solve the problem.\
    if incoming calls are recieving and not able to make outgoing calls, then you require assistance from our support team.\n Would you like to open incident?",
            "no_in_calls": "check connectivity of phone, do a restart by unplug and plug the cable, check if outgoing calls are working or not and if working then\
    you require our team support to help you out.",
            "crack_sound":"First of all, please check your cable connection and check if its connected to correct port. crackling sounds are mostly caused by the cable that has poor electric connection or faulty power bricks(if using any) also will make this issue\
    replacing ethernet/power brick should solve the issue, if its not, open an incident to resolve this issue asap.\n Would you like to open incident?",
            "register_issues":"check registration by restarting (unplug and plug cable) if it doesn't worked, go to phone settings -> security settings -> reset security settings\
    some models wont have reset option so manually navigate to CTL/ITL files. Use **# to unlock phone and delete CTL and ITL files. Once deleted security settings files\
    do a restart and verify if its register to Call Manager. Most of cases it will work, if not raise an incident and we are happy to help.?\n Would you like to open incident?"}
    



## start of chat flow

    if result['intent'] == "phone_issue":
        
        prev_slots_list.append(result["slots"]) # appending slots
        prev_intent_list.append(result["intent"]) #appending intents


        if len(prev_intent_list) == 1: # checking whether its the 1st intent from user

            respo = phone_issue_round_1(issue_dict,result["slots"]['issue'],solution_dict) ##redirect to 1st round process
        
        if (len(prev_intent_list) == 2):
            if prev_intent_list[-2] == "phone_issue":
                respo = "Instead of giving missing information, you are just repeating the issue again.."
        response = {
    "fulfillmentMessages": [
        {
            "text": {
                "text": [
                    respo
                ]
            }
        },
        {
            "text": {
                "text": [
                
                ]
            }
        }
    ],
    "message": "success",
    "status": "200"
}
        return jsonify(response)


    if result['intent'] == "response_no":
        prev_intent_list.append(result["intent"])
        prev_slots_list.append(0) ## no slots available for response_no

        if (prev_intent_list[-2] == "phone_issue") & (len(prev_intent_list)==2):
                ##checking if its second intent and 1st was phone issue

            respo = phone_issue_round_2_no()
        
        elif (prev_intent_list[-2] == "response_yes") & (prev_intent_list[-3] == "phone_issue"):
        ## checking whether 2nd round went wrong
            respo = phone_issue_round_3_no() ## redirecting to slot collection

                
        elif prev_intent_list[-2] == "collect_slots": ## check if no recieved even after collecting slots
            respo = phone_issue_lost_round()
            prev_slots_list.clear()
            prev_intent_list.clear()
            prev_user_query_list.clear()
            issue_ext.clear()
            issue_room.clear()
            issue_issue.clear()
            user_name.clear()

        elif (prev_intent_list[-2] == "pin_reset") & (len(prev_intent_list)==2):

            respo = pin_reset_round_2_no()
        
        elif (prev_intent_list[0] == "pin_reset") | (prev_intent_list[-2] =="collect_slots"):

            respo = "Sorry.. We still not able to detect your extension number. Please try again from scratch"
            prev_slots_list.clear()
            prev_intent_list.clear()
            prev_user_query_list.clear()
            issue_ext.clear()
            issue_room.clear()
            issue_issue.clear()
            user_name.clear()



        response = {
    "fulfillmentMessages": [
        {
            "text": {
                "text": [
                    respo
                ]
            }
        },
        {
            "text": {
                "text": [
                
                ]
            }
        }
    ],
    "message": "success",
    "status": "200"
}
        return jsonify(response)




    if result["intent"] == "response_yes":

        prev_intent_list.append(result["intent"])
        prev_slots_list.append(0)

        if (prev_intent_list[-2] == "phone_issue") & (len(prev_intent_list)==2): #check if this is a open inc response after round 1 t shoot 

            respo = phone_issue_round_2_yes(prev_slots_list,issue_ext,issue_room,issue_issue) ## redirect to 2nd round to open inc

        elif (prev_intent_list[-2] == "response_yes") | (prev_intent_list[-2] =="collect_slots"): # check if this is a yes after 2nd round yes

            respo = phone_issue_round_3_yes(user_name,prev_user_query_list,issue_ext,issue_room,issue_issue) ## redirect to 3rd round to open inc
            respo = "Okay, I have successfully created incident {} for this issue and please note it down for your future references.\
 Our support team will contact you shortly regarding this issue.  Thank you and have a Great day ahead !!!".format(respo)
            prev_slots_list.clear()
            prev_intent_list.clear()
            prev_user_query_list.clear()
            issue_ext.clear()
            issue_room.clear()
            issue_issue.clear()
            user_name.clear()


        elif (prev_intent_list[-2] == "pin_reset") & (len(prev_intent_list)==2):

            respo = pin_reset_round_2_yes(user_name,prev_user_query_list,issue_ext)
            respo = "Okay, I have successfully created incident {} for this voice mail pin reset and please note it down for your future references.\
 You will receive a mail shortly from our support team with temporary pin. Please login in using that pin and change it within 3 business days.\nThank you and have a Great day ahead !!!".format(respo)
            prev_slots_list.clear()
            prev_intent_list.clear()
            prev_user_query_list.clear()
            issue_ext.clear()
            issue_room.clear()
            issue_issue.clear()
            user_name.clear()

        elif (prev_intent_list[0] == "pin_reset") & (prev_intent_list[-2] =="collect_slots"):

            respo = pin_reset_round_2_yes(user_name,prev_user_query_list,issue_ext)
            respo = "Okay, I have successfully created incident {} for this voice mail pin reset and please note it down for your future references.\
 You will receive a mail shortly from our support team with temporary pin. Please login in using that pin and change it within 3 business days.\nThank you and have a Great day ahead !!!".format(respo)
            prev_slots_list.clear()
            prev_intent_list.clear()
            prev_user_query_list.clear()
            issue_ext.clear()
            issue_room.clear()
            issue_issue.clear()
            user_name.clear()

        response = {
    "fulfillmentMessages": [
        {
            "text": {
                "text": [
                    respo
                ]
            }
        },
        {
            "text": {
                "text": [
                
                ]
            }
        }
    ],
    "message": "success",
    "status": "200"
}
        return jsonify(response)


    if result["intent"] == "collect_slots":
        prev_slots_list.append(result["slots"]) # appending slots
        prev_intent_list.append(result["intent"])

        if (prev_intent_list[-2] == "response_yes") | (prev_intent_list[-2] == "response_no"): ## slot collection can be come in various ways, but once slot collected 
            #slot collection function needed
            respo = slot_collection_round(prev_slots_list,issue_ext,issue_room,issue_issue)

        elif (prev_intent_list[-2] == "response_no") & (prev_intent_list[0] == "pin_reset"):
            respo = slot_collection_pin_reset(prev_slots_list,issue_ext)


        response = {
    "fulfillmentMessages": [
        {
            "text": {
                "text": [
                    respo
                ]
            }
        },
        {
            "text": {
                "text": [
                
                ]
            }
        }
    ],
    "message": "success",
    "status": "200"
}
        return jsonify(response)



    if result["intent"] == "pin_reset":
        prev_slots_list.append(result["slots"]) # appending slots
        prev_intent_list.append(result["intent"])

        if len(prev_intent_list) == 1:
            respo = pin_reset_round_1(prev_slots_list)
        response = {
    "fulfillmentMessages": [
        {
            "text": {
                "text": [
                    respo
                ]
            }
        },
        {
            "text": {
                "text": [
                
                ]
            }
        }
    ],
    "message": "success",
    "status": "200"
}
        return jsonify(response)



    else:
        prev_slots_list.clear()
        prev_intent_list.clear()
        prev_user_query_list.clear()
        issue_ext.clear()
        issue_room.clear()
        issue_issue.clear()
        user_name.clear()
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            "Sorry, I can't help you.. Your conversation went in the wrong direction. I am here to help you for your VoIP device related issues or requests and\
    make your life easier by opening tickets to support team behalf of you, if required. I am not trained to answer for your general queries.\
    If you have any issues with your VoIP device or need to request for VoIP services, you can connect with me. Thank you!"
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                        
                        ]
                    }
                }
            ],
            "message": "error",
            "status": "500"
        }
        return jsonify(response)
  except:
    prev_slots_list.clear()
    prev_intent_list.clear()
    prev_user_query_list.clear()
    issue_ext.clear()
    issue_room.clear()
    issue_issue.clear()
    user_name.clear()
    response = {
        "fulfillmentMessages": [
            {
                "text": {
                    "text": [
                        "Sorry for the inconvenience.. There is something went wrong which I am trying to figure it out. Please try after some time..."
                    ]
                }
            },
            {
                "text": {
                    "text": [
                    
                    ]
                }
            }
        ],
        "message": "error",
        "status": "500"
    }
    return jsonify(response)

if __name__ == '__main__':
  port = int(os.getenv('PORT', 5000))
  print("Starting app on port %d" % port)
  app.run(debug=False, port=port, host="127.0.0.1")