import requests

class Snow_inc():

    def raise_inc(self,data_input):

        API_ENDPOINT = "https://dev57960.service-now.com/api/now/import/u_inbound_integration_inc"
        #req = {"u_requested_for":"Abel Tuter","u_short_description":"2236729 - VM Reset","u_description":"i need to reset vm password","u_incident_state":"2","u_category":"Hardware","u_sub_category":"phone","u_urgency":"2","u_impact":"2","u_configuration_item":"voip phone","u_assignment_group":"burbank-assg-voice"}
        r = requests.post(url = API_ENDPOINT, json = data_input, auth = ('admin', 'kIT7wIEni6qL'))
        r_to_json = r.json()
        inc_number_resp = r_to_json["result"][0]["display_value"]

        return inc_number_resp