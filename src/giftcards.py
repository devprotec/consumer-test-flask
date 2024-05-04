from datetime import datetime
import random
import string
from .models import transactions, giftcards, customers
from .notifications import Notifications
import uuid
import datetime
import requests
from flask import jsonify, request
from bson import json_util
import json


class GiftCards:
    """"
    Entry for a gift card Record. Contains the following fields:
        - id: Unique identifier for the record.
        - amount: Amount of the gift card.
        - status: Status of the gift card (active, expired, used, inactive).
        - creation_timestamp: Date the gift card was created.
        - balance: Balance of the gift card.
        - type: Type of the gift card (BUSINESS, PIYATA).
        - currency: Currency of the gift card (GHS, RWF).
        - created_by: The admin who created the gift card.
        - gifter_id: The id of the customer who gifted the card.
        - gifter_name: The name of the customer who gifted the card.
        - gifted_id: The id of the customer who received the gift card.
        - gifted_name: The name of the customer who received the gift card.
    """

    @staticmethod
    def retrieve_giftcard_by_uuid(giftcard_id):
        """
        Retrieve a giftcard record from the database.
        """
        my_query = {"id": giftcard_id}
        giftcard = giftcards.find_one(my_query)
        if giftcard is None:
            return jsonify({"error": "Gift card not found"}), 401
        return giftcard

    @staticmethod
    def delete_giftcard(giftcard_id):
        """
        Delete a giftcard record from the database.
        """
        my_query = {"id": giftcard_id}
        deleted_giftcard = giftcards.delete_one(my_query)
        if deleted_giftcard.deleted_count == 1:
            return jsonify({"success": "Gift card deleted successfully."})
        return jsonify({"error": "Gift card not found."})

    @staticmethod
    def update_giftcard(giftcard_id, data):
        """
        Update a giftcard record in the database.
        """
        my_query = {"id": giftcard_id}
        updated_giftcard = giftcards.find_one_and_update(
            my_query, {"$set": data})
        new_giftcard = giftcards.find_one(my_query)
        print(new_giftcard)
        if updated_giftcard:
            return json.loads(json_util.dumps({"result": new_giftcard})), 200

        return jsonify({"error": "Failed to update giftcard. Try again, please."}), 401

    def create_giftcard(self, data):
        """
        Create a giftcard record.
        """

        secret_code = self.id_generator()
        print(secret_code)

        giftcard = {
            "id": uuid.uuid4().hex,
            "creation_timestamp": datetime.datetime.now(),
            "status": "UNPAID",
            "secret_code":secret_code,
            **data
        }

        new_giftcard = giftcards.insert_one(giftcard)

        if new_giftcard:
            inserted_giftcard = self.retrieve_giftcard_by_uuid(giftcard["id"])
            return json.loads(json_util.dumps({"result": inserted_giftcard})), 200
        return jsonify({"error": "Failed to add giftcard. Try again, please."}), 401
    
    @staticmethod
    def confirm_giftcard_payment(giftcard_id, customer_id):
        giftcard = giftcards.find_one({"id": giftcard_id})
        if giftcard:
            giftcards.find_one_and_update( {"id": giftcard_id}, {"$set": {"status": "PAID"}})

            if giftcard['email'] is not None:
                Notifications().send_giftcard_email(email=giftcard['email'], gifter_name=giftcard['gifter_name'], gifted_name=giftcard['gifted_name'], giftcard_id=giftcard['id'],giftcard_code=giftcard['secret_code'])
            
            customer = customers.find_one({'id': customer_id})
            fcm_token = customer.get('fcm_token')

            if fcm_token:
                Notifications.send_single_notifications(
                    fcm_token=fcm_token,
                    title="Gift Card Payment Successful",
                    body="Hello " + customer['first_name'] + " your gift card payment was successful.")
            else: 
                fcm_token = customer.get('fcm token')
                print(fcm_token)
                Notifications.send_single_notifications(
                    fcm_token=fcm_token,
                    title="Gift Card Payment Successful",
                    body="Hello " + customer['first_name'] + " your gift card payment was successful.")
                
            return jsonify({"success": "Payment confirmed"}), 200
        else: 
            return jsonify({"error": "Gift card not found"}), 400

    @staticmethod
    def make_rwanda_payment(number, amount, giftcard_id,email, customer_Id):
            country_code = "250"
            url = "https://opay-api.oltranz.com/opay/paymentrequest"

            request_body = {
                "telephoneNumber": country_code + str(number),
                "amount": int(amount),
                "organizationId": "ef4668f8-1bc0-4a9c-abf0-741aad737e99",
                "description": "Piyata Gift Card",
                "callbackUrl": "https://testing-piyata-app-backend-418cd9ca0934.herokuapp.com/api/giftcards/rwanda/payment-callback/"+giftcard_id+"/"+email,
                "transactionId": uuid.uuid4().hex
            }
           
            headers = {
                "User-Agent": "Custom",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Content-Length": "290"}
            x = requests.post(url, json=request_body, headers=headers)

            if x.status_code == 200:
                ok = x.text.split('"status":')[1]
                status = ok.split(',')[0]
                status = status.split('}')[0]
                # Check payment success status and record transaction in DB
                transaction = {
                    "type": "PAYMENT",
                    "id": request_body['transactionId'],
                    "order_id": giftcard_id,
                    "amount": amount,
                    "date": datetime.datetime.now(),
                    "callbackObject": x.text,
                    "customer_id": customer_Id,
                    "api_name": "Opay",
                    "country": "RW",
                    "status": status,
                    "service_name": "Gift Card"
                }
                transactions.insert_one(transaction)
                return jsonify({"success": "Payment request successful."}), 200
            else: 
                return jsonify({"error": "Failed to request payment. Please, try again."}), 400
       
    
    def rwanda_payment_callback(self,giftcard_id, email):

        giftcard = giftcards.find_one({"id":giftcard_id})
        print(giftcard)

        if giftcard is not None:
            giftcards.find_one_and_update({"id":giftcard_id},{"$set": {"status": "ACTIVE"}})
            if email is not None:
                Notifications().send_giftcard_email(email=email, gifter_name=giftcard['gifter_name'], gifted_name=giftcard['gifted_name'], giftcard_id=giftcard['id'],giftcard_code=giftcard['secret_code'])

            
            updated_giftcard = self.retrieve_giftcard_by_uuid(giftcard_id)
            return json.loads(json_util.dumps({"result": updated_giftcard})), 200
        else: 
            return jsonify({"error": "Gift card not found"}), 400
        
    
    @staticmethod
    def id_generator(size=6, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
        return ''.join(random.choice(chars) for _ in range(size))