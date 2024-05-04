import os
import json
from flask import jsonify, request, redirect, session
import datetime
import uuid
from bson import json_util
from dateutil.relativedelta import relativedelta

from src.notifications import Notifications

from src.notifications import Notifications
from .models import Business, Services, customers, orders, transactions, businesses
from .models import Customer
import requests
from . import mail
from flask_mail import Message

access_key = os.environ.get('RWANDA_ACCESS_KEY')
paystack_secret = os.environ.get("PAYSTACK_TEST_SECRET_KEY")


class OrderManagement:

    def create_customer_order(self, customer):
        customer_id = customer["id"]
        if customers.find_one({"id": customer_id}):
            data = json.loads(request.data)
            order = {
                "id": uuid.uuid4().hex,
                "customer_id": customer["id"],
                "customer_names": customer['first_name'] + " " + customer['last_name'],
                "customer_phone": customer['phone_number'],
                "service_name": data.get("service_name"),
                "service_id": data.get('service_id'),
                "duration": data.get('duration'),
                "price": data.get("service_price"),
                "service_fee": data.get("service_fee"),
                "description": data.get("service_description"),
                "business_id": data.get('business_id'),
                "business_phone": data.get('business_phone'),
                "start_time": data.get("start_time"),
                "end_time": data.get("end_time"),
                "service_delivery": data.get("service_delivery"),
                "location": data.get("location"),
                "business_name": data.get("business_name"),
                "address": data.get("address"),
                "notes": data.get("note"),
                "date": data.get("date"),
                "creation_timestamp": datetime.datetime.now(),
                "status": "PENDING",
                "country_code": customer['country_code'],
                "paid_business": False,
                "image": data.get('image'),
                "promo": False,
                "payment_url": "",
                "payment_reference": data.get("payment_reference"),
                "staff_id": data.get("staff_id"),
                "add_ons": data.get("add_ons")
            }
            # print(order)
            if customer['country_code'] == "+233":
                orders.insert_one(order)
                return order

            elif customer['country_code'] == "+250":
                orders.insert_one(order)

                return Customer().request_payment(order,
                                                  customer, order['id'], order["service_fee"])
            else:
                return {"error": "Error creating order"}
            

    def create_customer_cashless_order(self, customer):
        customer_id = customer["id"]
        if customers.find_one({"id": customer_id}):
            data = json.loads(request.data)
            # Create and insert order
            order = {
                "id": uuid.uuid4().hex,
                "customer_id": customer["id"],
                "customer_names": customer['first_name'] + " " + customer['last_name'],
                "customer_phone": customer['phone_number'],
                "service_name": data.get("service_name"),
                "service_id": data.get('service_id'),
                "duration": data.get('duration'),
                "price": data.get("service_price"),
                "service_fee": data.get("service_fee"),
                "description": data.get("service_description"),
                "business_id": data.get('business_id'),
                "business_phone": data.get('business_phone'),
                "start_time": data.get("start_time"),
                "end_time": data.get("end_time"),
                "service_delivery": data.get("service_delivery"),
                "location": data.get("location"),
                "business_name": data.get("business_name"),
                "address": data.get("address"),
                "notes": data.get("note"),
                "date": data.get("date"),
                "creation_timestamp": datetime.datetime.now(),
                "status": "PAID",
                "country_code": customer['country_code'],
                "paid_business": False,
                "image": data.get('image'),
                "promo": False,
                "payment_url": "",
                "payment_reference": data.get("payment_reference"),
                "staff_id": data.get("staff_id"),
                "add_ons": data.get("add_ons")
            }
            orders.insert_one(order)
            
            
            business = businesses.find_one({"id": order["business_id"]})

            # Update pending balance of the business
            service_price = order['price']
            business_id = business["id"]
            pending_balance = business["pending_balance"]
            final_pending_balance = float(
                service_price) + (0.3 * float(order['service_fee']))
            
            if pending_balance is None or pending_balance == 0:
                pending_balance = 0          # First booking of the business

            pending_balance = pending_balance + final_pending_balance
            businesses.find_one_and_update({"id": business_id}, {
                '$set': {"pending_balance": pending_balance}})

            # Send push notification to business
            if business.get('fcm_token'):
                Notifications.send_single_notifications(fcm_token=business.get('fcm_token'), body="You have a new booking from "+order['customer_names'],title="New Booking on Piyata App")  
            
            # Send confirmation email to business
            msg = Message("Confirm Service Appointment", sender=(
            "Piyata", 'support@piyata.tech'), recipients=[business['email'], 'support@piyata.tech'])
            link = "https://www.piyata.tech/api/business/confirm/order/" + \
                order['id'] + "/"
            msg.html = '''
            <p>Hi {},</p><p>You have a new booking request from {} on {}.</p>
            <p>Service: {}<br>Location: {}<br>Time booked: {}<br>Notes: {}</p>
            <p>Thanks,<br>Team Piyata</p>
            '''.format(
                order['business_name'], order['customer_names'], order['date'], order['service_name'], order['service_delivery'], order['start_time'], order.get('notes'))
            mail.send(msg)


             # Send confirmation email to customer
            if customer.get('email') is not None:
                msg = Message("Booking Confirmation", sender=(
                    "Piyata", 'support@piyata.tech'), recipients=[customer['email'], 'support@piyata.tech'])
                msg.html = '''
                <p>Hi {},</p><p>Your booking with {} on {} has been confirmed.</p>
                <p>Service: {}<br>Location: {}<br>Time booked: {}<br>Notes: {}</p>
                <p>Thanks,<br>Team Piyata</p>
                '''.format(
                    order['customer_names'], order['business_name'], order['date'], order['service_name'], order['service_delivery'], order['start_time'], order.get('notes'))
                mail.send(msg)

            # Send push notification to customers
            fcm_token = customer.get('fcm_token')
            if fcm_token:
                Notifications.send_single_notifications(
                    fcm_token=fcm_token,
                    title="Booking Successful",
                    body="Your booking was successful. Booking fee is non refundable if you cancel 24 hours before the appointment time.")
            else: 
                fcm_token = customer.get('fcm token')
                print(fcm_token)
                Notifications.send_single_notifications(
                    fcm_token=fcm_token,
                    title="Booking Successful",
                    body="Your booking was successful. Booking fee is non refundable if you cancel 24 hours before the appointment time.")
        
            return order
        
    def create_customer_promo_order(self, customer):
        customer_id = customer["id"]
        if customers.find_one({"id": customer_id}):
            data = json.loads(request.data)
            # Create and insert order
            order = {
                "id": uuid.uuid4().hex,
                "customer_id": customer["id"],
                "customer_names": customer['first_name'] + " " + customer['last_name'],
                "customer_phone": customer['phone_number'],
                "service_name": data.get("service_name"),
                "service_id": data.get('service_id'),
                "duration": data.get('duration'),
                "price": data.get("service_price"),
                "service_fee": data.get("service_fee"),
                "description": data.get("service_description"),
                "business_id": data.get('business_id'),
                "business_phone": data.get('business_phone'),
                "start_time": data.get("start_time"),
                "end_time": data.get("end_time"),
                "service_delivery": data.get("service_delivery"),
                "location": data.get("location"),
                "business_name": data.get("business_name"),
                "address": data.get("address"),
                "notes": data.get("note"),
                "date": data.get("date"),
                "creation_timestamp": datetime.datetime.now(),
                "status": "PAID",
                "country_code": customer['country_code'],
                "paid_business": False,
                "image": data.get('image'),
                "promo": False,
                "payment_url": "",
                "payment_reference": data.get("payment_reference"),
                "staff_id": data.get("staff_id"),
                "add_ons": data.get("add_ons")
            }
            orders.insert_one(order)
            
            
            business = businesses.find_one({"id": order["business_id"]})

            # Send push notification to business
            if business.get('fcm_token'):
                Notifications.send_single_notifications(fcm_token=business.get('fcm_token'), body="You have a new booking from "+order['customer_names'],title="New Booking on Piyata App")  
            
            # Send confirmation email to business
            msg = Message("Confirm Service Appointment", sender=(
            "Piyata", 'support@piyata.tech'), recipients=[business['email'], 'support@piyata.tech'])
            link = "https://www.piyata.tech/api/business/confirm/order/" + \
                order['id'] + "/"
            msg.html = '''
            <p>Hi {},</p><p>You have a new booking request from {} on {}.</p>
            <p>Service: {}<br>Location: {}<br>Time booked: {}<br>Notes: {}</p>
            <p>Thanks,<br>Team Piyata</p>
            '''.format(
                order['business_name'], order['customer_names'], order['date'], order['service_name'], order['service_delivery'], order['start_time'], order.get('notes'))
            mail.send(msg)


             # Send confirmation email to customer
            if customer.get('email') is not None:
                msg = Message("Booking Confirmation", sender=(
                    "Piyata", 'support@piyata.tech'), recipients=[customer['email'], 'support@piyata.tech'])
                msg.html = '''
                <p>Hi {},</p><p>Your booking with {} on {} has been confirmed.</p>
                <p>Service: {}<br>Location: {}<br>Time booked: {}<br>Notes: {}</p>
                <p>Thanks,<br>Team Piyata</p>
                '''.format(
                    order['customer_names'], order['business_name'], order['date'], order['service_name'], order['service_delivery'], order['start_time'], order.get('notes'))
                mail.send(msg)

            # Send push notification to customers
            fcm_token = customer.get('fcm_token')
            if fcm_token:
                Notifications.send_single_notifications(
                    fcm_token=fcm_token,
                    title="Booking Successful",
                    body="Your booking was successful. Booking fee is non refundable if you cancel 24 hours before the appointment time.")
            else: 
                fcm_token = customer.get('fcm token')
                print(fcm_token)
                Notifications.send_single_notifications(
                    fcm_token=fcm_token,
                    title="Booking Successful",
                    body="Your booking was successful. Booking fee is non refundable if you cancel 24 hours before the appointment time.")
        
            return order
        

    @staticmethod
    def retrieve_order_by_uuid(id: str):
        my_query = {"id": id}
        order = orders.find_one(my_query)
        if order is None:
            return jsonify({"error": "user not found"}), 400
        return order
    
    def update_order_information(self, order, data):
        """"
        Update the business account information
        """
        if isinstance(order, str):
            return jsonify({"error": order}), 401
        id = order["id"]
        update = orders.update_one({"id": id}, {'$set': data})
        if update:
            updated_order = self.retrieve_order_by_uuid(id)
            return json.loads(json_util.dumps({"result": updated_order})), 200
        return jsonify({"error": "Failed to update your order information. Try again, please."}), 401

    def pay_business(self, order_id):
        order = orders.find_one({'id': order_id})
        # business = businesses.find_one({'id':order['business_id']})
        if not order['paid_business']: 
            country_code = "25"
            url = "https://opay-api.oltranz.com/opay/wallet/fundstransfer"
            amount = int(float(order['price']) +
                         ((float(2.5)*float(order['price']))/100)) 

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
                    "service_name":order['service_name']
                }
                transactions.insert_one(transaction)
            return status
        else:
            return "<script>window.alert('Payment is being processed or already completed.');</script>"

    def refund_customer(self, order_id):
        order = orders.find_one({'id': order_id})
        try:
            if order['status'] == "CANCELED" and order['promo'] == False: 
                # business = businesses.find_one({'id':order['business_id']})
                country_code = "25"
                url = "https://opay-api.oltranz.com/opay/wallet/fundstransfer"
                amount = int(float(order['price']) + 
                             ((float(2.6)*float(order['price']))/100)) 
                request_body = {
                    "merchantId": "ef4668f8-1bc0-4a9c-abf0-741aad737e99",
                    "receiverAccount": country_code + order['customer_phone'], 
                    "type": "MOBILE",
                    "transactionId": uuid.uuid4().hex,
                    "amount": amount,
                    "callbackUrl": "https://piyata.herokuapp.com/api/payment-callback/",
                    "description": "Refunding customer : " + order['customer_names'], 
                    "firstName": order['customer_names'], 
                    "lastName": "" 
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
                        "type": "REFUND",
                        "type": "REFUND",
                        "id": request_body['transactionId'],
                        "order_id": order_id,
                        "amount": request_body['amount'],
                        "date": datetime.datetime.now(),
                        "callbackObject": x.text,
                        "status": status,
                        "service_name":order['service_name']

                    }
                    transactions.insert_one(transaction)
                    orders.find_one_and_update(
                        {"id": order_id}, {'$set': {"status": "REFUNDED"}})

                return status

            else:
                if order['promo']: 
                    return {"error": "This service cannot be refunded because it was a promotion service."}

                return {"error": "Order was not canceled"}

        except:
            return {"error": "Order was not canceled"}

    def request_payment_ghana(self, customer, price):
        country_code = "0"
        price = int(price)*100
        url = "https://api.paystack.co/transaction/initialize"
        request_body = {
            "amount": price,
            "email": customer['email'],
            "currency": "GHS",
            "mobile_money": {
                "phone": country_code + str(customer['phone_number']),
                "provider": "mtn"
            }}
        headers = {
            "User-Agent": "Custom",
            "Authorization": 'Bearer'+paystack_secret, 
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Content-Length": "290"
        }

        paystack_response = requests.post(
            url, json=request_body, headers=headers)
        # response = json.loads(json_util.dumps(paystack_response.text))

        response = paystack_response.json()

        # Check payment success status and record transaction in DB
        if response.get("status"):
            return {"message": "Requested payment successfully.", "payment_url": response.get('data')["authorization_url"], "payment_reference": response.get('data')["reference"]}
        return {"error": "Failed to request payment."}

    def confirm_order_ghana(self, order):

        reference = order["payment_reference"]
        url = "https://api.paystack.co/transaction/verify/"+reference
        headers = {
            "Authorization": 'Bearer'+paystack_secret, 
            "Content-Type": "application/json",
        }

        paystack_response = requests.get(
            url, headers=headers)

        if paystack_response.status_code == 200:
            response = paystack_response.json()
            if response.get("data")["status"] == "success":
                orders.find_one_and_update({"id": order["id"]}, {
                                           '$set': {"status": "PAID"}})
                transaction = {
                    "type": "PAYMENT",
                    "type": "PAYMENT",
                    "id": response.get("data")["id"],
                    "order_id": order["id"],
                    "amount": order['price'],
                    "date": datetime.datetime.now(),
                    "callbackObject": "",
                    "status": response.get("data")["status"],
                    "service_name":order['service_name']
                }
                transactions.insert_one(transaction)
                business = Business.retrieve_business_by_uuid(
                    order['business_id'])
                msg = Message("Confirm Service Appointment", sender=(
                    "Piyata Booking", 'support@piyata.tech'), recipients=[business['email'], 'support@piyata.tech']) 
                link = "https://www.piyata.tech/api/business/confirm/order/" + \
                    order['id'] + "/"
                msg.html = '<p>Hi {},</p><p>You have a new booking request from {} on {}.</p><p>Service: {}<br>Location: {}<br>Time booked: {}<br>Notes: {}</p><p>Please, log in your Piyata account and click <a href="{}">here</a> to confirm this appointment or visit your business portal.</p><p>Thanks,<br>Team Piyata</p>'.format(
                    business["name"], order['customer_names'], order['date'], order['service_name'], order['address'], order['start_time'], order.get('notes'), link) 
                mail.send(msg)
                return orders.find_one({"id": order["id"]})

            return {"status": response.get("data")["status"]}
        return {"error": "error checking order status"}

    def confirm_order(self, order):
        if order['status'] != 'PAID':
            # Set order status to PAID
            orders.find_one_and_update({"id": order["id"]}, {
                '$set': {"status": "PAID"}})

            # Update pending balance of the business
            service_price = order['price']
            business = Business.retrieve_business_by_uuid(
                order['business_id'])
            customer = customers.find_one({'id':order['customer_id']})
            business_id = business["id"]
            pending_balance = business["pending_balance"]
            final_pending_balance = float(
                service_price) + (0.3 * float(order['service_fee']))
            
            if pending_balance is None or pending_balance == 0:
                pending_balance = 0          # First booking of the business

            pending_balance = pending_balance + final_pending_balance
            businesses.find_one_and_update({"id": business_id}, {
                '$set': {"pending_balance": pending_balance}})

            # Send confirmation email to the business
            Notifications.business_booking_confirmation_email(business_email=business['email'], order=order)
            
            # Send push notifcation to the business
            if business['fcm_token'] is not None:
                Notifications.send_single_notifications(title="New Booking on Piyata App",body="You have a new booking from "+order["customer_names"], fcm_token=business['fcm_token'])

            # Send confirmation email to customer
            if customer.get('email') is not None:
                Notifications.customer_payment_receipt_email(customer_email=customer['email'], order=order)
                Notifications.customer_booking_confirmation_email(customer_email=customer['email'], order=order)
                
            # Send push notification to customers
            fcm_token = customer.get('fcm_token')
            if fcm_token:
                Notifications.send_single_notifications(
                    fcm_token=fcm_token,
                    title="Booking Successful",
                    body="Your booking was successful. Booking fee is non refundable if you cancel 24 hours before the appointment time.")
            else: 
                fcm_token = customer.get('fcm token')
                print(fcm_token)
                Notifications.send_single_notifications(
                    fcm_token=fcm_token,
                    title="Booking Successful",
                    body="Your booking was successful. Booking fee is non refundable if you cancel 24 hours before the appointment time.")
                
            return orders.find_one({"id": order["id"]}), 200
        else:
            return jsonify({"message": "Order already paid"}), 400
    
    @staticmethod
    def transfer_from_pending_to_balance(order_id):
        order = orders.find_one({"id": order_id})
        if order is not None and order["status"] == "PAID":
            business = businesses.find_one({"id": order["business_id"]})
            points = 0
            balance_equivalent = 0
            country_code = business["country_code"]
            price = float(order["price"])
            piyata_points = business.get("piyata_points")

            if piyata_points is None:
                piyata_points = 0.0
            else:
                piyata_points = float(piyata_points)

            if country_code == "+233":
                if price > 50:
                    points = 0.005*50
                    balance_equivalent = points*2
                else:
                    points = 0.005*price
                    balance_equivalent = points*2
            elif country_code == "+250":
                if price > 1000:
                    points = 0.00005*1000
                    balance_equivalent = points*200
                else:
                    points = 0.00005*price
                    balance_equivalent = points*200
                
            #credit business with the amount of the order
            business_money = float(order["price"])
            if business["balance"] is None:
                business_balance = business_money + balance_equivalent
                businesses.find_one_and_update({"id": order["business_id"], }, {
                    '$set': {"balance": business_balance}})

            else:
                business_balance = float(
                    business["balance"]) + business_money + balance_equivalent
                businesses.find_one_and_update({"id": order["business_id"]}, {
                    '$set': {"balance": business_balance}})

            if business["pending_balance"] is not None and int(business['pending_balance']) > 0:
                business_pending_balance = float(
                    business["pending_balance"]) - business_money + balance_equivalent
                businesses.find_one_and_update({"id": order["business_id"]}, {
                    '$set': {"pending_balance": business_pending_balance}})

            orders.find_one_and_update({"id": order["id"]}, {
                                       '$set': {"status": "COMPLETED"}})
            
            # award business and customer with points
            businesses.find_one_and_update({"id": business['id']},{'$set': {"piyata_points": piyata_points + points}})

            customer = customers.find_one({'id':order['customer_id']})
            if customer:
                customer_points = customer.get('piyata_points')
                customer_balance = customer.get('balance')
                if customer_points is None:
                    customer_points = 0.0 + (points/2)
                else:
                    customer_points = float(customer_points) + (points/2)
                if customer_balance is None:
                    customer_balance = 0.0 + (balance_equivalent/2)
                else:
                    customer_balance = float(customer_balance) + (balance_equivalent/2)
                customers.find_one_and_update({"id": order['customer_id']},{'$set': {"piyata_points": customer_points, "balance": customer_balance}})
           
            #send notifications to customer and business
            if business['fcm_token']:
                Notifications.send_single_notifications(
                    fcm_token=business['fcm_token'],
                    title="Service Completed",
                    body="Your booking with " + order['customer_names'] + " has been completed. Thank you for using Piyata.")
            Notifications.send_service_completed_email_business(business_id=business['id'], customer_name = order['customer_name']  )
           
            if customer:
                fcm_token = customer.get('fcm_token')
                if fcm_token:
                    Notifications.send_single_notifications(
                        fcm_token=fcm_token,
                        title="Service Completed Successfully!",
                        body="Your booking with " + order['business_name'] + " has been completed. Thank you for using Piyata.")
                else: 
                    fcm_token = customer.get('fcm token')
                    print(fcm_token)
                    Notifications.send_single_notifications(
                        fcm_token=fcm_token,
                        title="Service Completed Successfully!",
                        body="Your booking with " + order['business_name'] + " has been completed. Thank you for using Piyata.")
            Notifications.send_service_completed_email_customer(customer_id=customer['id'], business_name = order['business_name'])
            
            updated_business = businesses.find({"id": business["id"]})
            updated_order = orders.find({"id": order["id"]})
            return json.loads(json_util.dumps({"business": updated_business, "order": updated_order})), 200
        else:
            return jsonify({"error": "business has already been credited or order does not exist"})

