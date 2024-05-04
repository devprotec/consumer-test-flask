from .models import messages
from flask import jsonify ,request
import json
from bson import json_util
import uuid
import datetime
import pymongo
from .models import businesses
class Messages:
    '''
    This class models the messages sent between Piyata and Businesses

        - id: The unique identifier of the message
        - sender_id: The user who sent the message (Piyata or Business)
        - sender_name: The name of the user who sent the message (Piyata or Business)
        - sender_email: The email of the user who sent the message (Piyata or Business)
        - recipient_id: The ID user who received the message (Piyata or Business)
        - recipient_name: The name of the user who received the message (Piyata or Business)
        - recipient_email: The email of the user who received the message (Piyata or Business)
        - body: The actual message sent between the sender and receiver
        - subject: The subject of the message
        - Date: The date and time when the message was sent,
        - recipient_type: The type of message that will be sent to (many or one) recipient
    '''

    @staticmethod
    def retrieve_message_by_uuid(message_id):
        """
        Retrieve a message record from the database.
        """
        my_query = {"id": message_id}
        giftcard = messages.find_one(my_query)
        if giftcard is None:
            return jsonify({"error": "Gift card not found"}), 401
        return giftcard


    def create_message(self, data):
        """
        Create a message record.
        """

        message = {
            "id": uuid.uuid4().hex,
            "date": datetime.datetime.now(),
            **data
        }
        new_message = messages.insert_one(message)

        if(new_message):
            new_message = self.retrieve_message_by_uuid(message["id"])
            return jsonify({"Success":"Email Message Sent Successfully"}), 200
            # return json.loads(json_util.dumps({"result": new_message})), 200
        else:
            return jsonify({"Error": "Failed to create message"}), 401

    @staticmethod
    def delete_message(message_id):
        """
        Delete a message record from the database.
        """
        my_query = {"id": message_id}
        deleted_message = messages.delete_one(my_query)
        if deleted_message.deleted_count == 1:
            return jsonify({"success": "Message deleted successfully."})
        return jsonify({"error": "Message not found"})

    @staticmethod
    def get_all_messages_by_business(business_id):
        """
        Retrieve all messages by a business from the database.
        """
        my_query = {"$or":[{"sender_id": business_id},{"recipient_id":business_id}]}
        all_messages = messages.find(my_query).sort([("date", pymongo.DESCENDING)])
        if messages is None:
            return jsonify({"error": "Messages not found"}), 401
        return json.loads(json_util.dumps({"result": all_messages})), 200
    @staticmethod
    def get_all_message_by_recipient_type(country,verification_status):
        """
        Retrieve all message where recipient_type is MANY
        """
        my_query={"$and":[{"recipient_type":"MANY"},{"business_country":country},{"business_status":verification_status}]}
        data_messages=messages.find(my_query).sort([("date", pymongo.DESCENDING)])
        if messages is None:
            return jsonify({"Error":"Messages not found"}),401
        return json.loads(json_util.dumps({"result":data_messages})), 200

    @staticmethod
    def get_messages_sent_all_bussiness():
        """
        Retrieve all messages sent to all bussinesses from the database.
        """
        data_messages=messages.find({"recipient_type":"ALL"}).sort([("date", pymongo.DESCENDING)])
        if messages is None:
            return jsonify({"Error":"Messages not found"}),401
        return json.loads(json_util.dumps({"messages":data_messages})), 200

    @staticmethod
    def get_paginate_bussiness(page):
        """
        Paginate Businesses and take 10 bussinesses per page
        """
        PER_PAGE = 20
        page_number=int(page)
        skip = (page_number - 1) * PER_PAGE
        cursor_businesses = businesses.find().skip(skip).limit(PER_PAGE)
        if cursor_businesses is None:
            return jsonify({"Error":"Businesses not found"}),401
        return json.loads(json_util.dumps({"businesses":cursor_businesses})), 200

    @staticmethod
    def get_all_messages_customer_by_booking_id(booking_id):
        """
        Retrieve all messages by a business send from customer .
        """
        my_query = {"$and":[{"$or":[{"sender_id": booking_id},{"recipient_id":booking_id}],"recipient_type":"BOOKING"}]}
        all_messages = messages.find(my_query).sort([("date", pymongo.DESCENDING)])
        if messages is None:
            return jsonify({"error": "Messages not found"}), 401
        return json.loads(json_util.dumps({"result": all_messages})), 200