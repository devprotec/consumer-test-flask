from flask import jsonify
import os
import json
import base64
from flask_mail import Message
import firebase_admin
from firebase_admin import messaging, credentials
from . import mail
from src import mongo_client

env = os.environ.get('FLASK_ENV')

if env == 'production':
    businesses = mongo_client.piyata_mobile_app_production.businesses
    customers = mongo_client.piyata_mobile_app_production.customers
else:
    businesses = mongo_client.piyata_mobile_app_testing.businesses
    customers = mongo_client.piyata_mobile_app_testing.customers

encoded_key = os.getenv("SERVICE_ACCOUNT_KEY")
encoded_key = str(encoded_key)[2:-1]
original_service_key = json.loads(
    base64.b64decode(encoded_key).decode('utf-8'))
firebase_cred = credentials.Certificate(original_service_key)

firebase_app = firebase_admin.initialize_app(firebase_cred)



class Notifications:
    @staticmethod
    def send_single_notifications(fcm_token, title, body):
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,

            ),
            token=fcm_token,
            android=messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    sound='default',
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default'
                    )
                )
            )
        )

        try:
            send_message = messaging.send(message)
            if send_message:
                return jsonify({'success': "Message sent successfully"}), 200
            return jsonify({'error': "Failed to send message. Please, try again."}), 401
        except Exception as e:
            return jsonify({'error': "Failed to send message. Please, try again."}), 401
    
    @staticmethod
    def send_multicast_notifications(tokens, title, body):
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,

            ),
            tokens=tokens,
            android=messaging.AndroidConfig(
                notification=messaging.AndroidNotification(
                    sound='default',
                ),
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default'
                    )
                )
            )
        )

        try:
            send_message = messaging.send_multicast(message)
            if send_message:
                return jsonify({'success': "Message sent successfully"}), 200
            return jsonify({'error': "Failed to send message. Please, try again."}), 401
        except Exception as e:
            return jsonify({'error': "Failed to send message. Please, try again."}), 401
    

    @staticmethod
    def send_welcome_email(customer_id):
        customer = customers.find_one({"id": customer_id})
        if customer:
            msg = Message("Welcome to Piyata", sender=(
                "Piyata", 'support@piyata.tech'), recipients=[customer['email'], 'support@piyata.tech'])
            msg.html = '''
            <p>Hello there,</p>
            <p>Thank you for choosing Piyata. You made the right choice! Piyata helps you reach exceptional beauty professionals around you. Start booking on Piyata to get the best customer service.</p>
            <p>Piyata Team</p>
            '''.format()
            mail.send(msg)
            return jsonify({'success': 'Email Notification Sent Successfully'}), 200
        return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}), 401

    @staticmethod
    def send_service_completed_email_customer(customer_id, business_name):
        customer = customers.find_one({"id": customer_id})
        if customer:
            msg = Message("Booking Completed", sender=(
                "Piyata", 'support@piyata.tech'), recipients=[customer['email'], 'support@piyata.tech'])
            msg.html = '''
            <p>Hello there,</p>
            <p>Your booking with {} has been completed. Thank you for using Piyata.</p>
            <p>Piyata Team</p>
            '''.format(business_name)
            mail.send(msg)
            return jsonify({'success': 'Email Notification Sent Successfully'}), 200
        return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}), 401
    
    @staticmethod
    def send_service_completed_email_business(business_id, customer_name):
        business = businesses.find_one({"id": business_id})
        if business:
            msg = Message("Booking Completed", sender=(
                "Piyata", 'support@piyata.tech'), recipients=[business['email'], 'support@piyata.tech'])
            msg.html = '''
            <p>Hello there,</p>
            <p>Your booking with {} has been completed. Thank you for using Piyata.</p>
            <p>Piyata Team</p>
            '''.format(customer_name)
            mail.send(msg)
            return jsonify({'success': 'Email Notification Sent Successfully'}), 200
        return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}), 401
    
    @staticmethod
    def send_booking_email(business_id):
        business = businesses.find_one({"id": business_id})
        if business:
            msg = Message("Booking Confirmation", sender=(
                "Piyata", 'support@piyata.tech'), recipients=[business['email'], 'support@piyata.tech'])
            msg.html = '''
            <p>Hello,</p>
            <p>Your booking on Piyata has been confirmed.</p>
            <p>Piyata Team</p>
            '''.format()
            mail.send(msg)
            return jsonify({'success': 'Email Notification Sent Successfully'}), 200
        return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}), 401

    @staticmethod
    def send_business_approval_message(business_id):
        business = businesses.find_one({"id": business_id})
        if business:
            msg = Message("Piyata", sender=(
                "Piyata", 'support@piyata.tech'), recipients=[business['email'], 'support@piyata.tech'])
            msg.html = '''
            <p>Hello,</p>
            <p>Thank you for submitting your documents for verification. We are pleased to inform you that your business has been approved. You can now start creating your services on Piyata to reach more customers. Welcome again, and we cannot wait to see you grow with Piyata.</p>
            <p>Piyata Team</p>
            '''.format()
            mail.send(msg)
            return jsonify({'success': 'Email Notification Sent Successfully'}), 200
        return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}), 401
    
    @staticmethod
    def send_business_rejection_message(business_id, rejected_reason):
        business = businesses.find_one({"id": business_id})
        if business:
            msg = Message("Piyata", sender=(
                "Piyata", 'support@piyata.tech'), recipients=[business['email'], 'support@piyata.tech'])
            msg.html = '''
            <p>Hello,</p>
            <p>Thank you for submitting your documents for verification. Unfortunately, your business has been rejected for some reasons. Please sign into your account to check the reasons and resubmit your business for verification.</p>
            <p>Rejected Reason: {}</p>
            <p>Piyata Team</p>
            '''.format(rejected_reason)
            mail.send(msg)
            return jsonify({'success': 'Email Notification Sent Successfully'}), 200
        return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}), 401
    
    @staticmethod
    def send_service_approval_message(business_id):
        business = businesses.find_one({"id": business_id})
        if business:
            msg = Message("Piyata", sender=(
                "Piyata", 'support@piyata.tech'), recipients=[business['email'], 'support@piyata.tech'])
            msg.html = '''
            <p>Hello,</p>
            <p>Thank you for submitting your service for verification. We are pleased to inform you that your service has been approved. Customers can now see and start booking your service.</p>
            <p>Piyata Team</p>
            '''.format()
            mail.send(msg)
            return jsonify({'success': 'Email Notification Sent Successfully'}), 200
        return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}), 401
    
          
    @staticmethod
    def send_service_reported_message(business_id):
        business = businesses.find_one({"id": business_id})
        if business:
            msg = Message("Piyata", sender=(
                "Piyata", 'support@piyata.tech'), recipients=[business['email'], 'support@piyata.tech'])
            msg.html = '''
            <p>Hello,</p>
            <p>Your service has been reported. Please check the reason on your business page and resend the service after rectifying the issue.</p>
            <p>Piyata Team</p>
            '''.format()
            mail.send(msg)
            return jsonify({'success': 'Email Notification Sent Successfully'}), 200
        return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}), 401
    
    @staticmethod
    def send_service_rejection_message(business_id, rejected_reason):
        business = businesses.find_one({"id": business_id})
        if business:
            msg = Message("Piyata", sender=(
                "Piyata", 'support@piyata.tech'), recipients=[business['email'], 'support@piyata.tech'])
            msg.html = '''
            <p>Hello,</p>
                <p>Thank you for submitting your service for verification. Unfortunately, your service has been rejected for some reasons. Please sign into your account to check the reasons and resubmit your service for verification.</p>
                <p>Rejected Reason: {}</p>
            <p>Piyata Team</p>
            '''.format(rejected_reason)
            mail.send(msg)
            return jsonify({'success': 'Email Notification Sent Successfully'}), 200
        return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}), 401
    

    @staticmethod
    def send_giftcard_email(email,gifter_name, gifted_name,giftcard_id, giftcard_code):
            msg = Message("You have a Piyata Gift Card", sender=(
                "Piyata", 'support@piyata.tech',), recipients=[email, 'support@piyata.tech'], bcc=['iradukundapaterne1@gmail.com'])
            msg.html = '''<p>Hello {},</p>
                <p>{} has given you a free Piyata gift card.</p>
                <p><b>How to redeem your gift card</b></p>
                <ol>
                    <li>Download the Piyata app and sign up if you don't have it. <a href="https://piyata.tech/download-app">Download Piyata for customers</a></li>
                    <li>Click on the link below using your mobile phone to redeem your gift card. <a href="https://piyata.tech/giftcards/{}">Redeem gift card here</a></li>
                </ol>
                <p><h1><em>{}</em></h1> is your gift card secret code</p>
                <p>Piyata Team</p>'''.format(gifted_name,gifter_name,giftcard_id,giftcard_code)
            mail.send(msg)
            
    @staticmethod
    def business_booking_confirmation_email(order, business_email):
        msg = Message("Confirm Service Appointment", sender=(
                "Piyata", 'support@piyata.tech'), recipients=[business_email, 'support@piyata.tech'], bcc=['iradukundapaterne1@gmail.com'])
        msg.html = '''
        <p>Hi {},</p><p>You have a new booking request from {} on {}.</p>
        <p>Service: {}<br>Location: {}<br>Time booked: {}<br>Notes: {}</p>
        <p>Thanks,<br>Team Piyata</p>
        '''.format(
            order['business_name'], order['customer_names'], order['date'], order['service_name'], order['service_delivery'], order['start_time'], order.get('notes'))
        mail.send(msg)
        
    @staticmethod
    def customer_booking_confirmation_email(order, customer_email):
        msg = Message("Booking Confirmation", sender=(
                    "Piyata", 'support@piyata.tech'), recipients=[customer_email, 'support@piyata.tech'], bcc=['iradukundapaterne1@gmail.com'])
        msg.html = '''
        <p>Hi {},</p><p>Your booking with {} on {} has been confirmed.</p>
        <p>Service: {}<br>Location: {}<br>Time booked: {}<br>Notes: {}</p>
        <p>Thanks,<br>Team Piyata</p>
        '''.format(
            order['customer_names'], order['business_name'], order['date'], order['service_name'], order['service_delivery'], order['start_time'], order.get('notes'))
        mail.send(msg)

    @staticmethod
    def customer_payment_receipt_email(order, customer_email):
        msg = Message("Payment Receipt", sender=(
                    "Piyata", 'support@piyata.tech'), recipients=[customer_email, 'support@piyata.tech'], bcc=['iradukundapaterne1@gmail.com'])
        msg.html = '''
        <p>Hi {},</p>
        <p>We have received your payment of GHS {} for the booking of {}.</p>
        <p>You will receive a separate email to confirm your booking soon.</p>
        <p>Thanks,<br>Team Piyata</p>
        '''.format(
            order['customer_names'], order['service_fee'], order['service_name'])
        mail.send(msg)

    @staticmethod
    def send_customer_approval_message(customer_id):
        customer = customers.find_one({"id": customer_id})
        if customer:
            msg = Message("Piyata", sender=(
                    "Piyata", 'support@piyata.tech'), recipients=[customer['email'], 'support@piyata.tech'])
            msg.html = '''
                <p>Hello,</p>
                <p>Thank you for submitting your account for verification. We are pleased to inform you that your account has been approved. You can now see and start booking service.</p>
                <p>Piyata Team</p>
                '''.format()
            mail.send(msg)
            return jsonify({'success': 'Email Notification Sent Successfully'}), 200
        return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}), 401
    
    @staticmethod
    def send_customer_rejection_message(customer_id,message):
        customer = customers.find_one({"id":customer_id })
        if customer:
            msg = Message("Piyata", sender=(
                "Piyata", 'support@piyata.tech'), recipients=[customer['email'], 'support@piyata.tech'])
            msg.html = '''
                <p>Hello,</p>
                    <p>Thank you for submitting your account for verification. Unfortunately, your account has been rejected for the following reasons: </p>
                    <p>{}</p>
                    <p>Please log into your account and resubmit your account for verification. </p>
                <p>Piyata Team</p>
                '''.format(message)
            mail.send(msg)
            return jsonify({'success': 'Email Notification Sent Successfully'}), 200
        return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}), 401
    
    @staticmethod
    def send_customer_submit_message(customer_id):
        customer = customers.find_one({"id":customer_id })
        if customer:
            msg = Message("Piyata", sender=(
                "Piyata", 'support@piyata.tech'), recipients=[customer['email'], 'support@piyata.tech'])
            msg.html = '''
                <p>Hello,</p>
                    <p>Successfully submitted for verification. The review process may take several hours. Thank you for helping keep Piyata community safe for all users.</p>
                <p>Piyata Team</p>
                '''.format()
            mail.send(msg)
            return jsonify({'success': 'Email Notification Sent Successfully'}), 200
        return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}), 401