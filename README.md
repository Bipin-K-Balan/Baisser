# Baisser

Baisser is a conversational AI, which used to automate some portion of tasks of VoIP network suppport Engineering team. The model is designed in a flexible way which can  expand its features and ability to support on other networking domain areas as well.

## Demo Video:

https://user-images.githubusercontent.com/53367536/124352960-32d84d80-dc21-11eb-95dc-29ddfd2c8070.mp4


## Problem Statement:

As a networking support Engineer who working with lots of requests (Incidents and Requested Items (RITMs)) and client's queries will have lot of challenges to handle all those tasks in the proper manner and also should align in the specific SLA (Service Level Agreement). For a VoIP Engineer, request will be mainly recieved from their Client's VoIP phone users who having working in another business domain, so they wont be having much more technical knowlege for handling cisco phones. So we are recieving tickets to our assignment group for even small phone issues and minor trouble shootings. In some cases user's even not aware of the proper way of raising ticket will lead to divert ticket to some other assignment group and it will take long time to reach our team after several shuttles which leads to SLA breach. If customer raised a request and if there any missing details like phone extension number or device MAC address which is critical to process that request, we again need to communicate to user and if user is not reachable, that also will breach SLA by clogging these RITM in assignment queue. So out of total tickets almost 35 % of the tickets are coming like this our networking team is struggling to give assistant for much more serious issues and tasks.

## Baisser process:

1.) Take the user details and ID while clicking the chat button and take the user issue as input.

2.) Based on the issue of the user, it will do the intent classification from the intents that trained on our model based on our domain specific all possible intents (total 13 intents) and 36 different slots that has marked in B, I, O labels.

3.) Once model identified the user issue/ intent, it will take the appropriate pre-defined solution for that issue which prepared by our Voice engineering experts and send it to user. This will be probably trouble shooting steps or guidance for that specific issues. This solutions are enough to solve majority of the user's small phone issues.

4.) After providing solution model asks user about the problem status. If solved then greet the user with a Thank you note other wise, model will tell the user about the requirement of support team in this problem and ask the user's permission to raise ticket.

5.) If user give yes or similar response as a permission, model will see the query given by user and check whether all details are present enough to raise a ticket.(Slot filling task in NLP. Here for processing each phone requests, different set of slots are required), if all details are present in the 1st query itself, using service now API  model will raise ticket behalf of user and provide the request number to the user as a response for further follow ups.

6.) If there is any missing details, model will ask user about the specific missing details. Once user enter missing details, model will validate and user respond positive these details will be used to create request behalf of user. This way model will be able to open request in the correct assignment group with all necessary details to process that request and return the request number to the user with enough details regarding the expected response from engineering team.


In this way our network team will not get any silly requests from user since it will be handled by model and networking team will only recieve the request with all necessary information that can be directly processed without asking any queries to users. At the same time user also getting benefits by getting immediate solution for small issues and getting a good interface to open tickets without any hassle or knowing it's technical details. 

Summarizing Baisser helps both Customers by make their life easy and Network support team to reduce their workload of 25% by nullifying false tickets, silly tickets and opening tickets without any missing details which are necessary to process it so that they can concentrate on quality work and tasks.

## Data gathering and Model training:

For getting the dataset to train the model, I've pulled the user request details in csv format from the Service now ticketing tool. Also used the conversations from the distribution Mail box and converted direct specific format text requests into conversational format. Used approx 1178 text line which cover all the intent of users in our working domain area.

![image](https://user-images.githubusercontent.com/53367536/124431882-98961800-dd8e-11eb-85c1-0ede45d58829.png)

Google's BERT transformer base cased model is used here for the joint intent classification and slot detection. I've used BERT's own tokenizer which having vocabulary size of 28,996 words to tokenize the sentence. Also from doing EDA, the maximum conversation sentence length from user converstaional dataset is 48. So further text encoding is based on that max sequence length, if sentence coming more that that limit will be chopped off or if less than that limit will be padded with zeros to make it fixed length. 

![image](https://user-images.githubusercontent.com/53367536/124421806-d475b100-dd7f-11eb-9beb-d7844e5bc080.png)

I have picked the hugging face version of the BERT transformer model (TFBERT Model -> Tensorflow 2.x based) which having 108M parameters for doing fine tuning. By diving into their architecture and Subclassing coding style, these model is taking inputs as tuples/ list/ dictionary of input id, attenstion mask, token type id, pos id etc.. For our use case, we need to convert our encoded text into input id/token id and attention masks. We also make the intent map since it wont take the labels as aphabets, so we indexing it with a map and apply to our dataset.

The output of BERT gives sequence and pooled output (We have dropeed TF DistilBERT Model since it doesn't give the pooler output(which is the hiiden state of [CLS] used for classification tasks, which is required for the intent classification.). Since we are using model as joint model, so we require last hidden state for slot filling and pooler output for intent classification. So in architecture modification we introduce drop out after the sequence output followed by a dense layer that having nerons equal to number of slots and pooled output layer also having drop out followed by dense layer that having neurons equals number of intents for classification, which will give the slot and intent logits as the model output.

![image](https://user-images.githubusercontent.com/53367536/124424083-0852d580-dd84-11eb-86f9-db084bc77237.png)

The model has fine tuned for 8 epochs, Adam optimizer, Sparse categorical cross entropy loss function, very small learning rate of 3e-5 with batch size of 13 since our dataset is very limited compared to a model that pretrained on huge dataset, so we need our model to get every variation of user data. Model size is near to 900 MB which providing 99 % accuracy on train and 96 % accuracy on testa data for intent classification. It only took roughly 3 to 5 mins to finetune the model on Google Colab NVidia Tesla T4 GPU.

![image](https://user-images.githubusercontent.com/53367536/124425060-a2ffe400-dd85-11eb-83ab-ae8c33d017a7.png)

The model is able to predict both intent of the user request and required slots accurately with out any failure cases.

![image](https://user-images.githubusercontent.com/53367536/124426253-6d5bfa80-dd87-11eb-91fa-9f707d5fc060.png)


For making the final application with this BERT model, there is no other popular NLU frame works like Rasa NLU, Google Dialogue Flow, Amazon lex or Azure luis used for creating this conversational AI, due to the lack of flexibility and feature expansion. There they are giving an interface to create and modify model with working on some .md and yaml files and most of the conversational AI, we have to use their own cloud platform to perform the task except Rasa. Here we are creating the full interface, so we can do any kind of integration of feature expansion based on our requirement.

Javascript, html and css to create the frontend of the model like a chatbot like interface (please see demo video to get an idea) and Service now API is used to make integration of Conversational AI to create and open tickets with customer given details in Service Now ticketing platform. Flask is used for binding the front end to python backend. Eventhough the main agenta of this AI to automate the ticket generation from user with all necessary information and solve their small issues related to cisco phones rather than making a human level interactive conversational AI, I've included basic conversational yes/no kind of intent along with the technical user intent while training the model to go the conversation between AI and user forward and for validating the user given inputs. The conversational flow is predefined and any queries apart from the topic will be avoided and model convience the user about the tasks which model capable of by giving proper responses. RoBERTa model also considered for the base model by seeing the performance results on research paper, but BERT outperforms RoBERTa by 5% of  accuracy with our dataset.

## Future expansion of this AI which are possible:

1.) Can merge other networking domain support which is common for this client and use it as a centralized AI.

2.) Can make one admin panel, which can control the performance and retraining approach of the model with few clicks by creating proper CI/CD pipelines.

3.) As of now the model is under testing and performing well on unseen user request, but if we use the uncoming test data coming from user and once the user validated the predicted intents and slots, we can store these texts into databases like Mongo DB, which can be later used for retraining.

## Deployment

Since the entire conversational AI has been developed for our client, initial step was to show the demo of the designed application and explain its functionality and the resulting benefits to our manager, I had to deploy it in a cloud environment. Since it is using heavy weighted BERT as the backend model, I also want to test its perfomance in cloud environment. Considering the usage of this application for a large scale of customers and scalability during business peak hours and holidays, I have used Kubernetics orchestration framework to deploy the application, once it is containarized. I have used Google Cloud Platform (GCP) as the cloud platform for deployment. GCP has their Kubernetes engine called GKE (Google Kubernetes Engine) which ensure all bells and whistles of easiness in deployment, auto-scaling based on utilization of resources, load balancing etc..

1.) Test application in local environment.

2.) Create a Dockerfile by including necessary commands enough to containarize the entire application so that it will work as expected in any environment.

3.) Create deployment.yaml and services.yaml which are the configuration files required for Kubernetes deployment.

4.) Push all the application files along with above 3 files into GCP, open GCP cloud Shell Editor and give the gcloud command to containerize the uploaded application by running the content that given in Docker file and it will be stored in Google Container Registry. Also required necessary admin permissions for storage, GKE

5.) Now create Kubernetes cluster


![baisser deployment in gke auto pilot](https://user-images.githubusercontent.com/53367536/127733295-03d9852a-fb9d-4f7b-951d-93e737727b90.PNG)
![deplo](https://user-images.githubusercontent.com/53367536/127733315-9354d78b-795a-419b-8f3c-6b07fc177b72.PNG)
![deploymentbaisser](https://user-images.githubusercontent.com/53367536/127733318-8af994d2-eda9-4ff4-9d4c-74e5bfb560dd.PNG)
![baisser_deployment](https://user-images.githubusercontent.com/53367536/127733322-6fdb8069-2f13-4be1-9b25-ff57074e2164.PNG)
![pushing deployment and service files](https://user-images.githubusercontent.com/53367536/127733325-126f4f40-1eaf-47a3-9b40-beede18cd1ea.PNG)
![pods status](https://user-images.githubusercontent.com/53367536/127733332-92b9149d-9564-468b-820f-3e71a5f4c593.PNG)
![got ip in k8](https://user-images.githubusercontent.com/53367536/127733335-b026e328-6dfb-43ab-85ca-f0c81eeaf43f.PNG)
![k8](https://user-images.githubusercontent.com/53367536/127733337-a2fd5fb7-9663-4ee4-aed8-04da4c70b2af.PNG)



