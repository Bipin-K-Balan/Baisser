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

def phone_issue_round_1(issue_dict,pred_issue_slots): # giving trouble shoot guides for intent == phone issue

    def check_value_exist(test_dict,issue_list):
        for ke,va in zip(issue_dict.keys(),issue_dict.values()):
            for v in va:
                for ele in issue_list:
                    if ele == v:
                return ke
        else:
            return "No Match"

    keys = check_value_exist(issue_dict,result["slots"]['issue'])

    if keys == "No Match":
        resp = "Understood that there is some issue with your device. Could you tell me little bit breif and clear, so that I can understand and help you."
    else:
        resp = solution_dict[keys]

    return resp # give T shoot as the 1st response



def phone_issue_round_2_yes(prev_slots_list): ## initiate if user given yes for round 1
    try:
        extlist = [i for i in prev_slots_list[-1].keys() if i=="target_extension"]
        ext = prev_slots_list[-1][extlist[0]][0]
        namelist = [i for i in prev_slots_list[-1].keys() if i=="new_name" or i=="user_name"or i =="request_owner"]
        name = prev_slots_list[-1][namelist[0]][0]
        if name in ["my","I","i","me"]:
            name = "Requestor"
        roomlist = [i for i in prev_slots_list[-1].keys() if i=="room_no"]
        room = prev_slots_list[-1][roomlist[0]][0]
        issuelist = [i for i in prev_slots_list[-1].keys() if i=="issue"]
        iss = prev_slots_list[-1][issuelist[0]][0]
        resp = "Okay.. we are proceeding to open incident, before that let me check the details that you've given\
                The Username is {}, extension number is {}, Room/Office loaction is {} and issue is / related to:'{}'.Confirm if its correct..".format(name,ext,room,iss)
    except Exception as e:
        resp = "Sorry, you are missing some information to proceed this request further. For phone issue related incidents, We require\
            User name, phone extension and location/office room number. Please input the request again with these information"
    return resp # The extracted slots verification text or error message is produced at round 2



def phone_issue_round_2_no(): ## initiate when user given no for 1st round
    resp = "Glad that my troubleshoot steps has helped to solve your problem. Thankyou have a great day!!"
    return resp # give thankyou note since issue has resolved by Tshhot steps



def phone_issue_round_3_yes(): # initiates when user says yes on round 2
    
    ## create data in a dictionary that accepted by snow
    ## required data to make phone issue inc
    data_to_snow = {}

    data_to_snow["u_requested_for"] = reqname
    data_to_snow["u_short_description"] = "user extension: {}, located in office/ Room: {} - {}".format(ext,room,iss)
    data_to_snow["u_description"] = query
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
    resp = "Please just provide details of User name, extension, room no and device issue in 1 sentence to understand better."
    return resp



def phone_issue_lost_round(): ## initiates when all the rounds has failed
    resp = "I'm really Sorry, I feels like, there is some issue with my understanding capabilities, since I just started to learn your data, I can serve you better going\
            forward whn I learn more and more. Now you can use this link to open Incident in service now with priority = 3 and Urgency = 2\
            and make the assignment group to Burbank area.  Once completed, one of our support team will be contacted you shortly."
    return resp

# home page


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
            "reqname": reqname
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
prev_user_query_list =[]

# intent and slot prediction

@app.route('/api/prediction', methods=['POST'])
@cross_origin()
def prediction():
    try:
        query = request.form['query']
        _, query = api_fun.anyLangtoEng(query)
        prev_user_query_list.append(query)
        result = model.predictions(query)
        print(result)

        # User conversation to Database
        db_object, db_admin_object = database_connection.db_connection()

        name = api_fun.get_cookie('name')
        reqname = api_fun.get_cookie('reqname')
        email = api_fun.get_cookie('email')
        mobile = api_fun.get_cookie('mobile')
        userchat = {
            "name": name,
            "requestor":reqname,
            "email": email,
            "mobile": mobile,
            "datetime": datetime.now(timezone.utc),
            "Content": query,
            "Predicted Intent": result["intent"],
            "Predicted Slots": result["slots"]
        }
        user_chat = db_object.UserChat.insert_one(userchat)

        # General/ Techincal Intent

        issue_dict = {"not_working":["not working","not responding","no response","dead","no power","no boot","booting","out"], 
                    "blank_screen":["blank","no display", "display","white display","blank display","blank screen"],
                    "no_softkey":["softkey", "no soft key", "no softkey"],
                     "no_dialtone":["no dialtone","dialtone","no dial","dial"],
                     "no_sound":["no sound"."hear", "not hearing","no voice","voice"],
                     "not_ringing":["no ring","no rings","not ringing","no bell"],
                     "no_out_calls":["outgoing calls","calls","call","outgoing call", "outside calls","no calls","no call"],
                     "no_in_calls":["incoming calls", "no incoming calls","incoming"],
                     "crack_sound":["cracking sound","crack calls","cracking voice","cracking","cracked","breaking","cracked sound","cracking calls"]
                    "register_issues":["register issues","not registered","not registering"]}

        solution_dict = {"not_working": "if phone is completely down, it could be due to power failure. Please check your connected port, ethernet cable and \
                            and check the if its PoE(Power over Ethernet), if its not you need to connect to powerbrick to turn it on. If you are connected via\
                            power brick, please check if its working or not. If you tried all the above and still having issue, you probabily\
                            require assistance from our support team. Would you like to raise an incident for this?",
                        "blank_screen": "if phone screen is blank and shows lights on speakers and dials, then you phone probably work with a\
                            soft reset.Kill the power to the phone by removing the power adapter or network cable and then reconnect\
                            after that press and hold # and wait to see the buttons begin to flash in sequence.\
                            Next press 123456789*0# and wait for the phone to reload \
                            If st method is not working try same but this time use: 3491672850*#\
                            The red line buttons should continue to scroll, After 60sec, this will change to green, and the phone should the boot up correctly\
                            If still issue persists you may open one incident. Do you want to open one?",
                        "no_softkey":"if you are'nt seeing soft key you may recently configured additional softkeys and few softkey might be hidden\
                            in the 'More' button. Or you may turn on speaker and go off hook and check the display to see desired softkey. If still\
                            issue is there probably you need to do configuration which requires our support. Would you like to raise incident for this",
                        "no_dialtone":"check your reciever cable and connection port, if display is working as normal you may restart the phone by\
                            unplug and plug the phone cable and check. Still issue persists, check whether you are able to make calls even without dialtone\
                            and open an incident. Would you like to open incident?",
                        "no_sound":"check the volume button and mute button of the phone and adjust it accordingly. Try restart the phone by unplugging and \
                            plugging the cable.If you still have issues. Login to end user manager and go to straming statistics and check and note down the stream 1. Check the\
                            stream status active or not, remote ip address, codec and open an incident. we need those information for the assistance.\
                            Would you like to open incident?",
                        "not_ringing":"check the volume button and ajust it accordinglyby going to settings button -> phone settings -> sound settings-> volume -> ring/speaker/handset/headset -> select level -> Save\
                            if still persist you can restart phone by unplug and plug cable and may proceed to open incident to support team.\
                            Is this information helpful or Would you like to open ticket?",
                        "no_out_calls":"if incoming calls is also not coming, probably it might be a registration issue. A quick resart by unplugging and plugging might solve the problem\
                            if icoming calls are recieving and there is issue with outgoing calls, then you require assistance from our support team to resolve it. Would you like to open\
                            incident for this?",
                        "no_in_calls": "check connectivity of phone, do a restart by unplug and plug the cable, check if outgoing calls are working or not and if working then\
                            you require our team support to help you out. Would you like to open incident?",
                        "crack_sound":"First of all, please check your cable connection and check if its connected to correct port. crackling sounds are mostly caused by the cable that has poor electric connection or faulty power bricks(if using any) also will make this issue\
                            replacing ethernet/power brick should solve the issue, if its not, open an incident to resolve this issue asap. Would you like to open incident?",
                        "register_issues":"check registration by restarting (unplug and plug cable) if it doesn't worked, go to phone settings -> security settings -> reset security settings\
                            some models wont have reset option so manually navigate to CTL/ITL files. Use **# to unlock phone and delete CTL and ITL files. Once deleted security settings files\
                            do a restart and verify if its register to Call Manager. Most of cases it will work, if not raise an incident and we are happy to help. Would you like to open incident?"}
        
    



## start of chat flow

        if result['intent'] == "phone_issue": 
            prev_slots_list.append(result["slots"]) # appending slots
            prev_intent_list.append(out["intent"]) #appending intents

            if len(prev_intent_list) == 1: # checking whether its the 1st intent from user

                respo = phone_issue_round_1(issue_dict,result["slots"]['issue']) ##redirect to 1st round process




        if result['intent'] == "response_no":
            prev_intent_list.append(result["intent"])
            prev_slots_list.append(0) ## no slots available for response_no

            if (prev_intent_list[-2] == "phone_issue") & (len(prev_slots_list)==2):
                    ##checking if its second intent and 1st was phone issue

                resp = phone_issue_round_2_no()
            
            elif (prev_intent_list[-2] == "response_yes") & (prev_intent_list[-3] == "phone_issue"):
            ## checking whether 2nd round went wrong
                resp = phone_issue_round_3_no(): ## redirecting to slot collection

                    
            elif prev_intent_list[-2] == "collect_slots": ## check if no recieved even after collecting slots
                resp = phone_issue_lost_round():




        if result["intent"] == "response_yes":
            prev_intent_list.append(result["intent"])
            prev_slots_list.append(0)

            if (prev_intent_list[-2] == "phone_issue") & (len(prev_intent_list)==2): #check if this is a open inc response after round 1 t shoot 

                resp = phone_issue_round_2_yes(prev_slots_list): ## redirect to 2nd round to open inc

            elif prev_intent_list[-2] == "response_yes": # check if this is a yes after 2nd round yes

                resp = phone_issue_round_3_yes(): ## redirect to 3rd round to open inc

            elif prev_intent_list[-2] == "collect_slots": ## check if yes coming after collecting slots

                resp = phone_issue_round_3_yes() # redirect to raise inc



        if result["intent"] == "collect_slots":

            if (prev_intent_list[-2] == "response_yes") | (prev_intent_list[-2] == "response_no"): ## slot collection can be come in various ways, but once slot collected 

                resp = phone_issue_round_3_yes()
            



        
        











        if result[1][0] in technical_intent:
            res_satisfied_or_assistance = 'Are you satisfied with your query?'
            intent_type = 'Technical'
        elif result[1][0] in ticket_gen_filter and result[1][0] in general_intent:
            res_satisfied_or_assistance = 'Do you want further assistance?'
            intent_type = 'General'
        else:
            res_satisfied_or_assistance = 'Are you satisfy with your query or you want to generate ticket for it?Please select suitable option.'
            # res_satisfied_or_assistance = 'Do you want further assistance?'
            intent_type = 'General'

        # Scrapping based upon the confidence score
        print(result[0])
        if result[0] >= 50 and result[1][0] not in scrape_data_filter:
            result = result[1]
            ip = result[0]
            f = open('load_intent_filter/intents_map.json', )
            data = json.load(f)

            # Reply based upon database added by admin

            # For list of courses from admin
            if ip in form_filter:
                list_of_courses = db_admin_object.megatron_course.find()
                list_of_courses = json.dumps(
                    list(list_of_courses), default=str)
            # For list of community courses from admin
            elif ip in community_form_filter:
                list_of_courses = db_admin_object.megatron_course.find(
                    {"course_type": "CO"})
                list_of_courses = json.dumps(
                    list(list_of_courses), default=str)
            elif ip == "NewBatch_details":
                list_of_courses = db_admin_object.megatron_course.find(
                    {"starting_date": {"$gt": datetime.now()}})
                list_of_courses = json.dumps(
                    list(list_of_courses), default=str)
            elif ip == "Dashboard_access":
                response_access = api_fun.reg_stu()
            # Ticket generate
            elif ip in ticket_gen_filter:
                mail_send = Sent_Generation()
                mail_send.fallback_support(query)
                list_of_courses = []
            elif ip in list_thumbnail_filter:
                list_of_url = data[ip]
                res = scrape_data.thumbnail_generate(
                    list_of_url, res_satisfied_or_assistance, intent_type)
                list_of_courses = []
            else:
                list_of_courses = []

            reply = data[ip]
            reply = api_fun.engtoHindi(reply)

            if ip in list_thumbnail_filter:
                response = res
            elif ip == "Dashboard_access":
                response = response_access
            else:

                response = {
                    "fulfillmentMessages": [
                        {
                            "text": {
                                "text": [reply]
                            }
                        },
                        {
                            "text": {
                                "text": [
                                    api_fun.engtoHindi(
                                        res_satisfied_or_assistance)
                                ]
                            }
                        }
                    ],
                    "intent": ip,
                    "list_of_courses": list_of_courses,
                    "message": "success",
                    "reply": reply,
                    "status": "200",
                    "intent_type": intent_type
                }
        else:
            print('predicted intent : '+str(result[1][0]))
            list_of_keyword = scrape_data.keyword_extract(query)
            print(list_of_keyword)
            if(len(list_of_keyword) > 0):
                strings = ' + '.join(list_of_keyword)
                response = scrape_data.scrapping_url(strings)
                # Database user response
                user_scrap_reply = {
                    "email": email,
                    "datetime": datetime.now(timezone.utc),
                    "Content": query,
                    "Extracted Words": list_of_keyword,
                    "Scrapping Response": response

                }
                user_scrap_chat = db_object.ScrappingChat.insert_one(
                    user_scrap_reply)
            else:
                response = {
                    "fulfillmentMessages": [
                        {
                            "text": {
                                "text": [
                                    api_fun.engtoHindi(
                                        "Sorry!! we are not able to process your query at a moment. Please try again later.")
                                ]
                            }
                        },
                        {
                            "text": {
                                "text": [
                                    api_fun.engtoHindi(
                                        "Do you want further assistance?")
                                ]
                            }
                        }
                    ],
                    "intent": "Not_identified",
                    "message": "error",
                    "status": "500",
                    "intent_type": "General"
                }
    except:
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Sorry!! we are unable to process your request at this time. Please try again later.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
                        ]
                    }
                }
            ],
            "message": "error",
            "status": "500",
            "intent_type": "General"
        }
    print(response)
    return jsonify(response)

# Fetch database details


@app.route('/api/dbFetchDetails', methods=['POST'])
@cross_origin()
def dbFetchDetails():
    try:
        db_object, db_admin_object = database_connection.db_connection()
        list_of_courses = db_admin_object.megatron_course.find()
        list_of_courses = json.dumps(list(list_of_courses), default=str)
        response = {
            "list_of_courses": list_of_courses,
            "message": "success",
            "status": "200"
        }
    except:
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Sorry!! we are not able to process your query at a moment. Please try again later.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
                        ]
                    }
                }
            ],
            "message": "error",
            "status": "500"
        }
    return jsonify(response)

# Fetch database details for registered student


@app.route('/api/dbFetchDetailsForRegisteredStudent', methods=['POST'])
@cross_origin()
def dbFetchDetailsForRegisteredStudent():
    response = api_fun.reg_stu()
    return jsonify(response)

# Language Translation


@app.route('/api/languageTranslateWithThumbnail', methods=['POST'])
@cross_origin()
def languageTranslateWithThumbnail():
    try:
        content = request.get_json()
        query = content['msg']
        print(query)
        output = api_fun.engtoHindi(query)
        list_of_url = [output, content['url_link']]
        res_satisfied_or_assistance = "Do you want further assistance?"
        intent_type = "General"
        response = scrape_data.thumbnail_generate(
            list_of_url, res_satisfied_or_assistance, intent_type)
        # response = {
        #     "result": output,
        #     "response": res,
        #     "message": "success",
        #     "status": "200"
        # }
    except:
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Sorry!! we are not able to process your query at a moment. Please try again later.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
                        ]
                    }
                }
            ],
            "message": "error",
            "status": "500"
        }
    return jsonify(response)

# assignment Query


@app.route('/api/assignmentQuery', methods=['POST'])
@cross_origin()
def assignmentQuery():
    try:
        query = request.form['query']
        print(query)
        output = api_fun.fallback_support(query)
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "We have sent email to support team regarding the same. It will be sort out within 24 hours.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
                        ]
                    }
                }
            ],
            "message": "success",
            "status": "200"
        }
    except:
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Sorry!! we are not able to process your query at a moment. Please try again later.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
                        ]
                    }
                }
            ],
            "message": "error",
            "status": "500"
        }
    return jsonify(response)

# internship Query BUtton


@app.route('/api/internshipQueryButton', methods=['POST'])
@cross_origin()
def internshipQueryButton():
    try:
        query = request.form['query']
        print(query)
        output = api_fun.fallback_support(query)
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "We have sent email to support team regarding the same. It will be sort out within 24 hours.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
                        ]
                    }
                }
            ],
            "message": "success",
            "status": "200"
        }
    except:
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Sorry!! we are not able to process your query at a moment. Please try again later.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
                        ]
                    }
                }
            ],
            "message": "error",
            "status": "500"
        }
    return jsonify(response)

# certificate Query


@app.route('/api/certificateQuery', methods=['POST'])
@cross_origin()
def certificateQuery():
    try:
        query = request.form['query']
        print(query)
        output = api_fun.fallback_support(query)
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "We have sent email to support team regarding the same. It will be sort out within 24 hours.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
                        ]
                    }
                }
            ],
            "message": "success",
            "status": "200"
        }
    except:
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Sorry!! we are not able to process your query at a moment. Please try again later.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
                        ]
                    }
                }
            ],
            "message": "error",
            "status": "500"
        }
    return jsonify(response)

# batch Query


@app.route('/api/batchQuery', methods=['POST'])
@cross_origin()
def batchQuery():
    try:
        query = request.form['query']
        print(query)
        output = api_fun.fallback_support(query)
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "We have sent email to support team regarding the same. It will be sort out within 24 hours.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
                        ]
                    }
                }
            ],
            "message": "success",
            "status": "200"
        }
    except:
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Sorry!! we are not able to process your query at a moment. Please try again later.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
                        ]
                    }
                }
            ],
            "message": "error",
            "status": "500"
        }
    return jsonify(response)

# courseTimings


@app.route('/api/courseTimings', methods=['POST'])
@cross_origin()
def courseTimings():
    coursename = request.form['coursename']
    response = api_fun.courseTimings(coursename)
    return jsonify(response)

# course_contents


@app.route('/api/courseContents', methods=['POST'])
@cross_origin()
def courseContents():
    coursename = request.form['coursename']
    response = api_fun.courseContents(coursename)
    return jsonify(response)

# courseFees


@app.route('/api/courseFees', methods=['POST'])
@cross_origin()
def courseFees():
    coursename = request.form['coursename']
    response = api_fun.courseFees(coursename)
    return jsonify(response)

# courseDetails


@app.route('/api/courseDetails', methods=['POST'])
@cross_origin()
def courseDetails():
    coursename = request.form['coursename']
    response = api_fun.courseDetails(coursename)
    return jsonify(response)

# class link


@app.route('/api/classLink', methods=['POST'])
@cross_origin()
def classLink():
    coursename = request.form['coursename']
    date = request.form['date']
    response = api_fun.classLink(coursename, date)
    return jsonify(response)

# payment Detail


@app.route('/api/paymentDetail', methods=['POST'])
@cross_origin()
def paymentDetail():
    coursename = request.form['coursename']
    response = api_fun.paymentDetail(coursename)
    return jsonify(response)

# resumeDetails


@app.route('/api/resumeDetails', methods=['POST'])
@cross_origin()
def resumeDetails():
    coursename = request.form['coursename']
    response = api_fun.resumeDetails(coursename)
    return jsonify(response)

# youtube link


@app.route('/api/youtubeLink', methods=['POST'])
@cross_origin()
def youtubeLink():
    coursename = request.form['coursename']
    date = request.form['date']
    response = api_fun.youtubeLink(coursename, date)
    return jsonify(response)

# fileNotFound


@app.route('/api/fileNotFound', methods=['POST'])
@cross_origin()
def fileNotFound():
    coursename = request.form['coursename']
    topic = request.form['topic']
    response = api_fun.fileNotFound(coursename, topic)
    return jsonify(response)

# internshipQuery


@app.route('/api/internshipQuery', methods=['POST'])
@cross_origin()
def internshipQuery():
    coursename = request.form['coursename']
    response = api_fun.internshipQuery(coursename)
    return jsonify(response)

# dashboardAccess


@app.route('/api/dashboardAccess', methods=['POST'])
@cross_origin()
def dashboardAccess():
    coursename = request.form['coursename']
    response = api_fun.dashboardAccess(coursename)
    return jsonify(response)

# satisfyNoScrapeData


@app.route('/api/satisfyNoScrapeData', methods=['POST'])
@cross_origin()
def satisfyNoScrapeData():
    try:
        content = request.get_json()
        query = content['user_query']
        strings = ' + '.join(query.split(" "))
        response = scrape_data.scrapping_url(strings)
        response["scrape_msg_after"] = api_fun.engtoHindi(
            "Are you satisfy with your query or you want to generate ticket for it?Please select suitable option.")
    except:
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Sorry!! we are not able to process your query at a moment. Please try again later.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
                        ]
                    }
                }
            ],
            "message": "error",
            "status": "500"
        }
    return jsonify(response)


# Not satisfied response send email to support
@app.route('/api/notSatisfiedSendEmail', methods=['POST'])
@cross_origin()
def notSatisfiedSendEmail():
    try:
        content = request.get_json()
        query = content['user_query']
        output = api_fun.fallback_support(query)
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "We have sent email to support team regarding the same. It will be sort out within 24 hours.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
                        ]
                    }
                }
            ],
            "message": "success",
            "status": "200"
        }
    except:
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Sorry!! we are not able to process your query at a moment. Please try again later.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
                        ]
                    }
                }
            ],
            "message": "error",
            "status": "500"
        }
    return jsonify(response)

# technicalButtonPrediction


@app.route('/api/technicalButtonPrediction', methods=['POST'])
@cross_origin()
def technicalButtonPrediction():
    try:
        content = request.get_json()
        query = content['msg']
        print(query)
        technical_concept = content['technical_concept']
        f = open('load_intent_filter/intents_map.json', )
        data = json.load(f)
        list_thumbnail_filter = np.load(
            'load_intent_filter/list_thumbnail.npy', allow_pickle=True)
        intent_type = "Technical"
        msg = "Are you satisfied with your query?"
        res_satisfied_or_assistance = api_fun.engtoHindi(msg)
        if technical_concept in list_thumbnail_filter:
            list_of_url = data[technical_concept]
            response = scrape_data.thumbnail_generate(
                list_of_url, res_satisfied_or_assistance, intent_type)
        else:
            response = {
                "fulfillmentMessages": [
                    {
                        "text": {
                            "text": [
                                api_fun.engtoHindi(
                                    "Sorry!! we are not able to process your query at a moment. Please try again later.")
                            ]
                        }
                    },
                    {
                        "text": {
                            "text": [
                                api_fun.engtoHindi(
                                    "Do you want further assistance?")
                            ]
                        }
                    }
                ],
                "message": "error",
                "status": "500"
            }
    except:
        response = {
            "fulfillmentMessages": [
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Sorry!! we are not able to process your query at a moment. Please try again later.")
                        ]
                    }
                },
                {
                    "text": {
                        "text": [
                            api_fun.engtoHindi(
                                "Do you want further assistance?")
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
