from flask import request, Blueprint, session, jsonify
from functools import wraps
from .models import Customer, Business, Orders, Review, Services,promotions, customers, giftcards, images, businesses, services, orders, reviews, transactions, Transaction, staffs
from .order_management import OrderManagement
from .notifications import Notifications
from .messages import Messages
from . import login_manager, mail
import datetime
import uuid
import boto3
import os
from werkzeug.utils import secure_filename
from .models import ImagesDatabaseClient
import json
from bson import json_util
from .giftcards import GiftCards
from .promotions import Promotions
from flask_mail import Mail, Message
# from time import sleep
# from celery import Celery


views = Blueprint('views', __name__)

require_verified_services = os.environ.get('REQUIRE_APPROVED_SERVICES')

# Flask-Login helper to retrieve a user from our db


@login_manager.user_loader
def load_user(email):
    return customers.find_one({"email": email})


def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            return jsonify({"error": "user not logged in"}), 400
    return wrap


@views.route('/api/signup', methods=["POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        customer = Customer()
        return customer.signup(email=email, password=password)
    else:
        return jsonify({"error": "invalid request"}), 400


@views.route('/api/google_signup', methods=["POST"])
def googleSignup():
    if request.method == "POST":
        email = request.form["email"]
        name = request.form["first_name"]
        image = request.form["image"]
        customer = Customer()
        return customer.google_signup(email=email, name=name, profile_picture=image)
    else:
        return jsonify({"error": "invalid request"}), 400

@views.route('/api/continue-with-apple', methods=["POST"])
def continue_with_apple():
    if request.method == "POST":
        id = request.form["id"]
        customer = Customer()
        return customer.continue_with_apple(id=id)
    else:
        return jsonify({"error": "invalid request"}), 400


@views.route('/api/login', methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        customer = Customer()
        return customer.login(email=email, password=password)
    else:
        return jsonify({"error": "invalid request"}), 400


@views.route('/api/logout')
def user_logout():
    return Customer().logout()


@views.route('/api/profile/update', methods=["POST"])
def update_customer_information():
    if request.method == "POST":
        data = json.loads(request.data)
        customer = Customer().retrieve_customer_by_uuid(
            session['user']['id'])
        return Customer().update_customer_account_information(customer, data=data)
    
@views.route('/api/business/update/<business_id>', methods=["POST"])
def update_business_information(business_id):
    if request.method == "POST":
        data = json.loads(request.data)
        business = Business().retrieve_business_by_uuid(business_id)
        return Business().update_business_account_information(business, data=data)
    
@views.route('/api/business/services-update/<business_id>', methods=["POST"])
def update_business_services_information(business_id):
    if request.method == "POST":
        data = json.loads(request.data)
        return Services().update_service_information(business_id=business_id, data=data)
    
@views.route('/api/service/update/<service_id>', methods=["POST"])
def update_pending_or_reported_service(service_id):
    if request.method == "POST":
        data = json.loads(request.data)
        service = Services().retrieve_pending_or_reported_service_by_uuid(service_id)
        return Services().update_pending_or_reported_service(service, data=data)
    
@views.route('/api/order/update/<order_id>', methods=["POST"]) 
def update_order_information(order_id):
    if request.method == "POST":
        data = json.loads(request.data)
        order = OrderManagement().retrieve_order_by_uuid(
           order_id)
        return OrderManagement().update_order_information(order= order, data=data)
    # Delete a business

@views.route('/api/retrieve_customer', methods=["GET"]) 
def retrieve_customer():
    if request.method == "GET":
        customer = Customer().retrieve_customer_by_uuid(session['user']['id'])
        return json.loads(json_util.dumps(customer))


@views.route('/api/profile/upload-image', methods=["POST"]) 
def upload_customer_profile():
    if request.method == "POST":
        s3 = boto3.resource('s3')
        BUCKET_NAME = 'piyataimages'
        f = request.files["profile"]
        filename = uuid.uuid4().hex + secure_filename(f.filename) 
        # f.save(filename)
        s3.Bucket(BUCKET_NAME).put_object(Key=filename, Body=f)
        customer = Customer().retrieve_customer_by_uuid(
            session['user']['id'])
        # Delete old profile image from bucket
        if customer['image']:  
            s3.Object(BUCKET_NAME, customer['image']).delete()  
        image_id = uuid.uuid4().hex
        if (customer['email']): 
            images.insert_one({"id": image_id, "creation_timestamp": datetime.datetime.now(
            ), "name": filename, "email": customer["email"], "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"}) 
        elif (customer['phone_number']):  
            images.insert_one({"id": image_id, "creation_timestamp": datetime.datetime.now(
            ), "name": filename, "phone_number": customer["phone_number"], "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"}) 
        image = ImagesDatabaseClient.retrieve_image_by_uuid(image_id)
        return Customer().update_customer_profile_image(customer, image)


@views.route('/api/all_businesses', methods=["GET"]) 
def get_all_businesses():
    customer = Customer.retrieve_customer_by_uuid(
        session['user']['id'])
    if not customer:
        return jsonify({"Error": "No user found. Please login or signup"})
    country = customer.get("country")
    preference = customer.get("account_preference", False)
    customer_favorite = customer.get("favorite_services", [])
    if preference is not None:
        if preference == False:
            all_business_results = []
            cursor_businesses = businesses.find(
                {
                "status": {"$in": ["ACTIVE", "INACTIVE"]},
                "account_verification.status": {"$in": ["VERIFIED", "UNVERIFIED", "PENDING"]},
                "country": country}).sort(
            [('rating', -1), ('reviews', -1), ("image", 1)])
            if cursor_businesses:
                data = list(cursor_businesses)
                businesses_with_services = []
                for business in data:
                    business_id = business.get("id")
                    
                    if require_verified_services == "True":
                        if services.find_one({"business_id": business_id, "online": True,  "verification_status" :"APPROVED"}):
                            businesses_with_services.append(business)
                    else:
                        if services.find_one({"business_id": business_id, "online": True}):
                            businesses_with_services.append(business)
                businesses_list = json.loads(json_util.dumps(businesses_with_services))
                all_business_results = businesses_list if businesses_list else []
            return all_business_results
        elif preference == True:
            all_business_results = []
            cursor_businesses = businesses.find(
                {
                "status": {"$in": ["ACTIVE", "INACTIVE"]},
                "service_categories": {"$in": customer_favorite},
                "account_verification.status": {"$in": ["VERIFIED", "UNVERIFIED", "PENDING"]},
                "country": country}).sort(
            [('rating', -1), ('reviews', -1), ("image", 1)])
            if cursor_businesses:
                data = list(cursor_businesses)
                businesses_with_services = []
                for business in data:
                    business_id = business.get("id")
                    if require_verified_services == "True":
                        if services.find_one({"business_id": business_id, "online": True,  "verification_status" :"APPROVED"}):
                            businesses_with_services.append(business)
                    else:
                        if services.find_one({"business_id": business_id, "online": True}):
                            businesses_with_services.append(business)
                businesses_list = json.loads(json_util.dumps(businesses_with_services))
                all_business_results = businesses_list if businesses_list else []
            return all_business_results
    else:
        return jsonify({"Error": "No User found. Please login or signup"})

@views.route('/api/get-unverified-businesses', methods=["GET"])
def get_all_unverified_businesses():
    all_unverified_business_results = []
    cursor_businesses = businesses.find({"account_verification.status": "PENDING"})
    if cursor_businesses:
        data = list(cursor_businesses)
        businesses_list = json.loads(json_util.dumps(data))
        all_unverified_business_results = businesses_list

        if all_unverified_business_results == []:
            all_unverified_business_results = "No businesses found"
        return all_unverified_business_results
    else:
        return jsonify({"Error": "No business found"})

@views.route('/api/fetch-guest-businesses/<country>/', methods=["GET"])
def fetch_guest_businesses(country):
    filtered_business = businesses.find({
                "status": {"$in": ["ACTIVE", "INACTIVE"]},
                "account_verification.status": {"$in": ["VERIFIED", "UNVERIFIED", "PENDING"]},
                "country": country}).sort(
            [('rating', -1), ('reviews', -1), ("image", 1)])
    if filtered_business:
        data = list(filtered_business)
        businesses_with_services = []
        for business in data:
            business_id = business.get("id")
            if require_verified_services == "True":
                if services.find_one({"business_id": business_id, "online": True,  "verification_status" :"APPROVED"}):
                    businesses_with_services.append(business)
            else:
                if services.find_one({"business_id": business_id, "online": True}):
                    businesses_with_services.append(business)
        businesses_list = json.loads(json_util.dumps(businesses_with_services))
        all_business_results = businesses_list if businesses_list else []
    return all_business_results

@views.route('/api/fetch-guest-services/<country>/', methods=["GET"])
def fetch_guest_services(country):
    currency = ''
    if country == "GH":
        currency = "GHC"
    elif country == "RW":
        currency = "RWF"
    filtered_services = services.find({'currency':currency,'online':True}).sort(
            [('rating', -1), ('reviews', -1), ("image", 1)])
    return json.loads(json_util.dumps(filtered_services))

@views.route('/api/all_services', methods=["GET"]) 
def get_all_services():
    print(str(require_verified_services).lower)
    customer = Customer.retrieve_customer_by_uuid(session['user']['id'])
    if not customer:
        return jsonify({"Error": "No user found. Please login or signup"})
    preference = customer.get("account_preference", False)
    customer_favorite = customer.get("favorite_services", [])
    country_code = customer.get("country_code")
    currency = ''
    if country_code == "+233":
        currency = "GHC"
    elif country_code == "+250":
        currency = "RWF"
    if preference is not None:
        if preference == False:
            all_service_results = []
            cursor_services = services.find(
                {
                "online": True,
                "verification_status" :"APPROVED",
                "currency": currency}).sort(
        [('rating', -1), ('reviews', -1), ("image", 1)]) if require_verified_services == "True" else services.find(
                {
                "online": True,
                "currency": currency}).sort(
        [('rating', -1), ('reviews', -1), ("image", 1)])
            if cursor_services:
                data = list(cursor_services)
                services_list = json.loads(json_util.dumps(data))
                all_service_results = services_list if services_list else []
                return  all_service_results
                
        elif preference == True:
            all_service_results = []
            cursor_services = services.find(
                {
                "online": True,
                "verification_status" :"APPROVED",
                "category":{"$in": customer_favorite},
                "currency": currency}).sort(
        [('rating', -1), ('reviews', -1), ("image", 1)]) if require_verified_services == "True" else services.find(
                {
                "online": True,
                "category":{"$in": customer_favorite},
                "currency": currency}).sort(
        [('rating', -1), ('reviews', -1), ("image", 1)])
            if cursor_services:
                data = list(cursor_services)
                services_list = json.loads(json_util.dumps(data))
                all_service_results = services_list if services_list else []
                return  all_service_results
    else:
        return jsonify({"Error": "No User found. Please login or signup"})


@views.route('/api/paid_orders/<customer_id>', methods=["GET"])
def get_all_paid_orders(customer_id):
    customer = Customer.retrieve_customer_by_uuid(session['user']['id'])
    country_code = customer["country_code"] 
    if customer:
        paid_orders = orders.find(
            {"customer_id":customer_id,
             "status": "PAID",
             "country_code": country_code
                            })
        if paid_orders:
            return json.loads(json_util.dumps(paid_orders))
        return jsonify({"Error": "No bookings found."})
    else:
        return jsonify({"Error": "No User found. Please login or signup"})

@views.route('/api/business/orders/<business_id>', methods=["GET"])
def get_all_business_paid_orders(business_id):
    customer = Customer.retrieve_customer_by_uuid(session['user']['id'])
    if customer:
        paid_orders = orders.find(
            {"business_id":business_id,
             "status": "PAID"
                            })
        if paid_orders:
            return json.loads(json_util.dumps(paid_orders))
        return jsonify({"Error": "No bookings found."})
    else:
        return jsonify({"Error": "No User found. Please login or signup"})

@views.route('/api/update/order/<order_id>/', methods=['POST']) 
def update_order(order_id):
    if request.method == "POST":
        order = orders.find_one({'id': order_id})
        if order:
            customer = Customer.retrieve_customer_by_uuid(session['user']['id'])
            return OrderManagement().update_order(order, customer)


@views.route('/api/filter/service', methods=["POST"]) 
def filter_services():
    if request.method == "POST":
        data = json.loads(request.data)
        return jsonify(Services().filter_services(data=data))


@views.route('/api/filter/business', methods=["POST"]) 
def filter_businesses():
    if request.method == "POST":
        data = json.loads(request.data)
        return jsonify(Business().filter_businesses(data=data))


@views.route('/api/search/business/<keyword>/', methods=['GET']) 
def get_businesses(keyword):
    customer = Customer.retrieve_customer_by_uuid(session['user']['id'])
    country_code = customer["country_code"]  
    if customer:
        cursor_businesses = businesses.find(
            {"$text": {"$search": keyword},
             "status": "ACTIVE",
             "account_verification.status":{"$in": ["VERIFIED", "PENDING", "UNVERIFIED"]},
             "country_code": country_code}).sort(
            [('rating', -1), ('reviews', -1), ("image", 1)]).limit(30)
        if cursor_businesses:
            data = list(cursor_businesses)
            businesses_with_services = []
            for business in data:
                business_id = business.get("id")
                if require_verified_services == "True":
                    if services.find_one({"business_id": business_id, "online": True,  "verification_status" :"APPROVED"}):
                        businesses_with_services.append(business)
                else:
                    if services.find_one({"business_id": business_id, "online": True}):
                        businesses_with_services.append(business)
            businesses_list = json.loads(json_util.dumps(businesses_with_services))
            all_business_results = businesses_list if businesses_list else []

            if all_business_results == []:
                all_business_results = "No results found in businesses for keyword:'" + keyword + "'"
            return jsonify({'result': all_business_results})


@views.route('/api/guest-search/business/<keyword>/<country>/', methods=['GET']) 
def get_guest_businesses(keyword, country):
    country_code = ''
    if country == "GH":
        country_code = "+233"
    elif country == "RW":
        country_code = "+250"
    cursor_businesses = businesses.find(
            {"$text": {"$search": keyword},
             "status": "ACTIVE",
            "account_verification.status":{"$in": ["VERIFIED", "PENDING", "UNVERIFIED"]},
             "country_code": country_code}).sort(
            [('rating', -1), ('reviews', -1), ("image", 1)]).limit(30)
    if cursor_businesses:
        data = list(cursor_businesses)
        businesses_with_services = []
        for business in data:
            business_id = business.get("id")
            if require_verified_services == "True":
                if services.find_one({"business_id": business_id, "online": True,  "verification_status" :"APPROVED"}):
                    businesses_with_services.append(business)
            else:
                if services.find_one({"business_id": business_id, "online": True}):
                    businesses_with_services.append(business)
        businesses_list = json.loads(json_util.dumps(businesses_with_services))
        all_business_results = businesses_list if businesses_list else []

        if all_business_results == []:
            all_business_results = "No results found in businesses for keyword:'" + keyword + "'"
        return jsonify({'result': all_business_results})

@views.route('/api/business/services/<business_id>', methods=["GET"])
def retrieve_services_using_business_id(business_id):
    all_business_services = []
    business_services = services.find({"business_id": business_id, "online": True,})
    if business_services:
        data = list(business_services)
        businesses_list = json.loads(json_util.dumps(data))
        all_business_services = businesses_list
    if all_business_services:
        return json.loads(json_util.dumps(all_business_services))
    return jsonify({"Error": "Services not found."})

@views.route('/api/business/unverified-services/<business_id>', methods=["GET"])
def retrieve_business_unverified_services_using_business_id(business_id):
    all_unverified_business_service = []
    business_services = services.find({"business_id": business_id,})
    if business_services:
        data = list(business_services)
        businesses_list = json.loads(json_util.dumps(data))
        all_unverified_business_service = businesses_list
    if all_unverified_business_service:
        return json.loads(json_util.dumps(all_unverified_business_service))
    return jsonify({"Error": "Services not found."})

@views.route('/api/business/schedule/<business_id>', methods=["GET"])
def retrieve_schedule_using_business_id(business_id):
    all_business_schedule = []
    business_schedule = businesses.find({"id": business_id, "status":{"$in": ["ACTIVE", "INACTIVE"]}})
    if business_schedule:
        data = list(business_schedule)
        businesses_list = json.loads(json_util.dumps(data))
        all_business_schedule = businesses_list
    if all_business_schedule:
        return json.loads(json_util.dumps(all_business_schedule))
    return jsonify({"Error": "Business not found."})

@views.route('/api/business/review/<business_id>', methods=["GET"])
def retrieve_reviews_using_business_id(business_id):
    all_business_reviews = []
    business_reviews = reviews.find({"business_id": business_id, "status": "APPROVED"})
    if business_reviews:
        data = list(business_reviews)
        businesses_list = json.loads(json_util.dumps(data))
        all_business_reviews = businesses_list
    if all_business_reviews:
        return json.loads(json_util.dumps(all_business_reviews))
    return jsonify({"Error": "Reviews not found."})

@views.route('/api/service/review/<service_id>', methods=["GET"])
def retrieve_reviews_using_service_id(service_id):
    all_service_reviews = []
    service_reviews = reviews.find({"service_id": service_id, "status": "APPROVED"})
    if service_reviews:
        data = list(service_reviews)
        services_list = json.loads(json_util.dumps(data))
        all_service_reviews = services_list
    if all_service_reviews:
        return json.loads(json_util.dumps(all_service_reviews))
    return jsonify({"Error": "Reviews not found."})

@views.route('/api/pending/services/', methods=["GET"])
def retrieve_reported_services():
    all_pending_services = []
    service_reviews = services.find({"verification_status": "PENDING"})
    if service_reviews:
        data = list(service_reviews)
        services_list = json.loads(json_util.dumps(data))
        all_pending_services = services_list
    if all_pending_services:
        return json.loads(json_util.dumps(all_pending_services))
    return jsonify({"Error": "Pending servicesd not found."})

@views.route('/api/reported/services/', methods=["GET"])
def retrieve_pending_services():
    all_reported_services = []
    service_reviews = services.find({"verification_status": "REPORTED"})
    if service_reviews:
        data = list(service_reviews)
        services_list = json.loads(json_util.dumps(data))
        all_reported_services = services_list
    if all_reported_services:
        return json.loads(json_util.dumps(all_reported_services))
    return jsonify({"Error": "Reported services not found."})

@views.route('/api/pending/review/', methods=["GET"])
def retrieve_pending_reviews():
    all_service_reviews = []
    service_reviews = reviews.find({"status": "PENDING"})
    if service_reviews:
        data = list(service_reviews)
        services_list = json.loads(json_util.dumps(data))
        all_service_reviews = services_list
    if all_service_reviews:
        return json.loads(json_util.dumps(all_service_reviews))
    return jsonify({"Error": "Pending reviews not found."})

@views.route('/api/reported/review/', methods=["GET"])
def retrieve_reported_reviews():
    all_service_reviews = []
    service_reviews = reviews.find({"status": "REPORTED"})
    if service_reviews:
        data = list(service_reviews)
        services_list = json.loads(json_util.dumps(data))
        all_service_reviews = services_list
    if all_service_reviews:
        return json.loads(json_util.dumps(all_service_reviews))
    return jsonify({"Error": "Reported reviews not found."})

@views.route('/api/service/order/<order_id>', methods=["GET"])
def retrieve_order_by_Id(order_id):
    order = OrderManagement().retrieve_order_by_uuid(order_id)
    order_service_id = order["service_id"] 
    order_customer_id = order["customer_id"]
    order_business_id = order["business_id"]
    orderId = order["id"]

    customer = Customer.retrieve_customer_by_uuid(
        order_customer_id)
    piyata_points = customer["piyata_points"]
    country_code = customer["country_code"]

    service = Services.retrieve_service_by_uuid(order_service_id)
    service_price = service['price']

    business = Business().retrieve_business_by_uuid(order_business_id)
    business_id = business["id"]
    pending_balance = business["pending_balance"]
    balance = business["balance"]

    order_service_fee = float(order["service_fee"])
    if order is not None and order["status"] == "PAID":
        final_service_price = float(service_price) + (0.3 * order_service_fee)
        orders.find_one_and_update({"id": orderId}, {
            '$set': {"status": "COMPLETED"}})
    if balance is None:
        balance = 0
    if balance is not None:
        pending_balance = pending_balance - final_service_price
        balance = balance + final_service_price
        businesses.find_one_and_update({"id": business_id}, {
            '$set': {"pending_balance": pending_balance}})
        businesses.find_one_and_update({"id": business_id}, {
            '$set': {"balance": balance}})

    if country_code == "+233":
        if piyata_points is not None:
            piyata_points = piyata_points + (order_service_fee * 0.05)
            customers.find_one_and_update({"id": order_customer_id}, {
                '$set': {"piyata_points": piyata_points}})

    elif country_code == "+250":
        if piyata_points is not None:
            piyata_points = piyata_points + (order_service_fee * 0.0005)
            customers.find_one_and_update({"id": order_customer_id}, {
                '$set': {"piyata_points": piyata_points}})

    return jsonify({"Completed": "Successful"})


@views.route('/api/guest-search/service/<keyword>/<country>/', methods=['GET'])
def get_guest_services(keyword,country):
    currency = ''
    if country == "GH":
        currency = "GHC"
    elif country == "RW":
        currency = "RWF"
    search_service_results = []
    cursor_services = services.find(
            {"$text": {"$search": keyword},
             "online": True,
             "verification_status" :"APPROVED",
             "currency": currency}).sort(
            [('rating', -1), ('reviews', -1), ("image", 1)]).limit(30)  if require_verified_services == "True" else services.find(
            {"$text": {"$search": keyword},
             "online": True,
             "currency": currency}).sort(
            [('rating', -1), ('reviews', -1), ("image", 1)]).limit(30)
    if cursor_services:
            data = list(cursor_services)
            services_list = json.loads(json_util.dumps(data))
            search_service_results = services_list

    if search_service_results == []:
            search_service_results = "No results of services called '" + keyword + "'"
    return jsonify({'result': search_service_results})

@views.route('/api/search/service/<keyword>/', methods=['GET'])
def get_services(keyword):
    currency = ''
    customer = Customer.retrieve_customer_by_uuid(session['user']['id'])
    country_code = customer["country_code"]
    customer_favorite= customer["favorite_services"]
    if(country_code == "+233"):
        currency = "GHC"
    elif(country_code == "+250"):
        currency = "RWF"
    search_service_results = []
    cursor_services = services.find(
            {"$text": {"$search": keyword},
             "online": True,
             "verification_status" :"APPROVED",
             "currency": currency}).sort(
            [('rating', -1), ('reviews', -1), ("image", 1)]).limit(30)  if require_verified_services == "True" else services.find(
            {"$text": {"$search": keyword},
             "online": True,
             "currency": currency}).sort(
            [('rating', -1), ('reviews', -1), ("image", 1)]).limit(30)
    if cursor_services:
            data = list(cursor_services)
            services_list = json.loads(json_util.dumps(data))
            search_service_results = services_list

    if search_service_results == []:
            search_service_results = "No results of services called '" + keyword + "'"
    return jsonify({'result': search_service_results})


@views.route('/api/booking/service_order', methods=["POST"])
@login_required
def create_service_order():
    if request.method == "POST":
        customer = Customer.retrieve_customer_by_uuid(
            session['user']['id'])
        order = OrderManagement().create_customer_order(customer)

        if order and order.get("id"):
            return jsonify(json.loads(json_util.dumps(order))), 200
        return jsonify({"error": "Order creation failed"}), 401


@views.route('/api/orders/confirm_order/paystack/<order_id>/', methods=["POST"])
def confirm_payment_order(order_id):
    if request.method == "POST":
        order = orders.find_one({'id': order_id})
        if order:
            if order["country_code"] == "+233":
                order_update = OrderManagement().confirm_order(order=order)
                return jsonify(json.loads(json_util.dumps(order_update)))
        return {"error": "order not found"}
    
@views.route('/api/giftcards/confirm-order/paystack/<giftcard_id>/', methods=["POST"])
def confirm_giftcard_payment(giftcard_id):
    if request.method == "POST":
        customer = Customer.retrieve_customer_by_uuid(
            session['user']['id'])
        if customer:
           GiftCards.confirm_giftcard_payment(giftcard_id=giftcard_id, customer_id=customer["id"])
        return {"error": "Customer not Found"}


@views.route('/api/orders/<user_id>/', methods=["GET"])
def get_orders(user_id):
    if request.method == "GET":
        orders_list = []
        cursor_orders = orders.find({"customer_id": user_id})
        if cursor_orders:
            data = list(cursor_orders)
            orders_list = json.loads(json_util.dumps(data))
        return jsonify(orders_list)

@views.route('/api/orders/with-status/<status>/', methods=["GET"])
def get_orders_with_status(status):
    if request.method == "GET":
        customer = Customer.retrieve_customer_by_uuid(
            session['user']['id'])
        
        if customer:
            orders_list = []
            cursor_orders = orders.find({"customer_id": customer["id"], "status": status})
            if cursor_orders:
                data = list(cursor_orders)
                orders_list = json.loads(json_util.dumps(data))
            return jsonify(orders_list)
        else:
            return jsonify({"error": "Customer not found"})
    else:
        return jsonify({"error": "Method not allowed"})


@views.route('/api/orders/cancel_order/<order_id>/', methods=["GET"])
def get_cancel_order(order_id):
    if request.method == "GET":
        order = OrderManagement().retrieve_order_by_uuid(order_id)
        booking_order_id = order["id"]
        booking_status = order["status"]
        service = Services.retrieve_service_by_uuid(order['service_id'])
        service_id = service["id"]
        service_price = service['price']
        business = Business.retrieve_business_by_uuid(
            order['business_id'])
        business_id = business["id"]
        pending_balance = business["pending_balance"]
        final_pending_balance = float(
            service_price) + (0.3 * float(order['service_fee']))
        pending_balance = pending_balance - final_pending_balance
        if booking_status == "PAID":
            orders.find_one_and_update({"id": booking_order_id}, {
                '$set': {"status": "CANCELED"}})
            businesses.find_one_and_update({"id": business_id}, {
                '$set': {"pending_balance": pending_balance}})
    return jsonify({"Completed": "Successful"})


@views.route('/api/booking/review', methods=["POST"])
@login_required
def create_review():
    if request.method == "POST":
        customer = Customer.retrieve_customer_by_uuid(
            session['user']['id'])
        return Review().store_review_record(customer)
    else:
        return jsonify({"error": "invalid request"}), 400

@views.route('/api/contact_login', methods=["POST"])
def contact_login():
    if request.method == "POST":
        phone_number = request.form["phone_number"]
        password = request.form["password"]
        customer = Customer()
        return customer.login_with_contact(phone_number=phone_number, password=password)
    else:
        return jsonify({"error": "invalid request"}), 400


@views.route('/api/contact_signup', methods=["POST"])
def contact_signup():
    if request.method == "POST":
        phone_number = request.form["phone_number"]
        password = request.form["password"]
        customer = Customer()
        return customer.contact_signup(phone_number=phone_number, password=password)
    else:
        return jsonify({"error": "invalid request"}), 400


@views.route('/api/login_without_password', methods=["POST"])
def login_without_password():
    if request.method == "POST":
        phone_number = request.form["phone_number"]
        customer = Customer()
        return customer.login_without_password(phone_number=phone_number,)
    else:
        return jsonify({"error": "invalid request"}), 400


@views.route('/api/google_login', methods=["POST"])
def google_login():
    if request.method == "POST":
        email = request.form["email"]
        customer = Customer()
        return customer.google_login(email=email)
    else:
        return jsonify({"error": "invalid request"}), 400

@views.route('/api/request-password-reset-otp/<phone_number>/', methods=["POST"])
def request_password_reset_otp(phone_number):
    if request.method == "POST":
        return Customer.request_password_reset_otp(phone_number)


@views.route('/api/verify-otp/<phone_number>/<code>/', methods=["POST"])
def verify_otp(phone_number, code):
    if request.method == "POST":
        return Customer.verify_otp(code=code, phone_number=phone_number)
    
@views.route('/api/customer/reset-password/<customer_id>/<password>/', methods=["POST"])
def reset_password_using_contact(customer_id, password):
    if request.method == "POST":
        return Customer.reset_password(password=password, customerId= customer_id)

@views.route('/api/customer/reset-email-password/<customer_email>/<password>/', methods=["POST"])
def reset_email_password(customer_email, password):
    if request.method == "POST":
        return Customer.reset_email_password(password=password, customer_email=customer_email)


@views.route('/api/customer/reset-contact-password/<customer_number>/<password>/', methods=["POST"])
def reset_contact_password(customer_number, password):
    if request.method == "POST":
        return Customer.reset_contact_password(password=password, customer_number=customer_number)


@views.route('/api/customer/request-password-reset-email/<email>', methods=["POST"])
def request_password_reset_email(email):
    customer = customers.find_one({"email": email})
    if customer:
        return jsonify({'success': 'User account found'}), 200
    return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}), 400


@views.route('/api/customer/request-password-reset-number/<phone_number>', methods=["POST"])
def request_password_reset_number(phone_number):
    customer = customers.find_one({"phone_number": phone_number})
    if customer:
        return jsonify({'success': 'User account found'}), 200
    return jsonify({"error": "No user account found with this phone number.\nTry again or create a new account."}), 400

@views.route('/api/customer/reset-password/', methods=["POST"])
def reset_password():
    if request.method == "POST":
        password = request.form["password"]
        customer = Customer.retrieve_customer_by_uuid(session['user']['id'])
        return Customer.reset_password(password=password, customerId=customer)


@views.route('/api/customer/send-welcome-email/<customer_id>/', methods=["POST"])
def send_welcome_email(customer_id):
    if request.method == "POST":
        return Notifications.send_welcome_email(customer_id=customer_id)

@views.route('/api/send-business-approval-message/<business_id>/', methods=["POST"])
def send_approval_email(business_id):
    if request.method == "POST":
        return Notifications.send_business_approval_message(business_id=business_id)
    
@views.route('/api/send-business-rejection-message/<business_id>/<rejected_reason>/', methods=["POST"])
def send_rejection_email(business_id,rejected_reason):
    if request.method == "POST":
        return Notifications.send_business_rejection_message(business_id=business_id, rejected_reason=rejected_reason)
    
@views.route('/api/send-service-approval-message/<business_id>/', methods=["POST"])
def send_service_approval_email(business_id):
    if request.method == "POST":
        return Notifications.send_service_approval_message(business_id=business_id)
    
@views.route('/api/send-service-reported-message/<business_id>/', methods=["POST"])
def send_service_reported_email(business_id):
    if request.method == "POST":
        return Notifications.send_service_reported_message(business_id=business_id)

@views.route('/api/send-service-rejection-message/<business_id>/<rejected_reason>/', methods=["POST"])
def send_service_rejection_email(business_id, rejected_reason):
    if request.method == "POST":
        return Notifications.send_service_rejection_message(business_id=business_id, rejected_reason=rejected_reason)

@views.route('/api/customer/send-welcome-email/<customer_id>/<business_name>', methods=["POST"])
def send_service_completed_email(customer_id, business_name):
    if request.method == "POST":
        return Notifications.send_service_completed_email(customer_id=customer_id, business_name=business_name)


@views.route('/api/customer/delete/<customer_id>/', methods=["POST"])
def delete_customer(customer_id):
    if request.method == "POST":
        return Customer.deleteAccount(customer_id=customer_id)


@views.route('/api/payment-callback/', methods=['GET', 'POST'])
def payment_callback():
    request_data = request.get_json()
    print(request_data)
    status = request_data['status']
    print("=========================PAYMENT-CALLBACK====================================")
    print(request_data)
    if status == "SUCCESS":
        transaction_id = request_data['transactionId']
        transaction = transactions.find_one({"id": transaction_id})
        if transaction:
            transactions.find_one_and_update({"id": transaction_id}, {
                                             '$set': {"status": "SUCCESS"}})
            order = orders.find_one({"id": transaction['order_id']})
            try:
                if order['status'] != "COMPLETED":
                    orders.find_one_and_update({"id": transaction['order_id']}, {
                                               '$set': {"status": "PAID"}})
                    print("Payment confirmed and status updated successfully.")
                    return "Payment confirmed and status updated successfully."
            except:
                print("Error when checking order status.")
                return "Error when checking order status."
    else:
        return status
    
@views.route('/api/payment/paystack-webhook/', methods=['GET', 'POST'])
def paystack_webhook():
    request_data = request.get_json()
    data = request_data['data']
    status = data['status']
    transaction_id = data['reference']
    transaction = transactions.find_one({"id": transaction_id})
    print("=========================PAYMENT-WEBHOOK====================================")
    if transaction:
        if status == "success":
            transactions.find_one_and_update({"id": transaction_id}, {
                                             '$set': {"status": "SUCCESS"}})
            if transaction['service_name'] == "Gift Card":
                GiftCards.confirm_giftcard_payment(giftcard_id=transaction['order_id'], customer_id=transaction['customer_id'])
                
            else:
                order = orders.find_one({"id": transaction['order_id']})
                if order:
                    OrderManagement().confirm_order(order=order)

        elif status == "failed":
            transactions.find_one_and_update({"id": transaction_id}, {
                                             '$set': {"status": "FAILED"}})
            customer = customers.find_one({'id':transaction['customer_id']})
            if customer.get('fcm_token'):
                Notifications.send_single_notifications(title="Payment Failed", body="Your payment has failed. Please try again.", fcm_token=customer.get('fcm_token'))
            
            return jsonify({"message": "Webhook received"}), 200
    else:
        return jsonify({"message": "Order not found"}), 400


@views.route('/api/orders/payment-status/<order_id>', methods=['GET'])
def check_payment_status(order_id):
    order = orders.find_one({"id": order_id})
    if order:
        status = order['status']
        if status == "PAID":
            return jsonify({"status": order['status']}), 200
        else:
            return jsonify({"status": order['status']}), 400
    else:
        return {"Error": "Order not found"}, 401


@views.route('/api/orders/delete-order/<order_id>', methods=['POST'])
def delete_order(order_id):
    order =  orders.delete_one({"id": order_id})
    if order.deleted_count == 1:
        return jsonify({"status": "Order deleted successfully."}), 200
    else :
        return jsonify({"Error": "Order not found"}), 401

@views.route("/api/delete/service/review/<review_id>/", methods=["POST"])
def delete_service_review(review_id):
    review =  reviews.find_one_and_update({"id": review_id}, {
                                               '$set': {"status": "DELETED"}})
    return review["status"]

@views.route("/api/approve/service/review/<review_id>/", methods=["POST"])
def approve_service_review(review_id):
        return Review.approve_review(review_id=review_id)

@views.route("/api/report/service/review/<review_id>/", methods=["POST"])
def report_service_review(review_id):
    review =  reviews.find_one_and_update({"id": review_id}, {
                                               '$set': {"status": "REPORTED"}})
    return review["status"]

@views.route("/api/service-likes/<review_id>/", methods=["POST"])
def adding_likes_to_review(review_id):
    get_review = Review.retrieve_review_by_uuid(review_id)
    likes = get_review["likes"]
    if get_review:
        likes = likes + 1
        reviews.find_one_and_update({"id": review_id}, {
                                               '$set': {"likes": likes}})
        return jsonify({"success": "Completed"})
    else:
         return jsonify({"error": "No review found.\nTry again later."}), 400

@views.route("/api/service-unlikes/<review_id>/", methods=["POST"])
def removing_likes_from_review(review_id):
    get_review = Review.retrieve_review_by_uuid(review_id)
    likes = get_review["likes"]
    if get_review:
        likes = likes - 1
        reviews.find_one_and_update({"id": review_id}, {
                                               '$set': {"likes": likes}})
        return jsonify({"success": "Completed"})
    else:
         return jsonify({"error": "No review found.\nTry again later."}), 400

@views.route("/api/admin-management/<customer_email>/<role>", methods=["POST"])
def add_admin_or_manager(customer_email, role):
    customer = Customer.retrieve_customer_by_email(customer_email)
    if customer:
        update_role =  customers.find_one_and_update({"email": customer_email}, {
                                               '$set': {"role": role}})
        if update_role:
            added_role = "" + role + " added succesfully"
            return jsonify({"Success": added_role})
        else:
             return jsonify({"error": "No user account found with this email.\nTry again later."}), 400
    else:
        return jsonify({"error": "No user account found with this email.\nTry again later."}), 400

@views.route("/api/delete/admin-management/<customer_email>", methods=["POST"])
def delete_admin_or_manager(customer_email):
    customer = Customer.retrieve_customer_by_email(customer_email)
    if customer:
        update_role =  customers.find_one_and_update({"email": customer_email}, {
                                               '$set': {"role": None}})
        if update_role:
            added_role = "" + customer_email + " removed successfully"
            return jsonify({"Success": added_role})
        else:
             return jsonify({"error": "No user account found with this email.\nTry again later."}), 400
    else:
        return jsonify({"error": "No user account found with this email.\nTry again later."}), 400
    
@views.route('/api/retrieve-admins', methods=['GET'])
def get_admins_and_managers():
    customer_results = []
    cursor_customers = customers.find(
        {
        "role": {"$in": ["ADMIN", "MANAGER", "AGENT"]}
         })
    if cursor_customers:
        data = list(cursor_customers)
        customer_list = json.loads(json_util.dumps(data))
        customer_results = customer_list

        if customer_results == []:
            customer_results = "No results of admins or managers found"
        return customer_results

@views.route('/api/services/unpublish/<service_id>/', methods=["POST"])
def unpublish_service(service_id):
    if request.method == "POST":
        data = json.loads(request.data)
        service = services.find({"id": service_id})
        if service:
            Services().update_service(service_id=service_id, data=data)
            updated_service = services.find_one({"id": service_id})
            return updated_service
        else:
             return jsonify({"error": "Failed to unpublish service."}), 400
        
@views.route('/api/giftcards/create/', methods=["POST"])
def create_giftcard():
    if request.method == "POST":
        admin =  customers.find_one({"id": session['user']['id']})
        if(admin):
            data = json.loads(request.data)
            return GiftCards().create_giftcard(data)
        else:
            return jsonify({"error": "User not found"}), 400
    
@views.route('/api/giftcards/update/<giftcard_id>/', methods=["POST"])
def update_giftcard(giftcard_id):
    """"
    Update a giftcard
    """
    if request.method == "POST":
        admin =  customers.find_one({"id": session['user']['id']})
        if(admin):
            data = json.loads(request.data)
            giftcard = giftcards.find({"id": giftcard_id})
            print(giftcard)
            if giftcard:
                return GiftCards().update_giftcard(giftcard_id=giftcard_id, data=data)
            else:
                return jsonify({"error": "Giftcard not found"}), 400
        else:
            return jsonify({"error": "User not found"}), 400
        

@views.route('/api/giftcards/delete/<giftcard_id>/', methods=["POST"])
def delete_giftcard(giftcard_id):
    """"
    Deletes a giftcard
    """
    if request.method == "POST":
        admin =  customers.find_one({"id": session['user']['id']})
        if(admin):
            return GiftCards().delete_giftcard(giftcard_id=giftcard_id)
        else:
            return jsonify({"error": "Admin not found"}), 400
@views.route('/api/giftcards/rwanda/pay/<number>/<amount>/<giftcard_id>/<email>', methods=["POST"])
def pay_rwanda_gift_card(number,amount,giftcard_id,email):
    """"
    Pay for a rwanda giftcard
    """
    if request.method == "POST":
          customer =  customers.find_one({"id": session['user']['id']})
          if(customer):
            customer_id = session['user']['id']
            return GiftCards().make_rwanda_payment(number=number,amount=amount,giftcard_id=giftcard_id,email=email, customer_Id=customer_id)
          else:
              return jsonify({"error": "User not found"}), 402
    else:
        print('bad request method')
        return jsonify({"error": "Admin not found"}), 400


@views.route('/api/giftcards/<giftcard_id>/', methods=["GET"])
def get_giftcard(giftcard_id):
    """"
    Retrieve a giftcard
    """
    if request.method == "GET":
        admin = customers.find_one({"id": session['user']['id']})
        if(admin):
            giftcard = giftcards.find_one({"id": giftcard_id})
            if giftcard:
                return json.loads(json_util.dumps({"result": giftcard})), 200
            else:
                return jsonify({"error": "Gift card not found"}), 400
        else:
            return jsonify({"error": "User not found"}), 400


@views.route('/api/admin/giftcards/', methods=["GET"])
def get_business_giftcards():
    """"
    Retrieve all giftcards for a business
    """
    if request.method == "GET":
        admin = customers.find_one({"id": session['user']['id'], "role": "ADMIN"})
        if(admin):
            business_giftcards = giftcards.find({"type": "PIYATA"})
            return json.loads(json_util.dumps(business_giftcards)), 200
        else:
            return jsonify({"error": "Admin not found"}), 400


@views.route('/api/customer/giftcards/', methods=["GET"])
def get_customer_giftcards():
    """"
    Retrieve all giftcards for a customer
    """
    if request.method == "GET":
        customer = customers.find_one({"id": session['user']['id']})
        if(customer):
            customer_giftcards = giftcards.find({"$or":[{"gifted_id": customer['id']},{"gifter_id":customer['id']}]})
            return json.loads(json_util.dumps(customer_giftcards)), 200
        else:
            return jsonify({"error": "Customer not found"}), 400
        
@views.route('/api/giftcards/rwanda/payment-callback/<giftcard_id>/<email>', methods=["POST"])
def rwanda_gift_card_payment_callback(giftcard_id,email):
    return GiftCards().rwanda_payment_callback(giftcard_id=giftcard_id,email=email)

@views.route('/api/booking/cashless-service-order', methods=["POST"])
@login_required
def create_cashless_service_order():
    if request.method == "POST":
        customer = Customer.retrieve_customer_by_uuid(
            session['user']['id'])
        order = OrderManagement().create_customer_cashless_order(customer)

        if order and order.get("id"):
            return jsonify(json.loads(json_util.dumps(order))), 200
        return jsonify({"error": "Order creation failed"}), 401


@views.route('/api/analytics/<country>/<status>', methods=["GET"])
def get_analytics_businesses(country,status):
    all_business_results = []
    cursor_businesses = businesses.find(
        {
        "account_verification.status":status,
        "country": country})
    if cursor_businesses:
        data = list(cursor_businesses)
        businesses_list = json.loads(json_util.dumps(data))
        all_business_results = businesses_list if businesses_list else []
        return all_business_results
    else:
        return jsonify({"Error": "No Business Found"})

@views.route('/api/favourite_businesses', methods=["GET"])
def get_favourite_businesses():
    customer = Customer.retrieve_customer_by_uuid(
        session['user']['id'])
    country = customer.get("country")
    customer_favorite = customer.get("user_favourites", [])
    if customer:
        if customer_favorite is not None:
            all_business_results = []
            cursor_businesses = businesses.find(
                {
                "id": {"$in": customer_favorite},
                "country": country
                    })
            if cursor_businesses:
                data = list(cursor_businesses)
                businesses_list = json.loads(json_util.dumps(data))
                all_business_results = businesses_list if businesses_list else []
                return all_business_results
    else:
        return jsonify({"Error": "No User found. Please login or signup"})

@views.route('/api/favourite-service/', methods=['GET'])
def get_favourite_services():
    currency = ''
    customer = Customer.retrieve_customer_by_uuid(session['user']['id'])
    customer_favorite = customer.get("user_favourites", [])
    country_code = customer.get("country_code")
    if(country_code == "+233"):
        currency = "GHC"
    elif(country_code == "+250"):
        currency = "RWF"
    favourite_service_result = []
    if customer:
        if customer_favorite is not None:
            cursor_services = services.find(
            {
            "id": {"$in": customer_favorite},
            "currency": currency})
            if cursor_services:
                data = list(cursor_services)
                services_list = json.loads(json_util.dumps(data))
                favourite_service_result = services_list if services_list else []
                return  favourite_service_result
    else:
        return jsonify({"Error": "No User found. Please login or signup"})
    
@views.route('/api/all-bookings-orders/', methods=["GET"])
def get_all_booking_orders():
    customer = Customer.retrieve_customer_by_uuid(session['user']['id'])
    country_code = customer["country_code"]
    customer_id = customer["id"]
    all_bookings = []
    if customer:
        paid_orders = orders.find(
            {"customer_id":customer_id,
             "country_code": country_code
                            })
        if paid_orders:
            data = list(paid_orders)
            booking_list = json.loads(json_util.dumps(data))
            all_bookings = booking_list if booking_list else []
            return  all_bookings
    else:
        return jsonify({"Error": "No User found. Please login or signup"})
    
@views.route('/api/all-success-transactions/', methods=["GET"])
def get_all_transactions_orders():
    customer = Customer.retrieve_customer_by_uuid(session['user']['id'])
    customer_id = customer["id"]
    all_transactions = []
    if customer:
        success_transactions = transactions.find(
            {"customer_id":customer_id,
             "status": {"$in": ["success", "SUCCESS"]} })
        if success_transactions:
            data = list(success_transactions)
            transaction_list = json.loads(json_util.dumps(data))
            all_transactions = transaction_list if transaction_list else []
            return  all_transactions
    else:
        return jsonify({"Error": "No User found. Please login or signup"})

@views.route('/api/businesses/get-single-business/<business_id>', methods = ["GET"])
def get_single_business(business_id):
    business = businesses.find_one({"id": business_id})
    business_staffs = staffs.find({"business_id": business_id})
    if business:
        business["staffs"] = list(business_staffs)
        return json.loads(json_util.dumps(business)), 200
    else:
        return jsonify({"Error": "No Business Found"}), 400

@views.route('/api/services/get-single-service/<service_id>', methods = ["GET"])
def get_single_service(service_id):
    service = services.find_one({"id": service_id})
    if service:
        return json.loads(json_util.dumps(service)), 200
    else:
        return jsonify({"Error": "No Service Found"}), 400
    
@views.route('/api/business/delete/<business_id>/', methods=["POST"]) 
def delete_business(business_id):
    if request.method == "POST":
        return Business.deleteAccount(business_id=business_id)

@views.route('/api/complete-order/<order_id>', methods=["POST"]) 
def complete_order(order_id):
    customer = customers.find_one({"id": session['user']['id']})
    if(customer):
        if request.method == "POST":
            return OrderManagement().transfer_from_pending_to_balance(order_id=order_id)
    else:
        return jsonify({"error": "Business not found"}), 400


@views.route('/api/transactions/add-record/', methods=["POST"])
def add_transaction_record():
    if request.method == "POST":
        customer =  customers.find_one({"id": session['user']['id']})
        if(customer):
            data = json.loads(request.data)

            return Transaction().add_transaction(data)
        else:
            return jsonify({"error": "User not found"}), 400

# ============== Messages ====================

@views.route('/api/messages/send-specific-business/<business_id>', methods=["POST"])
def send_message_specific_business(business_id):
    data = request.get_json()
    subject = data['subject']
    message = data['body']
    business = businesses.find_one({"id": business_id})
    if business:
        msg=Message(subject,sender=("piyata",'support@piyata.tech'),recipients=[business['email'],'support@piyata.tech'])
        msg.body= message
        mail.send(msg)
        Notifications.send_single_notifications(fcm_token=business['fcm_token'], body="You have a new message from piyata",title="New Message on Piyata App")  
        return Messages().create_message(data=data)
    return jsonify({"error": "No user account found with this email.\nTry again or create a new account."}),401

@views.route('/api/messages/send-mult-business',methods = ["POST"]) 
def send_many_messages():
    data = request.get_json()
    subject = data['subject']
    message = data['body']
    page=data['page']
    PER_PAGE = 20
    page_number=int(page)
    skip = (page_number - 1) * PER_PAGE
    all_business_results = []
    recipients =[]
    # tokens=[]
    cursor_businesses = businesses.find({
        "account_verification.status":data['business_status'],
        "country": data['business_country']
        }).skip(skip).limit(PER_PAGE)
    if cursor_businesses:
        datas = list(cursor_businesses)
        businesses_list = json.loads(json_util.dumps(datas))
        all_business_results = businesses_list if businesses_list else []
        for business in all_business_results:
            if business['email'] is not None and '@' in business['email']:
                recipients.append(business['email'])
                # tokens.append(business['fcm_token'])
        if not datas:
            return jsonify({'businesses': []}), 200
        msg = Message(sender=("piyata",'support@piyata.tech'),
                      recipients=json.loads(json_util.dumps(recipients)),
                      subject=subject,
                      body= message)
        mail.send(msg)
        # Notifications.send_multicast_notifications(tokens=tokens,body="You have a new message from piyata",title="New Message on Piyata App")
        return json.loads(json_util.dumps({"businesses":all_business_results})), 200

@views.route('/api/message/save/businesses/',methods = ["POST"]) 
def save_messages_of_all_bussinesses():
    if request.method == "POST":
        data = request.get_json()
        return Messages().create_message(data=data)
    else:
        return jsonify({"error": "Method Not Allowed"}), 405



@views.route('/api/messages/get-messages/<business_id>', methods=["GET"])
def get_messages(business_id):
    if request.method == "GET":
        return Messages.get_all_messages_by_business(business_id)
    else:
        return jsonify({"error": "Method Not Allowed"}), 405

@views.route('/api/messages/get-messages/many-businesses/<country>/<verification_status>', methods=['GET'])
def get_many_businesses_messages(country,verification_status):
    if request.method == "GET":
        return Messages.get_all_message_by_recipient_type(country,verification_status)
    else:
        return jsonify({"error": "Method Not Allowed"}), 405

@views.route('/api/messages/get-messages/all-businesses/', methods=['GET'])
def get_messages_sent_to_all_bussinesses():
    if request.method == "GET":
        return Messages.get_messages_sent_all_bussiness()
    else:
        return jsonify({"error": "Method Not Allowed"}), 405


@views.route('/api/messages/delete-message/<message_id>', methods=["POST"])
def delete_message(message_id):
    if request.method == "POST":
        return Messages.delete_message(message_id=message_id)
    else:
        return jsonify({"error": "Method Not Allowed"}), 405

@views.route('/api/messages/businesses/paginate/<page>', methods=["POST"]) 
def get_paginate_businesses(page):
    data = request.get_json()
    subject = data['subject']
    message = data['body']
    # PER_PAGE = 4
    PER_PAGE = 20
    page_number=int(page)
    skip = (page_number - 1) * PER_PAGE
    all_business_results = []
    recipients =[]
    # tokens=[]
    cursor_businesses = businesses.find().skip(skip).limit(PER_PAGE)
    if cursor_businesses:
        datas = list(cursor_businesses)
        businesses_list = json.loads(json_util.dumps(datas))
        all_business_results = businesses_list if businesses_list else []
        for business in all_business_results:
            if business['email'] is not None and '@' in business['email']:
                recipients.append(business['email'])
                # tokens.append(business['fcm_token'])
        if not datas:
            return jsonify({'businesses': []}), 200
        msg = Message(sender=("piyata",'support@piyata.tech'),
                      recipients=json.loads(json_util.dumps(recipients)),
                      subject=subject,
                      body= message)
        mail.send(msg)
        # Notifications.send_multicast_notifications(tokens=tokens,body="You have a new message from piyata",title="New Message on Piyata App")
        return json.loads(json_util.dumps({"businesses":all_business_results})), 200

@views.route('/api/messages/get-messages/customer/<booking_id>', methods=["GET"])
def get_customer_messages(booking_id):
    if request.method == "GET":
        return Messages.get_all_messages_customer_by_booking_id(booking_id)
    else:
        return jsonify({"error": "Method Not Allowed"}), 405
# =================================== Customer Verification =====================

@views.route('/api/customer/upload-file', methods=["POST"])
def upload_image():
    if request.method == "POST":
        s3 = boto3.resource('s3')
        BUCKET_NAME = 'piyataimages'
        f = request.files["image"]
        filename = uuid.uuid4().hex + secure_filename(f.filename)
        s3.Bucket(BUCKET_NAME).put_object(Key=filename, Body=f)
        image_id = uuid.uuid4().hex
        images.insert_one({"id": image_id, "creation_timestamp": datetime.datetime.now(
        ), "name": filename, "url": f"https://{BUCKET_NAME}.s3.amazonaws.com/{filename}"})
        image = ImagesDatabaseClient.retrieve_image_by_uuid(image_id)
        return jsonify({"image_url": image['url']})
    
@views.route('/api/send/customer/verification', methods=["POST"])
def customer_verification():
    if request.method == "POST":
        data = request.get_json()
        user=customers.find_one({"id": session['user']['id']})
        if user is not None:
            customers.update_one({"id": user['id']},{'$set':{'account_verification':data['account_verification']}})
            userInfo=customers.find_one({"id":user['id']})
            Notifications.send_customer_submit_message(customer_id=user['id'])
            return json.loads(json_util.dumps({"result":userInfo})),200
        return jsonify({"error":"Customer not found"}),401
    
@views.route('/api/customer/verification/filter', methods=["POST"])
def customer_verification_filter():
    data = request.get_json()
    query={"$and":[{"country":data['country']},{"account_verification.status":data['status']}]}
    customers_list=customers.find(query)
    if customers_list is None:
        return jsonify({"error":"Customer not found"}),401
    return json.loads(json_util.dumps({"result":customers_list})), 200

@views.route('/api/customer/verification/update/<id>', methods=["POST"])
def customer_verification_update(id):
    data = request.get_json()
    query={"id":id}
    customer=customers.find_one(query)
    if customer is None:
        return jsonify({"error":"Customer not found"}),401
    customers.update_one({"id": customer['id']},{'$set':{'account_verification':data['account_verification']}})
    if data['account_verification']['status']=="APPROVED":
        Notifications.send_customer_approval_message(customer_id=customer['id'])
    if data['account_verification']['status']=="REJECTED":
        Notifications.send_customer_rejection_message(customer_id=customer['id'],message=data['account_verification']['rejected_reason'])
    return json.loads(json_util.dumps({"result":"Update Successful"})), 200


@views.route('/api/business/staffs/<business_id>/', methods=["GET"])
def get_all_business_staffs(business_id):
    """"
    Retrieve all staff members of a business
    """
    if request.method == "GET":
        customer = customers.find_one({"id": session['user']['id']})
        if(customer):
            business_staffs = staffs.find({"business_id": business_id})
            return json.loads(json_util.dumps(business_staffs)), 200
        else:
            return jsonify({"error": "Customer not found"}), 400
    else:
        return jsonify({"error": "Method Not Allowed"}), 405
    
@views.route('/api/staff/orders/<staff_id>/', methods=["GET"])
def get_staff_orders(staff_id):
    """"
    Retrieve paid orders or a staff member of a business
    """
    if request.method == "GET":
        customer = customers.find_one({"id": session['user']['id']})
        if(customer):
            staff_orders = orders.find({"staff_id": staff_id, "status": "PAID"})
            return json.loads(json_util.dumps(staff_orders)), 200
        else:
            return jsonify({"error": "Customer not found"}), 400
    else:
        return jsonify({"error": "Method Not Allowed"}), 405

@views.route('/api/staffs/<staff_id>/', methods=["GET"])
def get_staff(staff_id):
    """"
    Retrieve a staff member
    """
    if request.method == "GET":
        customer = customers.find_one({"id": session['user']['id']})
        if(customer):
            staff = staffs.find_one({"id": staff_id})
            if staff:
                return json.loads(json_util.dumps({"result": staff})), 200
            else:
                return jsonify({"error": "Staff member not found"}), 400
        else:
            return jsonify({"error": "Customer not found"}), 400
    else:
            return jsonify({"error": "Method Not Allowed"}), 405

@views.route('/api/promotions/create/', methods=["POST"])
def create_promotion():
    if request.method == "POST":
        admin =  customers.find_one({"id": session['user']['id']})
        if(admin):
            data = json.loads(request.data)
            return Promotions().create_promotion(data)
        else:
            return jsonify({"error": "User not found"}), 400
    else:
        return jsonify({"error": "Method Not Allowed"}), 405
    
@views.route('/api/promotions/update/<promo_id>/', methods=["POST"])
def update_promotion(promo_id):
    """"
    Update a promotion
    """
    if request.method == "POST":
        admin =  customers.find_one({"id": session['user']['id']})
        if(admin):
            data = json.loads(request.data)
            promo = promotions.find({"id": promo_id})

            if promo:
                return Promotions().update_promotion(promo_id=promo_id, data=data)
            else:
                return jsonify({"error": "Promotion not found"}), 400
        else:
            return jsonify({"error": "User not found"}), 400
    else:
         return jsonify({"error": "Method Not Allowed"}), 405
        

@views.route('/api/promotions/delete/<promo_id>/', methods=["POST"])
def delete_promotion(promo_id):
    """"
    Deletes a promotion
    """
    if request.method == "POST":
        admin =  customers.find_one({"id": session['user']['id']})
        if(admin):
            return Promotions().delete_promotion(promo_id=promo_id)
        else:
            return jsonify({"error": "User not found"}), 400
    else:
        return jsonify({"error": "Method Not Allowed"}), 405
@views.route('/api/promotions/', methods=["GET"])
def get_promotions():
    """"
    Retrieve all promotions
    """
    if request.method == "GET":
        admin = customers.find_one({"id": session['user']['id']})
        if(admin):
            all_promotions = promotions.find()
            return json.loads(json_util.dumps(all_promotions)), 200
        else:
            return jsonify({"error": "User not found"}), 400
    else:
        return jsonify({"error": "Method Not Allowed"}), 405
    
@views.route('/api/order-with-promo/', methods=["POST"])
def get_order_with_promo():
    if request.method == "POST":
        customer = Customer.retrieve_customer_by_uuid(
            session['user']['id'])
        order = OrderManagement().create_customer_promo_order(customer)

        if order and order.get("id"):
            return jsonify(json.loads(json_util.dumps(order))), 200
        return jsonify({"error": "Order creation failed"}), 401
    else:
        return jsonify({"error": "Method Not Allowed"}), 405