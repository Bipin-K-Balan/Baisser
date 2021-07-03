# Baisser

Baisser is a conversational AI, which used to automate some portion of tasks of VoIP network suppport Engineering team. The model is designed in a flexible way which can  expand its features and ability to support on other networking domain areas as well.

## Problem Statement:

As a networking support Engineer who working with lots of requests (Incidents and Requested Items (RITMs)) and client's queries will have lot of challenges to handle all those tasks in the proper manner and also should align in the specific SLA (Service Level Agreement). For a VoIP Engineer, request will be mainly recieved from their Client's VoIP phone users who having working in another business domain, so they wont be having much more technical knowlege for handling cisco phones. So we are recieving tickets to our assignment group for even small phone issues and minor trouble shootings. In some cases user's even not aware of the proper way of raising ticket will lead to divert ticket to some other assignment group and it will take long time to reach our team after several shuttles which leads to SLA breach. If customer raised a request and if there any missing details like phone extension number or device MAC address which is critical to process that request, we again need to communicate to user and if user is not reachable, that also will breach SLA by clogging these RITM in assignment queue. So out of total tickets almost 35 % of the tickets are coming like this our networking team is struggling to give assistant for much more serious issues and tasks.

## Baisser process:

1.) Take the user details and ID and take the user issue.

2.) Based on the issue of the user, it will do the intent classification from the intents that trained on our model based on our domain specific all possible intents (total 13 intents) and 36 different slots that has marked in B, I, O

3.) Once model identified the user issue/ intent, it will take the pre-defined solution which prepared by our Voice engineering experts and send it to user. This will be probably trouble shooting steps or guidance for that specific issues. This solutions are enough to solve majority of the user's small phone issues.

4.) After providing solution model ask to the user about the problem status. If solved that greet the user other wise, model will tell the user about the requirement of support team in this problem and ask the user's permission to raise ticket.

5.) If user give yes or similar response, model will see the query given by user and check whether all details are present enough to raise a ticket.(Slot filling task in NLP), if all details are present using service now API, model will raise ticket behalf of user and provide the request number to the user for further follow ups.

6.) If there is any missing details, model will ask user about the specific missing details. This will be used to create request behalf of user. This way model will be able to open request in the correct assignment group with all necessary details to process that request.

In this way network team will not get any silly requests from user since it will be handled by model and networking team will only recieve the request with all necessary information that can be directly processed without asking any queries to users. Summarizing Baisser helps networking team to reduce their workload by 25% and they can concentrate on quality work and tasks.

## Model and training:

Pulled the user request details in csv format from the service now ticketing tool to train the model. Converted direct specific format text requests into conversational format for text lines. Used approx 1178 text line which cover all the intent of users. Google's BERT transformer based model is used here for the combined intent classification and slot detection. There is no other frame works used for creating this like Rasa NLU, Google Dialogue Flow, amazon lex or azure luis due to the lack of flexibility and feature expansion. RoBERTa and BERT considered for this model, but BERT outperforms RoBERTa by 5 % in accuracy for our dataset.
The model has fine tuned on pretrained hugging face model BERT cased model for 8 epochs with batch size of 16. Model size is near to 900 MB which providing 99 % accuracy on train and 97 % accuracy on testa data for intent classification. It only took roughly 15 mins to finetune the model.

## Baisser demo:



https://user-images.githubusercontent.com/53367536/124352960-32d84d80-dc21-11eb-95dc-29ddfd2c8070.mp4

