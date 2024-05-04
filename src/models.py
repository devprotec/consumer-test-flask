"""
Contains model instances corresponding to database records for the Piyata Consumer App.
The entry attributes are described in the design docs.
"""

__author__ = "Paterne Iradukunda"
__copyright__ = "Copyright 2023, Piyata"

import json
import os
from bson import json_util
from flask import jsonify, session, redirect, request
from flask_mail import Message
from . import mail
import datetime
import uuid
import re
from werkzeug.security import generate_password_hash, check_password_hash
from dateutil.relativedelta import relativedelta
import requests
from twilio.rest import Client

from src import mongo_client

account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
twilio_verify_sid = os.environ.get('TWILIO_VERIFY_SID')
auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)
env = os.environ.get('FLASK_ENV')
require_verified_services = os.environ.get('REQUIRE_APPROVED_SERVICES')


if env == 'production':
    businesses = mongo_client.piyata_mobile_app_production.businesses
    customers = mongo_client.piyata_mobile_app_production.customers
    images = mongo_client.piyata_mobile_app_production.images
    orders = mongo_client.piyata_mobile_app_production.orders
    services = mongo_client.piyata_mobile_app_production.services
    reviews = mongo_client.piyata_mobile_app_production.reviews
    transactions = mongo_client.piyata_mobile_app_production.transactions
    giftcards = mongo_client.piyata_mobile_app_production.giftcards
    messages  = mongo_client.piyata_mobile_app_production.messages
    staffs = mongo_client.piyata_mobile_app_production.staffs
    promotions = mongo_client.piyata_mobile_app_production.promotions
else:
    businesses = mongo_client.piyata_mobile_app_testing.businesses
    customers = mongo_client.piyata_mobile_app_testing.customers
    images = mongo_client.piyata_mobile_app_testing.images
    orders = mongo_client.piyata_mobile_app_testing.orders
    services = mongo_client.piyata_mobile_app_testing.services
    reviews = mongo_client.piyata_mobile_app_testing.reviews
    transactions = mongo_client.piyata_mobile_app_testing.transactions
    giftcards = mongo_client.piyata_mobile_app_testing.giftcards
    messages  = mongo_client.piyata_mobile_app_testing.messages
    staffs  = mongo_client.piyata_mobile_app_testing.staffs
    promotions = mongo_client.piyata_mobile_app_testing.promotions

# services.getIndexes()
# services.drop_index("name_text")
services.create_index([("name", "text"),
                       ("description", "text"),
                       ("price", "text"),
                       ("category", "text")
                       ], name="name_text_description_text_price_text_category_text", weights={
    "name": 1,
    "description": 1,
    "price": 1,
    "category": 1
}, default_language="english", language_override="language")

businesses.create_index([("business_name", "text"),
                         ("description", "text"),
                         ("country", "text"),
                         ("category", "text")
                         ], name="business_name_text_description_text_price_text_category_text", weights={
    "business_name": 2,
    "description": 2,
    "price": 2,
    "category": 2
}, default_language="english", language_override="language")

access_key = os.environ.get('RWANDA_ACCESS_KEY')

# For customers....


class Customer:
    """
    Entry for a Customer Record. Contains the following fields:
        - id: ID number of the customer.
        - first_name: First name of the customer.
        - last_name: Last name of the custoomer.
        - email: Email address of the customer.
        - phone_number: Phone number of the customer.
        - password: Password associated with the account of the customer.
        - age: Age of the customer.
        - image: file name of the profile picture.
        - location: Link to the Google Maps location of the customer or dict of coordinates of the customer's position
        - creation_timestamp: Date and time at which the customer joined the platform.
        - orders: List of orders (IDs) made by customer.
        - online: Indicates the status of the customer, online or not (True or False)
    """

    def google_signup(self, name, email, profile_picture):
        user = {
            "id": uuid.uuid4().hex,
            "first_name": name,
            "last_name": "",
            "email": email,
            "country": None,
            "country_code": None,
            "phone_number": None,
            "birthdate": None,
            "password": None,
            "location": None,
            "creation_timestamp": datetime.datetime.now(),
            "online": True,
            "image": profile_picture,
            "saved_images": [],
            "promo": 0,
            "piyata_points": 0,
            "balance": 0,
            "completed_onboarding":False,
            "role": None
        }
        if customers.find_one({"email": user["email"]}):
            return jsonify({"error": "Email address already in use."}), 401
        # Store customer in database
        if customers.insert_one(user):
            return self.start_session(user)
            # return jsonify({"success": "Signup success!"}), 200
        return jsonify({"error": "Google Signup Failed! Please, try again or contact us."}), 400

    def signup(self, email, password):
        """
        Creating an instance of the business record class (creating a business account on the platform)
        Input:
            - id: ID number of the customer.
            - first_name: First name of the customer.2
            - last_name: Last name of the custoomer.
            - email: Email address of the customer.
            - phone_number: Phone number of the customer.
            - password: Password associated with the account of the customer.
            - age: Age of the customer.
            - image: file name of the profile picture.
            - location: Link to the Google Maps location of the customer or dict of coordinates of the customer's position
            - creation_timestamp: Date and time at which the customer joined the platform.
            - active: Indicates the status of the customer, online or not (True or False)

        Returns:
            A customer record

        """
        # Create the user object...
        user = {
            "id": uuid.uuid4().hex,
            "first_name": None,
            "last_name": None,
            "email": email.lower(),
            "country": None,
            "country_code": None,
            "phone_number": None,
            "birthdate": None,
            "password": password,
            "location": None,
            "creation_timestamp": datetime.datetime.now(),
            "active": True,
            "image": None,
            "saved_images": [],
            "favorite_services": [],
            "promo": 0,
            "piyata_points": 0,
            "balance": 0,
            "completed_onboarding":False,
            "role": None
        }
        # Verifying the email
        if customers.find_one({"email": user["email"]}):
            return jsonify({"error": "Email address already in use."}), 401
        password_criteria = Solution().strongPasswordChecker(user['password'])
        if password_criteria == "":
            user['password'] = generate_password_hash(user['password'])
        else:
            return jsonify({"error": password_criteria}), 401
        # Store customer in database
        if customers.insert_one(user):
            return self.start_session(user)
            # return jsonify({"success": "Signup success!"}), 200
        return jsonify({"error": "Signup Failed! Please, try again or contact us."}), 400

    def contact_signup(self, phone_number, password):
        """
        Creating an instance of the business record class (creating a business account on the platform)
        Input:
            - id: ID number of the customer.
            - first_name: First name of the customer.
            - last_name: Last name of the customer.
            - email: Email address of the customer.
            - phone_number: Phone number of the customer.
            - password: Password associated with the account of the customer.
            - age: Age of the customer.
            - image: file name of the profile picture.
            - location: Link to the Google Maps location of the customer or dict of coordinates of the customer's position
            - creation_timestamp: Date and time at which the customer joined the platform.
            - active: Indicates the status of the customer, online or not (True or False)

        Returns:
            A customer record

        """
        # Create the user object...
        user = {
            "id": uuid.uuid4().hex,
            "first_name": None,
            "last_name": None,
            "email": None,
            "country": None,
            "country_code": None,
            "phone_number": phone_number,
            "birthdate": None,
            "password": password,
            "location": None,
            "creation_timestamp": datetime.datetime.now(),
            "active": True,
            "image": None,
            "saved_images": [],
            "promo": 0,
            "piyata_points": 0,
            "balance": 0,
            "completed_onboarding":False,
            "role": None
        }
        # Verifying the email
        if customers.find_one({"phone_number": user["phone_number"]}):
            return jsonify({"error": "Phone number already in use."}), 401
        password_criteria = Solution().strongPasswordChecker(user['password'])
        if password_criteria == "":
            user['password'] = generate_password_hash(user['password'])
        else:
            return jsonify({"error": password_criteria}), 401
        # Store customer in database
        if customers.insert_one(user):
            return self.start_session(user)
            # return jsonify({"success": "Signup success!"}), 200
        return jsonify({"error": "Signup Failed! Please, try again or contact us."}), 400

    def continue_with_apple(self, id):
        user = {
            "id": id,
            "first_name": None,
            "last_name": None,
            "email": None,
            "country": None,
            "country_code": None,
            "phone_number": None,
            "birthdate": None,
            "password": None,
            "location": None,
            "creation_timestamp": datetime.datetime.now(),
            "active": True,
            "image": None,
            "saved_images": [],
            "promo": 0,
            "piyata_points": 0,
            "balance": 0,
            "completed_onboarding":False,
            "role": None,
        }
        # Verifying the id
        customer = customers.find_one({"id": id})
        if customer:
            return self.start_session(customer)
        else:
            # Store customer in database
            if customers.insert_one(user):
                return self.start_session(user)
                # return jsonify({"success": "Signup success!"}), 200
            return jsonify({"error": "Signup Failed! Please, try again or contact us."}), 400

    def start_session(self, user):
        del user['password']
        session['logged_in'] = True
        session['user'] = user
        try:
            user['_id'] = json.loads(json_util.dumps(user['_id']))
            user = json.loads(json_util.dumps(user))
            return jsonify(user), 200
        except ImportError as error:
            return jsonify({"error": "{}".format(error)}), 401

    def logout(self):
        session.clear()
        return redirect('/')

    def login(self, email, password):
        customer = customers.find_one({"email": email.lower()})
        if customer and customer['password'] == None:
            return jsonify({"error": "Click on 'Forgot Password' to create a new password."}), 401

        if customer and check_password_hash(customer['password'], password):

            return self.start_session(customer)
        return jsonify({"error": "Wrong email or password. Try again, please."}), 401

    def login_with_contact(self, phone_number, password):
        customer = customers.find_one({"phone_number": phone_number})
        if customer and customer['password'] == None:
            return jsonify({"error": "Click on 'Forgot Password' to create a new password."}), 401

        if customer and check_password_hash(customer['password'], password):
            return self.start_session(customer)
        return jsonify({"error": "Wrong number or password. Try again, please."}), 401

    def login_without_password(self, phone_number):
        customer = customers.find_one({"phone_number": phone_number})
        if customer:
            return self.start_session(customer)
        return jsonify({"error": "Phone number does not exist"}), 401

    def google_login(self, email):
        customer = customers.find_one({"email": email.lower()})
        if customer:
            return self.start_session(customer)
        return jsonify({"error": "Failed to log-in. Try again, please."}), 401

    @staticmethod
    def reset_password(password, customerId):
        password_hash = generate_password_hash(password)
        customer = customers.find_one({"id": customerId})
        if customer:
            customers.find_one_and_update(
                {"id": customerId}, {'$set': {"password": password_hash}})
            return jsonify({'success': 'Password Reset Successful'}), 200
        return jsonify({'error': 'user not found'}), 401

    @staticmethod
    def reset_email_password(password, customer_email):
        password_hash = generate_password_hash(password)
        customer = customers.find_one({"email": customer_email})
        if customer:
            customers.find_one_and_update(
                {"email": customer_email}, {'$set': {"password": password_hash}})
            return jsonify({'success': 'Password Reset Successful'}), 200
        return jsonify({'error': 'user not found'}), 401

    @staticmethod
    def reset_contact_password(password, customer_number):
        password_hash = generate_password_hash(password)
        customer = customers.find_one({"phone_number": customer_number})
        if customer:
            customers.find_one_and_update(
                {"phone_number": customer_number}, {'$set': {"password": password_hash}})
            return jsonify({'success': 'Password Reset Successful'}), 200
        return jsonify({'error': 'user not found'}), 401

    @staticmethod
    def deleteAccount(customer_id):
        customer = customers.find_one({"id": customer_id})
        deleted_fields = {
            "first_name": None,
            "last_name": None,
            "email": None,
            "country": None,
            "country_code": None,
            "phone_number": None,
            "birthdate": None,
            "password": None,
            "location": None,
            "creation_timestamp": None,
            "active": None,
            "status": "deleted",
            "image": None,
            "saved_images": None,
            "favorite_services": None,
            "promo": None,
            "piyata_points": None,
            "balance": None,
            "fcm_token": None,
            "gender": None,
            "notification_settings": None,
        }
        if customer:
            customers.find_one_and_update(
                {"id": customer_id}, {'$set': deleted_fields})

            return jsonify({"success": "customer deleted successfully"}), 200
        return jsonify({"error": "customer not found"}), 401

    @staticmethod
    def request_password_reset_email(email):
        customer = customers.find_one({"email": email})
        if customer:
            return jsonify({'success': 'User account found'}), 200
        return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}), 400

    @staticmethod
    def reset_password_error():
        return jsonify({"error": "No user account found with that email.\nTry again or create a new account."}), 401

    @staticmethod
    def retrieve_customer_by_uuid(id: str):
        my_query = {"id": id}
        customer = customers.find_one(my_query)
        if customer is None:
            return jsonify({"error": "user not found"}), 400
        return customer

    @staticmethod
    def request_password_reset_otp(phone_number):
        customer = customers.find_one({"phone_number": phone_number})
        if customer:
            full_phone_number = customer['country_code']+phone_number
            try:
                verification = client.verify \
                        .v2 \
                        .services(twilio_verify_sid) \
                        .verifications \
                        .create(to=full_phone_number, channel='sms') 

                if verification.status == "pending": 
                        return jsonify({'success':'Verification code sent successfully'}), 200
            except Exception as e:
                print("The error is: Twilio otp error",e)
                return jsonify({'error':'Cannot request password reset at this time'}), 401
        return jsonify({"error": "No user account found with this phone number.\nTry again or create a new account."}), 401
    
    @staticmethod
    def verify_otp(code, phone_number):
        customer = customers.find_one({"phone_number": phone_number})
        if customer:
            full_phone_number = customer['country_code']+phone_number
            try:
                verification_check = client.verify \
                                .v2 \
                                .services(twilio_verify_sid) \
                                .verification_checks \
                                .create(to=full_phone_number, code=code)
                print(verification_check.status)
            
                if(verification_check.status == 'approved'):
                    return jsonify({'success': 'Verification Success','customer_id':customer['id']}), 200
                return jsonify({'error': 'Invalid token or token expired'}), 401
            except:
                return jsonify({'error': 'Invalid token or token expired'}), 401
        return jsonify({'error':'user not found'}), 401

    @staticmethod
    def retrieve_customer_by_email(email: str):
        my_query = {"email": email}
        customer = customers.find_one(my_query)
        if customer is None:
            return jsonify({"error": "user not found"}), 400
        return customer

    def update_customer_profile_image(self, customer, image):
        id = customer["id"]
        if customers.find_one_and_update({"id": id}, {'$set': {"image": image["url"]}}):
            updated_customer = self.retrieve_customer_by_uuid(id)
            return json.loads(json_util.dumps({"result": updated_customer})), 200

    def update_customer_account_information(self, customer, data):
        """"
        Update the customer account information
        """
        if isinstance(customer, str):
            return jsonify({"error": customer}), 401
        id = customer["id"]
        update = customers.update_one({"id": id}, {'$set': data})
        if update:
            updated_customer = self.retrieve_customer_by_uuid(id)
            return json.loads(json_util.dumps({"result": updated_customer})), 200
        return jsonify({"error": "Failed to update your account information. Try again, please."}), 401

    def pay_business(self, order_id):
        order = orders.find_one({'id': order_id})
        # business = businesses.find_one({'id':order['business_id']})
        if not order['paid_business']:
            country_code = "25"
            url = "https://opay-api.oltranz.com/opay/wallet/fundstransfer"
            # print(country_code + order['business_phone'])
            amount = int(float(order['price']) + 
                         ((float(2.5)*float(order['price']))/100))
            # print(price)
            request_body = {
                "merchantId": "ef4668f8-1bc0-4a9c-abf0-741aad737e99",
                "receiverAccount": country_code + order['business_phone'], 
                "type": "MOBILE",
                "transactionId": uuid.uuid4().hex,
                "amount": amount,
                "callbackUrl": "https://piyata.herokuapp.com/api/payment-callback/",
                "description": "FUNDS TRANSFER TEST",
                "firstName": order['customer_names'].split(" ")[0],
                "lastName": order['customer_names'].split(" ")[1] 
            }

            headers = {
                "User-Agent": "Custom",
                "Content-Type": "application/json",
                "accessKey": access_key,
                "Accept": "application/json",
                "Content-Length": "290"}

            x = requests.post(url, json=request_body, headers=headers)
            ok = x.text.split('"status":')[1]
            status = ok.split(',')[0]
            status = str(status.split('}')[0])

            if x.status_code == 200:
                transaction = {
                    "type": "PAYOUT",
                    "type": "PAYOUT",
                    "id": request_body['transactionId'],
                    "order_id": order_id,
                    "amount": request_body['amount'],
                    "date": datetime.datetime.now(),
                    "callbackObject": x.text,
                    "status": status,
                    "service_name":order['service_name'],
                }
                transactions.insert_one(transaction)

            return status
        else:
            return "<script>window.alert('Payment is being processed or already completed.');</script>"

    def request_payment(self, order, customer, order_id, service_fee):
        if request.method == "POST" or "GET":
            # booking_fee = 5
            # price = int(price)
            country_code = "250"
            url = "https://opay-api.oltranz.com/opay/paymentrequest"
            request_body = {
                "telephoneNumber": country_code + customer['phone_number'],
                "amount": service_fee,
                "organizationId": "ef4668f8-1bc0-4a9c-abf0-741aad737e99",
                "description": "Service booking fee.",
                "callbackUrl": "https://protected-castle-83558-9440440948bf.herokuapp.com/api/payment-callback/",
                "transactionId": uuid.uuid4().hex
            }
            headers = {
                "User-Agent": "Custom",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Content-Length": "290"}
            
            x = requests.post(url, json=request_body, headers=headers)
            # Check payment success status and record transaction in DB
            if x.status_code == 200:
                ok = x.text.split('"status":')[1]
                status = ok.split(',')[0]
                status = status.split('}')[0]
                transaction = {
                    "type": "PAYMENT",
                    "type": "PAYMENT",
                    "id": request_body['transactionId'],
                    "order_id": order_id,
                    "amount": request_body['amount'],
                    "date": datetime.datetime.now(),
                    "api_name": "Opay",
                    "country": customer["country"],
                    "customer_id": order["customer_id"],
                    "callbackObject": x.text,
                    "status": status,
                    "service_name": order['service_name'],
                    "service_name": order['service_name']
                }
                print(x.json)
                transactions.insert_one(transaction)
                return order
            else:
                return {"error": "Failed to request payment. Please, try again."}
        else:
            return {"error": "Failed to request payment."}
        
    def reward_referrrer(self, referral_code, piyata_points, balance_equivalent):
        referral_code = str(referral_code).lower
        agent = customers.find_one({"referral.personal_code": referral_code})
        
        if agent is not None:
            referral = agent['referral']
            balance = agent['balance']

            if(balance is None):
                balance = 0 + float(balance_equivalent)
            else:
                balance = float(balance) + float(balance_equivalent)

            if referral is not None:
                referral['referral_count'] += 1
                referral['earned_piyata_points'] += float(piyata_points)
                customers.update_one({"referral.personal_code": referral_code}, {'$set': {"referral": referral, "balance": balance}})
                updated_agent = customers.find_one({"referral.personal_code": referral_code})
                return json.loads(json_util.dumps(updated_agent)), 200
            else:
                referral = {
                    "referral_count": 1,
                    "earned_piyata_points": piyata_points,
                    "personal_code": referral_code
                }
                customers.update_one({"referral.personal_code": referral_code}, {'$set': {"referral": referral, "balance": balance}})
                updated_agent = customers.find_one({"referral.personal_code": referral_code})
                return json.loads(json_util.dumps(updated_agent)), 200
        else:
            return jsonify({"error": "Agent not found."}), 200


        



class Business:
    @staticmethod
    def retrieve_business_by_uuid(id: str):
        my_query = {"id": id}
        business = businesses.find_one(my_query)
        if business is None:
            return "Business account not found."
        return business

    @staticmethod
    def retrieve_business_by_name(id: str):
        my_query = {"business_name": id}
        business = businesses.find_one(my_query)
        if business is None:
            return "Business account not found."
        return business

    @staticmethod
    def retrieve_all_businesses():
        all_business = businesses.find()
        return json.loads(json_util.dumps(all_business))

    @staticmethod
    def filter_businesses(data):

        filtered_businesses = []
        businesses_with_services = []

        if(data.get('category')):
            category = [data.get('category')]
            filtered_businesses = businesses.find(
                {
                "status": {"$in": ["ACTIVE", "INACTIVE"]},
                "service_categories": {"$in": category},
                "account_verification.status": {"$in": ["VERIFIED", "UNVERIFIED", "PENDING"]},
                "country": data['country']}).sort(
            [('rating', -1), ('reviews', -1)])
        else: 
            filtered_businesses = businesses.find(
                {
                "status": {"$in": ["ACTIVE", "INACTIVE"]},
                "account_verification.status": {"$in": ["VERIFIED", "UNVERIFIED", "PENDING"]},
                "country": data['country']}).sort(
            [('rating', -1), ('reviews', -1)])
       
        for business in filtered_businesses:
            business_id = business.get("id")
            
            if require_verified_services == "True":
                if services.find_one({"business_id": business_id, "online": True,  "verification_status" :"APPROVED"}):
                    businesses_with_services.append(business)
            else:
                if services.find_one({"business_id": business_id, "online": True}):
                    businesses_with_services.append(business)
     
        if (data.get("rating")):
            rating = data.get("rating")
            businesses_with_services = [
                business for business in businesses_with_services if business.get("rating") >= rating]
            
        return json.loads(json_util.dumps(businesses_with_services))
  
  
    @staticmethod
    def deleteAccount(business_id):
        business = businesses.find_one({"id": business_id})
        deleted_fields = {
            "first_name": None,
            "last_name": None,
            "email": None,
            "country_code": None,
            "country": None,
            "service_categories": None,
            "business_name": None,
            "staff_size": None,
            "momo_number": None,
            "phone_number": None,
            "birthdate": None,
            "password": None,
            "address": None,
            "momo_limit": None,
            "location": None,
            "creation_timestamp": None,
            "image": None,
            "saved_images": None,
            "schedule": None,
            "cover_image": None,
            "rating": None,
            "reviews": None,
            "promo": None,
            "pending_balance": None,
            "balance": None,
            "account_verification": None,
            "momo_network_code":  None,
            "payment_code": None,
            "momo_name": None,
            "status": "DELETED",
            "service_folders": None,
            "customer_demographics":None,
            "payment_methods": None,
            "notification_settings":None,
            "owner_name" : None,
            "start_year" : None,
            "gender": None,
            "fcm_token":None,
            "completed_onboarding":False,

        }
        if business:
            services.delete_many({"business_id": business_id})
            businesses.find_one_and_update({"id": business_id}, {'$set': deleted_fields})

            return jsonify({"success": "business deleted successfully"}), 200
        return jsonify({"error": "business not found"}), 401
  
  
  
    @staticmethod
    def deleteAccount(business_id):
        business = businesses.find_one({"id": business_id})
        deleted_fields = {
            "first_name": None,
            "last_name": None,
            "email": None,
            "country_code": None,
            "country": None,
            "service_categories": None,
            "business_name": None,
            "staff_size": None,
            "momo_number": None,
            "phone_number": None,
            "birthdate": None,
            "password": None,
            "address": None,
            "momo_limit": None,
            "location": None,
            "creation_timestamp": None,
            "image": None,
            "saved_images": None,
            "schedule": None,
            "cover_image": None,
            "rating": None,
            "reviews": None,
            "promo": None,
            "pending_balance": None,
            "balance": None,
            "account_verification": None,
            "momo_network_code":  None,
            "payment_code": None,
            "momo_name": None,
            "status": "DELETED",
            "service_folders": None,
            "customer_demographics":None,
            "payment_methods": None,
            "notification_settings":None,
            "owner_name" : None,
            "start_year" : None,
            "gender": None,
            "fcm_token":None,
            "completed_onboarding":False,

        }
        if business:
            services.delete_many({"business_id": business_id})
            businesses.find_one_and_update({"id": business_id}, {'$set': deleted_fields})

            return jsonify({"success": "business deleted successfully"}), 200
        return jsonify({"error": "business not found"}), 401
  
    
    @staticmethod
    def retrieve_business_by_uuid(id: str):
        my_query = {"id": id}
        business = businesses.find_one(my_query)
        if business is None:
            return jsonify({"error": "user not found"}), 400
        return business
    
    def update_business_account_information(self, business, data):
        """"
        Update the business account information
        """
        if isinstance(business, str):
            return jsonify({"error": business}), 401
        id = business["id"]
        update = businesses.update_one({"id": id}, {'$set': data})
        if update:
            updated_business = self.retrieve_business_by_uuid(id)
           
            return json.loads(json_util.dumps({"result": updated_business})), 200
        return jsonify({"error": "Failed to update your account information. Try again, please."}), 401


class Services:
    # Returns a list of dict type object(s) of Service record from the database with the given parameter.
    @staticmethod
    def retrieve_service_by_uuid(id: str):
        my_query = {"id": id}
        service = services.find_one(my_query)
        if service is None:
            return "Service not found."
        return service

    @staticmethod
    def retrieve_service_by_price(price: float):
        my_query = {"price": price}
        service = services.find_one(my_query)
        if service is None:
            return "Services of specified price not found."
        return service

    @staticmethod
    def retrieve_service_by_name(name: str):
        my_query = {"name": name}
        service = services.find_one(my_query)
        if service is None:
            return "Service not found."
        return service

    @staticmethod
    def retrieve_services_by_duration(duration: int):
        my_query = {"duration": duration}
        service = services.find(my_query)
        if service is None:
            return "Services of specified duration not found."
        return service

    @staticmethod
    def retrieve_services_by_business_id(business_id: int):
        my_query = {"business_id": business_id}
        service = services.find(my_query)
        if service is None:
            return "This business has no services currently."
        return service
    
    @staticmethod
    def update_service(service_id, data):
        # Check if service record exists in database.
        my_query = {"id": service_id}
        updated_service = services.find_one_and_update(
            my_query, {"$set": data})
        new_service = services.find_one(my_query)
        if updated_service:
            return new_service, 200
        return jsonify({"error": "Failed to unpublish service. Try again, please."}), 401

    @staticmethod
    def retrieve_business_services_by_business_id(id: str):
        my_query = {"business_id": id}
        service = services.find(my_query)
        if service is None:
            return jsonify({"error": "user not found"}), 400
        return service

    def update_service_information(self, business_id, data):
        """"
        Update the business account information
        """
        my_query = {"id": business_id}
        business = businesses.find_one(my_query)
        if business is None:
            return jsonify({"error": "Business not found"}), 400
        
        update = services.update_many({"business_id": business_id}, {'$set': data})
        if update:
            print(update)
            updated_business = self.retrieve_business_services_by_business_id(business_id)
            return json.loads(json_util.dumps({"result": updated_business})), 200
        return jsonify({"error": "Failed to update business service information. Try again, please."}), 401

    @staticmethod
    def retrieve_pending_or_reported_service_by_uuid(id: str):
        my_query = {"id": id}
        service = services.find_one(my_query)
        if service is None:
            return jsonify({"error": "user not found"}), 400
        return service
    
    def update_pending_or_reported_service(self, service, data):
        """"
        Update the business account information
        """
        if isinstance(service, str):
            return jsonify({"error": service}), 401
        id = service["id"]
        update = services.update_one({"id": id}, {'$set': data})
        if update:
            updated_service = self.retrieve_pending_or_reported_service_by_uuid(id)
            return json.loads(json_util.dumps({"result": updated_service})), 200
        return jsonify({"error": "Failed to update service information. Try again, please."}), 401

    @staticmethod
    def filter_services(data):
        filtered_services = []
        if (data.get('category')):
            category = [data.get('category')]
            filtered_services = services.find({"online": True, "currency": data["currency"], "category":{"$in": category},})
        else:
            filtered_services = services.find({"online": True, "currency": data["currency"]})
        if (data.get("min_price")):
            filtered_services = [
                service for service in filtered_services if float(service["price"]) >= float(data["min_price"])]
        if (data.get("max_price")):
            filtered_services = [
                service for service in filtered_services if (float(service["price"])*(1.1)) <= float(data["max_price"])]
        if (data.get("rating")):
            filtered_services = [
                service for service in filtered_services if service["rating"] >= data["rating"]]
        if(require_verified_services == "True"):
            filtered_services = [
                service for service in filtered_services if service.get("verification_status") =="APPROVED"]

        return json.loads(json_util.dumps(filtered_services))

    @staticmethod
    def retrieve_all_services():
        all_services = services.find()
        return json.loads(json_util.dumps(all_services),)

    @staticmethod
    def retrieve_services_using_business_id(business_id):
        """
        Get all services of a business
        """
        # my_query = {"business_id": business_id}
        # business_services = services.find(my_query)
        all_services = services.find()
        business_services = [
            service for service in all_services if service["business_id"] == business_id]

        print(business_services)
        if business_services:
            return json.loads(json_util.dumps(business_services))
        return jsonify({"Error": "Services not found."})


class Transaction:
    @staticmethod
    def retrieve_transaction_by_uuid(id: str):
        my_query = {"id": id}
        transaction = transactions.find_one(my_query)
        if transaction is None:
            return "Transaction not found."
        return transaction

    @staticmethod
    def retrieve_transaction_by_order_id(id: str):
        my_query = {"order_id": id}
        transaction = transactions.find_one(my_query)
        if transaction is None:
            return "Transaction not found."
        return transaction
    
    def add_transaction(self, data):
        """
        Create a transaction record.
        """

        transaction = {
            "date": datetime.datetime.now(),
            **data
        }

        new_transaction = transactions.insert_one(transaction)
        if new_transaction:
            inserted_transaction = self.retrieve_transaction_by_uuid(transaction["id"])
            return json.loads(json_util.dumps({"result": inserted_transaction})), 200
        return jsonify({"error": "Failed to add transaction. Try again, please."}), 401
    


class Orders:
    @staticmethod
    def retrieve_order_by_uuid(id: str):
        my_query = {"id": id}
        order = orders.find_one(my_query)
        if order is None:
            return "Order not found."
        return order

    @staticmethod
    def retrieve_order_by_serviceId(id: str):
        my_query = {"service_id": id}
        order = orders.find_one(my_query)
        if order is None:
            return "Order not found."
        return order
    
    def update_customer_order_information(self, order, data):
        """"
        Update the customer order information
        """
        if isinstance(order, str):
            return jsonify({"error": order}), 401
        id = order["id"]
        update = orders.update_one({"id": id}, {'$set': data})
        if update:
            updated_order = self.retrieve_order_by_uuid(id)
            return json.loads(json_util.dumps({"result": updated_order})), 200
        return jsonify({"error": "Failed to update your order information. Try again, please."}), 401


class ImagesDatabaseClient:
    """"
    Entry for an Image Record. Contains the following fields:
        - id: ID number of the image.
        - email: Email address of the customer.
        - url: URL of the image.
        - phone_number: Phone number of the customer.
    """
    @staticmethod
    def retrieve_image_by_uuid(id: str):
        my_query = {"id": id}
        image = images.find_one(my_query)
        if image is None:
            return "Service not found."
        return image

    @staticmethod
    def retrieve_image_by_email(email: str):
        my_query = {"email": email}
        image = images.find_one(my_query)
        if image is None:
            return "Image not found."
        return image

    @staticmethod
    def retrieve_all_images(self):
        return images.find()

    @staticmethod
    def delete_image_by_id(id):
        # Check if service record exists in database.
        my_query = {"_id": id}
        image = images.find(my_query)

        if image is None:
            return "Image not found."

        images.delete_one(my_query)
        return "Image deleted successfully."


class Review:
    def store_review_record(self, customer):
        customer_id = customer["id"]
        if customers.find_one({"id": customer_id}):
            review = {
                "id": uuid.uuid4().hex,
                "customer_id": customer_id,
                "customer_first_name": customer["first_name"],
                "customer_last_name": customer["last_name"],
                "service_id": request.form.get("service_id"),
                "service_name": request.form.get("service_name"),
                "business_id": request.form.get("business_id"),
                "rating": float(request.form.get("rating")),
                "status": "PENDING",
                "likes": 0,
                "images_url": [],
                "title": request.form.get("title"),
                "description": request.form.get("description"),
                "creation_timestamp": datetime.datetime.now(),
            }
            reviews.insert_one(review)
        return jsonify({"result": "Review submitted successfully."}), 200
    
    @staticmethod
    def approve_review(review_id):
        review = reviews.find_one({"id": review_id})
        if review is not None:
            # Update the rating of the service
            service = Services().retrieve_service_by_uuid(review["service_id"])
            if service is not None:
                average_rating = service['rating']
                number_of_reviews = service['reviews']
                if average_rating is None or average_rating == 0:
                    average_rating = float(review.get("rating"))
                if number_of_reviews == 0 or number_of_reviews == "None":
                    number_of_reviews = 0
                average_rating = (float(review.get("rating")) + average_rating)/2
                number_of_reviews = number_of_reviews + 1
                services.find_one_and_update({"id": review.get("service_id")}, {
                                            '$set': {"rating": average_rating}})
                services.find_one_and_update({"id": review.get("service_id")}, {
                                            '$set': {"reviews": number_of_reviews}})
            
            business = Business().retrieve_business_by_uuid(review["business_id"])
            if business is not None:
                business_average_rating = business['rating']
                business_number_of_reviews = business['reviews']
                if business_average_rating is None or business_average_rating == 0:
                    business_average_rating = float(review.get("rating"))
                if business_number_of_reviews == 0 or business_number_of_reviews == "None":
                    business_number_of_reviews = 0
                business_average_rating = (
                    float(review.get("rating")) + business_average_rating)/2
                business_number_of_reviews = business_number_of_reviews + 1
                businesses.find_one_and_update({"id": review.get("business_id")}, {
                    '$set': {"rating": business_average_rating}})
                businesses.find_one_and_update({"id": review.get("business_id")}, {
                    '$set': {"reviews": business_number_of_reviews}})
            reviews.find_one_and_update({"id": review_id}, {'$set': {"status": "APPROVED"}})
            return jsonify({"message": "Review approved."}), 200
        else:
            return jsonify({"message": "Review not found."}), 401
        

    
    @staticmethod
    def retrieve_review_by_uuid(id: str):
        my_query = {"id": id}
        review = reviews.find_one(my_query)
        if review is None:
            return "Review not found."
        return review


# Password checker
class Solution(object):
    def strongPasswordChecker(self, password):
        error = ""
        # check the length of the password
        if len(password) < 6:
            error += " Password must have at least 6 characters."
        # searching for digits
        if re.search(r"\d", password) is None:
            error += " Password must have at least one digit."
        # searching for uppercase
        if re.search(r"[A-Z]", password) is None:
            error += " Password must have at least one uppercase letter."
        # searching for lowercase
        if re.search(r"[a-z]", password) is None:
            error += " Password must have at least one lowercase letter."
        # searching for symbols
        if re.search(r"\W", password) is None:
            error += " Password must have at least one special character"
        return error